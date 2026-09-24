"""Hybrid retrieval: filter, vector search, impact scroll, rank."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from news_rag.config import get_settings
from news_rag.embed import embed_query
from news_rag.entity_index import corpus_entity_names
from news_rag.parse import ParsedQuery, extract_stock_hint, parse_time_window, resolve_entities
from news_rag.qdrant_reader import (
    QdrantReader,
    build_filter,
    describe_filters_for_log,
    filter_spec,
)

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger


def _trim_snippet(text: str, limit: int) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _wants_price_recap(question: str) -> bool:
    lower = question.lower()
    return any(word in lower for word in ("price", "target", "rating", "upgrade", "downgrade", "recap"))


def retrieve_for_question(
    question: str,
    *,
    stock: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
) -> tuple[ParsedQuery, list[dict]]:
    settings = get_settings()
    published_from, published_to, window_label = parse_time_window(
        question,
        date_from=date_from,
        date_to=date_to,
        default_days=settings.default_window_days,
    )
    hint = extract_stock_hint(question, stock)
    t0 = time.perf_counter()
    corpus = corpus_entity_names()
    if query_log is not None:
        query_log.log_step("corpus_entity_index", time.perf_counter() - t0, unique_names=len(corpus))
    names, note = resolve_entities(hint, corpus)
    entity_filter = names if names else None

    parsed = ParsedQuery(
        question=question.strip(),
        published_from=published_from,
        published_to=published_to,
        window_label=window_label,
        stock_hint=hint,
        entity_resolved=names,
        entity_match_note=note,
    )
    if query_log is not None:
        query_log.log_parsed(parsed)

    filter_kwargs = {
        "entity_names": entity_filter,
        "published_from": published_from,
        "published_to": published_to,
        "min_relevance": settings.min_relevance,
        "min_impact": min_impact,
        "source": source or None,
        "direction": direction or None,
    }
    filt = build_filter(**filter_kwargs)
    allow_recap = _wants_price_recap(question)
    post_filter_meta = {
        "exclude_event_type_price_recap": not allow_recap,
        "retrieve_vector_limit": settings.retrieve_vector_limit,
        "retrieve_impact_limit": settings.retrieve_impact_limit,
        "retrieve_max_articles": settings.retrieve_max_articles,
        "collection": settings.qdrant_collection,
    }
    spec = filter_spec(**filter_kwargs)
    if query_log is not None:
        query_log.log_filters(spec, post_filters=post_filter_meta)
        query_log.log_filters_applied(
            describe_filters_for_log(
                spec,
                collection=settings.qdrant_collection,
                post_filters=post_filter_meta,
            )
        )

    reader = QdrantReader()
    t1 = time.perf_counter()
    vector = embed_query(question)
    if query_log is not None:
        query_log.log_step("embed_query", time.perf_counter() - t1, vector_dim=len(vector))

    t2 = time.perf_counter()
    vector_rows = reader.query_vector(vector, filt, settings.retrieve_vector_limit)
    if query_log is not None:
        query_log.log_step(
            "qdrant_query_vector",
            time.perf_counter() - t2,
            hits=len(vector_rows),
            limit=settings.retrieve_vector_limit,
        )
        query_log.log_articles_block("qdrant_vector", vector_rows)

    t3 = time.perf_counter()
    impact_rows = reader.scroll_filtered(filt, settings.retrieve_impact_limit)
    if query_log is not None:
        query_log.log_step(
            "qdrant_scroll_filtered",
            time.perf_counter() - t3,
            hits=len(impact_rows),
            limit=settings.retrieve_impact_limit,
        )
        query_log.log_articles_block("qdrant_scroll", impact_rows)

    by_url: dict[str, dict] = {}
    for row in vector_rows:
        url = row.get("url") or ""
        if not url:
            continue
        by_url[url] = {**row, "_vector_score": row.get("score", 0.0)}

    for row in impact_rows:
        url = row.get("url") or ""
        if not url:
            continue
        if url not in by_url:
            by_url[url] = {**row, "_vector_score": 0.0}
        else:
            by_url[url].update({k: v for k, v in row.items() if k not in by_url[url] or not by_url[url].get(k)})

    if query_log is not None:
        query_log.write(f"merge unique_urls={len(by_url)}")

    ranked: list[dict] = []
    skipped_recap = 0
    for row in by_url.values():
        if not allow_recap and row.get("event_type") == "price_recap":
            skipped_recap += 1
            continue
        snippet = _trim_snippet(row.get("scraped_text") or "", settings.snippet_chars)
        ranked.append(
            {
                "url": row.get("url"),
                "title": row.get("title"),
                "source": row.get("source"),
                "published_at": row.get("published_at"),
                "entity_names": row.get("entity_names") or [],
                "primary_industry": row.get("primary_industry") or "",
                "max_impact": int(row.get("max_impact") or 0),
                "max_relevance": int(row.get("max_relevance") or 0),
                "direction": row.get("direction") or "",
                "event_type": row.get("event_type") or "",
                "snippet": snippet,
                "_vector_score": float(row.get("_vector_score") or 0.0),
            }
        )

    entity_set = {name.lower() for name in names}

    def _entity_match_rank(item: dict) -> int:
        if not entity_set:
            return 0
        article_entities = {str(n).lower() for n in (item.get("entity_names") or [])}
        return 1 if entity_set & article_entities else 0

    ranked.sort(
        key=lambda item: (
            _entity_match_rank(item),
            item["max_impact"],
            item["_vector_score"],
            item.get("published_at") or "",
        ),
        reverse=True,
    )
    final = ranked[: settings.retrieve_max_articles]
    if query_log is not None:
        if skipped_recap:
            query_log.write(f"post_filter skipped_price_recap={skipped_recap}")
        query_log.log_articles_block("ranked_for_llm", final, snippet_limit=settings.snippet_chars)
    return parsed, final
