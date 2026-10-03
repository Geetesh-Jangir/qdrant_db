"""Scoped news retrieval for the ask engine — no unfiltered fallback when entities required."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

from news_rag.config import get_settings
from news_rag.embed import embed_query
from news_rag.parse import parse_time_window
from news_rag.qdrant_reader import QdrantReader, build_filter, filter_spec
from news_rag.query_plan import ScopeRefinement, SearchMode

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


def _topic_match(article: dict, topics: list[str]) -> bool:
    if not topics:
        return True
    hay = " ".join(
        [
            str(article.get("title") or ""),
            str(article.get("snippet") or ""),
            " ".join(str(x) for x in (article.get("sector_names") or [])),
        ]
    ).lower()
    return any(t.lower() in hay for t in topics)


def retrieve_scoped_news(
    semantic_query: str,
    *,
    scope: ScopeRefinement | None = None,
    question: str = "",
    date_from: str | None = None,
    date_to: str | None = None,
    window_days: int | None = None,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
) -> list[dict]:
    settings = get_settings()
    scope = scope or ScopeRefinement()
    effective_days = window_days if window_days else settings.default_window_days
    published_from, published_to, _label = parse_time_window(
        question or semantic_query,
        date_from=date_from,
        date_to=date_to,
        default_days=effective_days,
    )

    entity_filter: list[str] | None = None
    mode: SearchMode = scope.search_mode
    if mode in ("entities_only", "event_plus_entities") and scope.news_entities:
        entity_filter = list(scope.news_entities)
    elif mode == "event_only":
        entity_filter = None
    else:
        entity_filter = list(scope.news_entities) if scope.news_entities else None

    # When entities were chosen, require filter — zero hits stay zero.
    if mode != "event_only" and scope.news_entities and not entity_filter:
        if query_log is not None:
            query_log.write("RETRIEVE skipped reason=empty_entity_filter")
        return []

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
    spec = filter_spec(**filter_kwargs)
    if query_log is not None:
        query_log.write(
            f"RETRIEVE mode={mode} entities={entity_filter} topics={scope.news_topics}"
        )
        query_log.log_filters(spec, post_filters={"scoped": True, "mode": mode})

    reader = QdrantReader()
    query_text = semantic_query or question
    t_embed = time.perf_counter()
    vector = embed_query(query_text.strip())
    if query_log is not None:
        query_log.log_step("embed_query", time.perf_counter() - t_embed, vector_dim=len(vector))

    t_vec = time.perf_counter()
    vector_rows = reader.query_vector(vector, filt, settings.retrieve_vector_limit)
    if query_log is not None:
        query_log.log_step("qdrant_query_vector", time.perf_counter() - t_vec, hits=len(vector_rows))

    min_score = settings.retrieve_min_vector_score
    vector_rows = [r for r in vector_rows if float(r.get("score") or 0) >= min_score]

    impact_rows: list[dict] = []
    if entity_filter:
        t_scroll = time.perf_counter()
        impact_rows = reader.scroll_filtered(filt, settings.retrieve_impact_limit)
        if query_log is not None:
            query_log.log_step("qdrant_scroll_filtered", time.perf_counter() - t_scroll, hits=len(impact_rows))

    allow_recap = _wants_price_recap(question or semantic_query)
    k = 60.0
    rrf_scores: dict[str, float] = {}
    by_url: dict[str, dict] = {}

    for rank, row in enumerate(vector_rows):
        url = row.get("url") or ""
        if not url:
            continue
        rrf_scores[url] = rrf_scores.get(url, 0.0) + (1.0 / (k + rank + 1))
        by_url[url] = {**row, "_vector_score": row.get("score", 0.0)}

    for rank, row in enumerate(impact_rows):
        url = row.get("url") or ""
        if not url:
            continue
        rrf_scores[url] = rrf_scores.get(url, 0.0) + (1.0 / (k + rank + 1))
        if url not in by_url:
            by_url[url] = {**row, "_vector_score": 0.0}

    entity_set = {str(n).lower() for n in (entity_filter or [])}
    ranked: list[dict] = []
    for url, row in by_url.items():
        if not allow_recap and row.get("event_type") == "price_recap":
            continue
        if scope.news_topics and mode in ("event_only", "event_plus_entities") and not _topic_match(
            row, scope.news_topics
        ):
            continue
        raw_text = str(row.get("scraped_text") or row.get("snippet") or "")
        snippet = _trim_snippet(raw_text, settings.snippet_chars)
        article_entities = {str(n).lower() for n in (row.get("entity_names") or [])}
        title_lower = str(row.get("title") or "").lower()
        exact_entity_match = bool(entity_set & article_entities) or any(n in title_lower for n in entity_set)
        impact = int(row.get("max_impact") or 0)
        base_rrf = rrf_scores.get(url, 0.0)
        combined_score = base_rrf + (0.05 if exact_entity_match else 0.0) + (0.01 * impact)
        ranked.append(
            {
                "url": url,
                "title": row.get("title"),
                "source": row.get("source"),
                "published_at": row.get("published_at"),
                "entity_names": row.get("entity_names") or [],
                "sector_names": row.get("sector_names") or [],
                "snippet": snippet,
                "max_impact": impact,
                "_vector_score": float(row.get("_vector_score") or 0.0),
                "_rrf_score": combined_score,
            }
        )

    ranked.sort(key=lambda item: (item["_rrf_score"], item["max_impact"]), reverse=True)
    final: list[dict] = []
    for item in ranked:
        if len(final) >= 5:
            break
        final.append(item)

    if query_log is not None:
        query_log.write(f"RETRIEVE kept={len(final)} dropped={len(ranked) - len(final)}")
        query_log.log_articles_block("scoped_news", final, snippet_limit=400)

    return final
