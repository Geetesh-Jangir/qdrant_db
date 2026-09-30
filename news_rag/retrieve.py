"""Hybrid retrieval: filter, vector search, impact scroll, rank."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from news_rag.config import get_settings
from news_rag.embed import embed_query
from news_rag.entity_index import corpus_entity_names
from news_rag.parse import (
    ParsedQuery,
    classify_query_intent,
    extract_stock_hint,
    parse_time_window,
    resolve_entities,
)
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

    # Resolve Fund & Sub-Questions
    from news_rag.fund_search import extract_top_holdings, extract_top_sectors, get_fund_index
    from news_rag.parse import split_multi_questions
    fund_index = get_fund_index()
    fund_detail = fund_index.resolve_fund_from_text(question)

    sub_questions = split_multi_questions(question)
    intent = classify_query_intent(question, hint, names, fund_resolved=fund_detail)

    vector_query_text = question.strip()

    # If a fund is resolved and no explicit single company was requested, focus on fund top holdings & sectors
    if fund_detail and not names:
        top_h = extract_top_holdings(fund_detail, limit=15)
        top_s = extract_top_sectors(fund_detail, limit=4)
        h_names = [h["name"] for h in top_h if h.get("name")]
        s_names = [s["sector"] for s in top_s if s.get("sector")]
        
        matched_fund_entities = [e for e in (h_names + s_names) if e in corpus]
        resolved_for_parsed = matched_fund_entities if matched_fund_entities else h_names[:5]
        entity_filter = matched_fund_entities if matched_fund_entities else None
        
        # Guide vector search with fund holding keywords
        vector_query_text = f"{question.strip()} {' '.join(h_names[:4])} {' '.join(s_names[:2])}".strip()
    else:
        resolved_for_parsed = names

    parsed = ParsedQuery(
        question=question.strip(),
        published_from=published_from,
        published_to=published_to,
        window_label=window_label,
        stock_hint=hint,
        entity_resolved=resolved_for_parsed,
        entity_match_note=note,
        intent=intent,
        fund_resolved=fund_detail,
        sub_questions=sub_questions,
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
        "intent": intent,
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
    vector = embed_query(vector_query_text)
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
    if fund_detail and not names:
        # Prioritize company-specific holding articles across multiple holdings first, then fallback to sector-level news
        top_h = extract_top_holdings(fund_detail, limit=20)
        top_s = extract_top_sectors(fund_detail, limit=4)
        comp_matched = [h["name"] for h in top_h if h["name"] in corpus]
        sec_matched = [s["sector"] for s in top_s if s["sector"] in corpus]

        impact_rows = []
        existing_urls = set()

        # Balance scroll across distinct holding companies (up to 2 articles per holding to maximize entity diversity)
        for comp in comp_matched:
            filt_comp = build_filter(**{**filter_kwargs, "entity_names": [comp]})
            rows = reader.scroll_filtered(filt_comp, 2)
            for r in rows:
                u = r.get("url")
                if u and u not in existing_urls:
                    impact_rows.append(r)
                    existing_urls.add(u)

        remaining = max(0, settings.retrieve_impact_limit - len(impact_rows))
        if remaining > 0 and sec_matched:
            for sec in sec_matched:
                filt_sec = build_filter(**{**filter_kwargs, "entity_names": [sec]})
                sec_rows = reader.scroll_filtered(filt_sec, 2)
                for sr in sec_rows:
                    u = sr.get("url")
                    if u and u not in existing_urls:
                        impact_rows.append(sr)
                        existing_urls.add(u)
    else:
        impact_rows = reader.scroll_filtered(filt, settings.retrieve_impact_limit)

    if query_log is not None:
        query_log.log_step(
            "qdrant_scroll_filtered",
            time.perf_counter() - t3,
            hits=len(impact_rows),
            limit=settings.retrieve_impact_limit,
        )
        query_log.log_articles_block("qdrant_scroll", impact_rows)

    # Calculate Reciprocal Rank Fusion (RRF) scores
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
        else:
            by_url[url].update({k_v: v_v for k_v, v_v in row.items() if k_v not in by_url[url] or not by_url[url].get(k_v)})

    if query_log is not None:
        query_log.write(f"merge unique_urls={len(by_url)} rrf_candidates={len(rrf_scores)}")

    ranked: list[dict] = []
    skipped_recap = 0
    entity_set = {str(name).lower() for name in (resolved_for_parsed or names or [])}

    for url, row in by_url.items():
        if not allow_recap and row.get("event_type") == "price_recap":
            skipped_recap += 1
            continue

        raw_text = str(row.get("scraped_text") or row.get("snippet") or "")
        snippet = _trim_snippet(raw_text, settings.snippet_chars)
        
        # Entity match bonus
        article_entities = {str(n).lower() for n in (row.get("entity_names") or [])}
        title_lower = str(row.get("title") or "").lower()
        exact_entity_match = bool(entity_set & article_entities) or any(n in title_lower for n in entity_set)
        
        impact = int(row.get("max_impact") or 0)
        base_rrf = rrf_scores.get(url, 0.0)
        
        # Combined score with entity boost and business impact weight
        combined_score = base_rrf + (0.05 if exact_entity_match else 0.0) + (0.01 * impact)

        ranked.append(
            {
                "url": url,
                "title": row.get("title"),
                "source": row.get("source"),
                "published_at": row.get("published_at"),
                "entity_names": row.get("entity_names") or [],
                "primary_industry": row.get("primary_industry") or "",
                "max_impact": impact,
                "max_relevance": int(row.get("max_relevance") or 0),
                "direction": row.get("direction") or "",
                "event_type": row.get("event_type") or "",
                "snippet": snippet,
                "_vector_score": float(row.get("_vector_score") or 0.0),
                "_rrf_score": combined_score,
                "_exact_match": exact_entity_match,
            }
        )

    # Sort candidates by combined RRF score, impact, vector score, and recency
    ranked.sort(
        key=lambda item: (
            1 if item["_exact_match"] else 0,
            item["_rrf_score"],
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
