"""Planner-driven multi-query macro retrieval with theme clustering (specific macro topics)."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, TYPE_CHECKING

from news_rag.article_pool import article_dedupe_key
from news_rag.market_pulse import (
    MARKET_PULSE_DEFAULT_WINDOW_DAYS,
    MARKET_PULSE_RETRY_WINDOW_DAYS,
    cluster_articles_by_theme,
    market_pulse_representatives_from_clusters,
    market_pulse_window_days,
)
from news_rag.parse import parse_time_window
from news_rag.query_plan import ScopeRefinement

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

MACRO_ENHANCED_TOP_CLUSTERS = 6


def _query_variants(semantic: str, question: str) -> list[str]:
    base = (semantic or question or "").strip()
    if not base:
        base = "India macro financial markets"
    seen: set[str] = set()
    out: list[str] = []
    for q in (
        base,
        f"India RBI rates rupee liquidity {base}",
        f"India FII DII equity flows {base}",
        f"India crude oil inflation bond yields {base}",
        f"India banking credit corporate earnings {base}",
    ):
        key = q.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
    return out[:5]


def _fetch_macro_query(
    semantic: str,
    question: str,
    *,
    window_days: int,
    query_log: QueryLogger | None,
    filter_kwargs: dict[str, Any],
) -> list[dict[str, Any]]:
    from news_rag.scoped_retrieve import retrieve_scoped_news

    scope = ScopeRefinement(search_mode="event_only", news_topics=[])
    rows = retrieve_scoped_news(
        semantic,
        scope=scope,
        question=question,
        window_days=window_days,
        query_log=query_log,
        ignore_question_time_hints=True,
        **filter_kwargs,
    )
    for row in rows:
        row["_macro_enhanced_query"] = semantic[:80]
        row["_news_layer"] = "macro"
    return rows


def run_macro_news_enhanced(
    question: str,
    *,
    semantic_query: str = "",
    window_days: int | None = None,
    query_log: QueryLogger | None = None,
    per_query_cap: int = 8,
    **filter_kwargs: Any,
) -> dict[str, Any]:
    started = time.perf_counter()
    wd = market_pulse_window_days(question, window_days or MARKET_PULSE_DEFAULT_WINDOW_DAYS)
    variants = _query_variants(semantic_query, question)

    def _collect(wdays: int) -> dict[str, dict[str, Any]]:
        pool: dict[str, dict[str, Any]] = {}
        if not variants:
            return pool
        with ThreadPoolExecutor(max_workers=max(1, min(5, len(variants)))) as ex:
            futs = {
                ex.submit(
                    _fetch_macro_query,
                    sem,
                    question,
                    window_days=wdays,
                    query_log=query_log,
                    filter_kwargs=filter_kwargs,
                ): sem
                for sem in variants
            }
            for fut in as_completed(futs):
                try:
                    for row in fut.result()[:per_query_cap]:
                        key = article_dedupe_key(row)
                        if not key:
                            continue
                        prev = pool.get(key)
                        if prev is None or int(row.get("max_impact") or 0) > int(prev.get("max_impact") or 0):
                            pool[key] = row
                except Exception as exc:
                    if query_log is not None:
                        query_log.write(f"MACRO_ENHANCED query_fail {exc}")
        return pool

    pool = _collect(wd)
    if not pool:
        wide = min(MARKET_PULSE_RETRY_WINDOW_DAYS, wd + 30)
        pool = _collect(wide)
        if pool:
            wd = wide

    articles = list(pool.values())
    clusters = cluster_articles_by_theme(articles)[:MACRO_ENHANCED_TOP_CLUSTERS]
    cluster_payloads = [
        {
            "id": c.cluster_id,
            "label": c.label,
            "theme_key": c.theme_key,
            "article_count": c.article_count,
            "score": round(c.score, 3),
            "sectors": c.sectors,
            "entities": c.entities,
            "articles": c.articles,
        }
        for c in clusters
    ]
    representatives = market_pulse_representatives_from_clusters(
        cluster_payloads, limit=MACRO_ENHANCED_TOP_CLUSTERS
    )
    published_from, published_to, window_label = parse_time_window(
        "", date_from=None, date_to=None, default_days=wd
    )
    flat: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cl in clusters:
        for art in cl.articles:
            key = article_dedupe_key(art)
            if key and key not in seen:
                seen.add(key)
                flat.append(art)

    elapsed = (time.perf_counter() - started) * 1000
    if query_log is not None:
        query_log.write(
            f"MACRO_ENHANCED queries={len(variants)} articles={len(articles)} "
            f"clusters={len(clusters)} window_days={wd}"
        )

    return {
        "ok": True,
        "data": {
            "semantic_query": semantic_query or question,
            "window_days": wd,
            "window_label": window_label,
            "published_from": published_from,
            "published_to": published_to,
            "articles": flat,
            "representative_articles": representatives,
            "clusters": cluster_payloads,
        },
        "error": "",
        "elapsed_ms": elapsed,
    }
