"""Entity-scored news for gainer/loser stocks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Any, Literal

from news_rag.holdings_market import fetch_dedicated_holding_news
from news_rag.news_entity_resolve import resolve_corpus_entity
from news_rag.query_plan import ScopeRefinement
from news_rag.scoped_retrieve import retrieve_scoped_news

from ai_insight.common.time_ist import ist_now
from ai_insight.holding_insights.news import get_top_news, news_window

from new.news_filter import merge_article_pool, rank_and_pick_articles

Move = Literal["up", "down"]


def _slim_article(row: dict[str, Any]) -> dict[str, Any]:
    from news_rag.snippet_clean import article_body_for_llm

    body = article_body_for_llm(row, limit=0) or str(row.get("snippet") or "").strip()
    return {
        "title": str(row.get("title") or "")[:220],
        "snippet": str(row.get("snippet") or "")[:420],
        "full_text": body,
        "url": str(row.get("url") or ""),
        "published_at": row.get("published_at"),
        "direction": row.get("direction") or "unclear",
        "_pick_score": row.get("_pick_score"),
    }


def _holding_rows(entity_name: str, trading_date: date | None = None) -> list[dict[str, Any]]:
    today = trading_date or ist_now().date()
    window = news_window(today)
    bundle = get_top_news(entity_name, window, k=30)
    rows: list[dict[str, Any]] = []
    for art in bundle.articles:
        rows.append(
            {
                "title": art.headline,
                "scraped_text": art.full_text,
                "url": art.article_id,
                "published_at": art.published_at,
                "direction": art.sentiment,
                "max_impact": art.nav_impact_display,
                "relevancy_score": art.relevancy_score,
            }
        )
    return rows


def _scoped_rows(
    entity: str,
    instrument_name: str,
    move: Move,
    *,
    fund_name: str,
    window_days: int,
) -> list[dict[str, Any]]:
    scope = ScopeRefinement(news_entities=[entity], news_topics=[], search_mode="event_plus_entities")
    if move == "up":
        query = f"{entity} India shares earnings upgrade order wins last week"
    else:
        query = f"{entity} India shares fall profit warning downgrade last week"
    return retrieve_scoped_news(
        query,
        scope=scope,
        question=f"{fund_name} {instrument_name}",
        window_days=window_days,
        min_impact=1,
        vector_limit=40,
    )


def fetch_stock_news(
    instrument_name: str,
    move: Move,
    *,
    fund_name: str = "",
    window_days: int = 10,
    limit: int = 8,
) -> list[dict[str, Any]]:
    entity = resolve_corpus_entity(instrument_name) or instrument_name
    gated = _holding_rows(entity)
    scoped = _scoped_rows(entity, instrument_name, move, fund_name=fund_name, window_days=window_days)
    legacy = fetch_dedicated_holding_news(
        instrument_name,
        fund_name or instrument_name,
        window_days=max(window_days, 10),
        limit=limit + 12,
    )
    pool = merge_article_pool(gated, scoped, legacy)
    ranked = rank_and_pick_articles(instrument_name, move, pool, limit=limit)
    return [_slim_article(r) for r in ranked]


def _one_mover(
    row: dict[str, Any],
    move: Move,
    *,
    fund_name: str,
    window_days: int,
    per_stock: int,
) -> dict[str, Any]:
    name = str(row.get("instrument_name") or "")
    articles = fetch_stock_news(
        name,
        move,
        fund_name=fund_name,
        window_days=window_days,
        limit=per_stock,
    )
    return {
        "instrument_name": name,
        "move": move,
        "change_1w_pct": row.get("change_1w_pct"),
        "impact_1w_pct": row.get("impact_1w_pct"),
        "percentage": row.get("percentage"),
        "articles": articles,
        "usable_news": bool(articles),
    }


def news_for_movers(
    gainers: list[dict[str, Any]],
    losers: list[dict[str, Any]],
    *,
    fund_name: str,
    window_days: int = 10,
    per_stock: int = 8,
) -> list[dict[str, Any]]:
    tasks: list[tuple[dict[str, Any], Move]] = []
    for row in gainers:
        if row.get("instrument_name"):
            tasks.append((row, "up"))
    for row in losers:
        if row.get("instrument_name"):
            tasks.append((row, "down"))
    if not tasks:
        return []

    blocks: list[dict[str, Any]] = []
    workers = min(6, len(tasks))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(_one_mover, row, move, fund_name=fund_name, window_days=window_days, per_stock=per_stock): row
            for row, move in tasks
        }
        for fut in as_completed(futs):
            try:
                blocks.append(fut.result())
            except Exception:
                row = futs[fut]
                blocks.append(
                    {
                        "instrument_name": row.get("instrument_name"),
                        "move": "up",
                        "change_1w_pct": row.get("change_1w_pct"),
                        "impact_1w_pct": row.get("impact_1w_pct"),
                        "percentage": row.get("percentage"),
                        "articles": [],
                        "usable_news": False,
                    }
                )
    blocks.sort(key=lambda b: abs(float(b.get("impact_1w_pct") or 0)), reverse=True)
    return blocks