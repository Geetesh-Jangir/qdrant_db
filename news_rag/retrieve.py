"""Hybrid retrieval: intent-driven branching, vector search, impact scroll, rank."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from news_rag.config import get_settings
from news_rag.embed import embed_query
from news_rag.entity_index import corpus_entity_names
from news_rag.fund_search import extract_top_holdings, extract_top_sectors, lookup_extracted_fund
from news_rag.parse import (
    ParsedQuery,
    extract_stock_hint,
    parse_time_window,
    resolve_entities,
    split_multi_questions,
)
from news_rag.qdrant_reader import (
    QdrantReader,
    build_filter,
    describe_filters_for_log,
    filter_spec,
)
from news_rag.query_router import RouterResult, route_query

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
    router_override: RouterResult | None = None,
    query_log: QueryLogger | None = None,
) -> tuple[ParsedQuery, list[dict]]:
    settings = get_settings()

    # 1. Agent 1: Router
    t_router = time.perf_counter()
    router = router_override or route_query(question, query_log=query_log)
    if query_log is not None:
        query_log.log_step("query_router", time.perf_counter() - t_router, intent=router.intent)

    # 2. Fund Lookup on extracted entity only
    fund_detail = None
    is_ambiguous = False
    close_matches: list[str] = []
    if not router.fund.is_empty():
        fund_detail, is_ambiguous, close_matches = lookup_extracted_fund(
            isin=router.fund.isin,
            name=router.fund.name,
        )

    # 3. Determine time window
    effective_days = router.window_days if router.window_days and not (date_from or date_to) else settings.default_window_days
    published_from, published_to, window_label = parse_time_window(
        question,
        date_from=date_from,
        date_to=date_to,
        default_days=effective_days,
    )

    t0 = time.perf_counter()
    corpus = corpus_entity_names()
    if query_log is not None:
        query_log.log_step("corpus_entity_index", time.perf_counter() - t0, unique_names=len(corpus))

    # 4. Resolve explicit company entities from router
    extracted_companies = list(router.companies)
    if stock and stock not in extracted_companies:
        extracted_companies.append(stock)

    hint = extracted_companies[0] if extracted_companies else extract_stock_hint(question, stock)
    names, note = resolve_entities(hint, corpus)

    sub_questions = router.asked if router.asked else split_multi_questions(question)

    parsed = ParsedQuery(
        question=question.strip(),
        published_from=published_from,
        published_to=published_to,
        window_label=window_label,
        stock_hint=hint,
        entity_resolved=names,
        entity_match_note=note,
        intent=router.intent,
        fund_resolved=fund_detail,
        sub_questions=sub_questions,
        router_result=router,
        fund_ambiguous=is_ambiguous,
        close_funds=close_matches,
    )
    if query_log is not None:
        query_log.log_parsed(parsed)

    # 5. Intent-driven Branching
    intent = router.intent

    # Branch A: Concept queries — zero Qdrant queries
    if intent == "concept":
        if query_log is not None:
            query_log.write("retrieve_branch intent=concept skip_qdrant=true")
        return parsed, []

    # Branch B: Fund Facts queries (NAV, Holdings, Sectors) — zero Qdrant news queries
    if intent in ("fund_nav", "fund_holdings", "fund_sectors"):
        if query_log is not None:
            query_log.write(f"retrieve_branch intent={intent} fund_resolved={bool(fund_detail)} skip_qdrant=true")
        return parsed, []

    # Branch C: News & Event Retrieval
    reader = QdrantReader()
    allow_recap = _wants_price_recap(question)
    vector_rows: list[dict] = []
    impact_rows: list[dict] = []

    # Case 1: Fund News / Fund Event Impact
    if fund_detail and intent in ("fund_event_impact", "fund_news"):
        top_h = extract_top_holdings(fund_detail, limit=15)
        top_s = extract_top_sectors(fund_detail, limit=4)
        comp_matched = [h["name"] for h in top_h if h["name"] in corpus]
        sec_matched = [s["sector"] for s in top_s if s["sector"] in corpus]
        fund_entities = comp_matched + sec_matched

        vector_query_text = f"{question.strip()} {router.event_focus} {' '.join(comp_matched[:4])}".strip()
        vector = embed_query(vector_query_text)

        filter_kwargs = {
            "entity_names": fund_entities if fund_entities else None,
            "published_from": published_from,
            "published_to": published_to,
            "min_relevance": settings.min_relevance,
            "min_impact": min_impact if min_impact is not None else 1,
            "source": source or None,
            "direction": direction or None,
        }
        filt = build_filter(**filter_kwargs)
        vector_rows = reader.query_vector(vector, filt, settings.retrieve_vector_limit)

        if intent == "fund_news":
            # Multi-holding scan for general fund news
            existing_urls = {r.get("url") for r in vector_rows if r.get("url")}
            for comp in comp_matched[:8]:
                filt_comp = build_filter(**{**filter_kwargs, "entity_names": [comp]})
                rows = reader.scroll_filtered(filt_comp, 2)
                for r in rows:
                    u = r.get("url")
                    if u and u not in existing_urls:
                        impact_rows.append(r)
                        existing_urls.add(u)
        else:
            impact_rows = reader.scroll_filtered(filt, settings.retrieve_impact_limit)

    # Case 2: Single Stock, Sector, Macro, Bullion, General
    else:
        entity_filter = names if names else None
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
        vector = embed_query(question.strip())
        vector_rows = reader.query_vector(vector, filt, settings.retrieve_vector_limit)
        impact_rows = reader.scroll_filtered(filt, settings.retrieve_impact_limit)

    # 6. Reciprocal Rank Fusion (RRF) Ranking
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

    ranked: list[dict] = []
    skipped_recap = 0
    entity_set = {str(name).lower() for name in (names or [])}

    for url, row in by_url.items():
        if not allow_recap and row.get("event_type") == "price_recap":
            skipped_recap += 1
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

    final: list[dict] = []
    entity_counts: dict[str, int] = {}
    for item in ranked:
        ents = [str(e).lower() for e in item.get("entity_names") or []]
        primary_ent = ents[0] if ents else "unknown"
        if entity_counts.get(primary_ent, 0) < 3:
            final.append(item)
            entity_counts[primary_ent] = entity_counts.get(primary_ent, 0) + 1
        if len(final) >= settings.retrieve_max_articles:
            break

    if query_log is not None:
        if skipped_recap:
            query_log.write(f"post_filter skipped_price_recap={skipped_recap}")
        query_log.log_articles_block("ranked_for_llm", final, snippet_limit=settings.snippet_chars)

    return parsed, final
