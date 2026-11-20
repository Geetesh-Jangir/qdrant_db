"""Sector-level news for detected mover clusters (layered Qdrant retrieval)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Any, Literal

from news_rag.holdings_market import _slim_article

from ai_insight.common.time_ist import ist_now

from new.sector_clusters import SectorCluster
from new.week_window import EQUITY_WEEK_DAYS, equity_week_window, filter_articles_to_week

SECTOR_NEWS_PER_CLUSTER = 5
SECTOR_NEWS_EXTENDED_DAYS = 21
SECTOR_NEWS_MIN_ARTICLES = 3
DEFAULT_WINDOW_DAYS = EQUITY_WEEK_DAYS

Move = Literal["positive", "negative", "unclear"]


def _direction_for_side(side: str) -> str | None:
    if side == "up":
        return "positive"
    if side == "down":
        return "negative"
    return None


def _filter_by_direction(articles: list[dict[str, Any]], side: str) -> list[dict[str, Any]]:
    want = _direction_for_side(side)
    if not want:
        return articles
    aligned = [a for a in articles if str(a.get("direction") or "").lower() == want]
    return aligned if len(aligned) >= 2 else articles


def _week_filter_window(trading_date: date | None, window_days: int) -> tuple[str, str]:
    day = trading_date or ist_now().date()
    if int(window_days) == EQUITY_WEEK_DAYS:
        return equity_week_window(day)
    from ai_insight.common.time_ist import rolling_window

    return rolling_window(day, days=max(1, min(int(window_days), EQUITY_WEEK_DAYS)))


def _fetch_layered(
    sector_key: str,
    *,
    question: str,
    window_days: int,
    direction: str | None,
    publish_window: tuple[str, str],
) -> list[dict[str, Any]]:
    from news_rag.tools import run_layered_news

    kwargs: dict[str, Any] = {
        "layer": "sector_news",
        "semantic_query": f"{sector_key} India sector earnings outlook",
        "question": question,
        "entity_filters": [sector_key],
        "window_days": window_days,
    }
    if direction:
        kwargs["direction"] = direction
    payload = run_layered_news(**kwargs)
    raw: list[Any] = []
    if isinstance(payload, dict) and payload.get("ok"):
        data = payload.get("data")
        if isinstance(data, dict):
            raw = list(data.get("articles") or [])
    slim = [_slim_article(a) for a in raw if isinstance(a, dict)]
    return filter_articles_to_week(slim, publish_window)


def fetch_sector_cluster_news(
    cluster: SectorCluster,
    *,
    fund_name: str,
    window_days: int = DEFAULT_WINDOW_DAYS,
    per_cluster: int = SECTOR_NEWS_PER_CLUSTER,
    allow_extended_window: bool = False,
) -> dict[str, Any]:
    names = ", ".join(cluster.to_dict().get("holding_names") or [])[:120]
    side_word = "rose" if cluster.side == "up" else "fell"
    question = (
        f"{fund_name}: why did {cluster.sector_key} holdings ({names}) {side_word} this week?"
    )
    direction = _direction_for_side(cluster.side)
    publish_window = _week_filter_window(None, window_days)
    articles = _fetch_layered(
        cluster.sector_key,
        question=question,
        window_days=window_days,
        direction=direction,
        publish_window=publish_window,
    )
    articles = _filter_by_direction(articles, cluster.side)
    used = window_days
    if (
        allow_extended_window
        and len(articles) < SECTOR_NEWS_MIN_ARTICLES
        and window_days < SECTOR_NEWS_EXTENDED_DAYS
    ):
        ext_window = _week_filter_window(None, SECTOR_NEWS_EXTENDED_DAYS)
        extra = _fetch_layered(
            cluster.sector_key,
            question=question,
            window_days=SECTOR_NEWS_EXTENDED_DAYS,
            direction=direction,
            publish_window=ext_window,
        )
        extra = _filter_by_direction(extra, cluster.side)
        if len(extra) > len(articles):
            articles = extra
            used = SECTOR_NEWS_EXTENDED_DAYS
    articles = articles[: max(1, per_cluster)]
    base = cluster.to_dict()
    return {
        **base,
        "usable_news": bool(articles),
        "articles": articles,
        "window_days_used": used,
    }


def news_for_sector_clusters(
    clusters: list[SectorCluster],
    *,
    fund_name: str,
    window_days: int = DEFAULT_WINDOW_DAYS,
    per_cluster: int = SECTOR_NEWS_PER_CLUSTER,
    max_workers: int = 4,
    allow_extended_window: bool = False,
) -> list[dict[str, Any]]:
    if not clusters:
        return []
    workers = min(max_workers, len(clusters))
    blocks: list[dict[str, Any]] = []
    if workers <= 1:
        for cluster in clusters:
            blocks.append(
                fetch_sector_cluster_news(
                    cluster,
                    fund_name=fund_name,
                    window_days=window_days,
                    per_cluster=per_cluster,
                    allow_extended_window=allow_extended_window,
                )
            )
        return blocks
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {
            pool.submit(
                fetch_sector_cluster_news,
                cluster,
                fund_name=fund_name,
                window_days=window_days,
                per_cluster=per_cluster,
                allow_extended_window=allow_extended_window,
            ): cluster
            for cluster in clusters
        }
        by_sector: dict[tuple[str, str], dict[str, Any]] = {}
        for fut in as_completed(futs):
            cluster = futs[fut]
            try:
                by_sector[(cluster.sector_key, cluster.side)] = fut.result()
            except Exception:
                stub = cluster.to_dict()
                stub.update(usable_news=False, articles=[], window_days_used=window_days)
                by_sector[(cluster.sector_key, cluster.side)] = stub
    for cluster in clusters:
        key = (cluster.sector_key, cluster.side)
        if key in by_sector:
            blocks.append(by_sector[key])
    return blocks