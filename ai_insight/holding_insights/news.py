"""Top holding news from Qdrant with moderate gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from news_pipeline.textutil import parse_time

from ai_insight.common.qdrant_access import fetch_entity_rows
from ai_insight.common.time_ist import rolling_window
from ai_insight.holding_insights.config import (
    HOLDING_INSIGHT_GATE,
    HOLDING_LOOKBACK_DAYS,
    HOLDING_NEWS_EXTENDED_DAYS,
    HOLDING_NEWS_MIN_ARTICLES,
    HOLDING_NEWS_LOOKBACK_DAYS,
    HOLDING_NEWS_TOP_K,
)


@dataclass
class NewsArticle:
    article_id: str
    published_at: str
    headline: str
    full_text: str
    relevancy_score: int
    sentiment: str
    nav_impact_display: int
    signed_score: int


@dataclass
class NewsBundle:
    articles: list[NewsArticle] = field(default_factory=list)
    scanned: int = 0
    after_gate: int = 0
    window: tuple[str, str] = ("", "")


def news_window(trading_date: date) -> tuple[str, str]:
    return rolling_window(trading_date, days=HOLDING_LOOKBACK_DAYS)


def _published_in_window(published_at: str, window: tuple[str, str]) -> bool:
    ts = parse_time(published_at)
    start = parse_time(window[0])
    end = parse_time(window[1])
    if ts is None or start is None or end is None:
        return bool(published_at.strip())
    return start <= ts <= end


def _rows_to_articles(
    rows: list[dict[str, Any]],
    *,
    window: tuple[str, str],
    k: int,
    prefer_window: tuple[str, str] | None = None,
) -> list[NewsArticle]:
    prefer = prefer_window or window

    def sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
        entity = row.get("entity") or {}
        article = row.get("article") or {}
        published = str(article.get("published_at") or "")
        ts = parse_time(published)
        ts_num = ts.timestamp() if ts else 0.0
        in_prefer = 1 if _published_in_window(published, prefer) else 0
        return (
            in_prefer,
            int(entity.get("signed_score") or 0),
            int(entity.get("relevance") or 0),
            int(entity.get("impact") or 0),
            float(entity.get("about_this_name") or 0.0),
            ts_num,
        )

    ordered = sorted(rows, key=sort_key, reverse=True)
    seen: set[str] = set()
    out: list[NewsArticle] = []
    for row in ordered:
        if len(out) >= k:
            break
        article = row.get("article") or {}
        entity = row.get("entity") or {}
        published = str(article.get("published_at") or "")
        if not _published_in_window(published, window):
            continue
        url = str(article.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        impact = int(entity.get("impact") or 0)
        out.append(
            NewsArticle(
                article_id=url,
                published_at=str(article.get("published_at") or ""),
                headline=str(article.get("title") or ""),
                full_text=str(article.get("scraped_text") or article.get("full_text") or ""),
                relevancy_score=int(entity.get("relevance") or 0),
                sentiment=str(entity.get("direction") or "unclear"),
                nav_impact_display=impact,
                signed_score=int(entity.get("signed_score") or 0),
            )
        )
    return out


def _fetch_rows(entity_name: str, window: tuple[str, str], *, client: Any = None):
    return fetch_entity_rows(
        "holding",
        window,
        names=[entity_name],
        gate=HOLDING_INSIGHT_GATE,
        client=client,
        with_text=True,
    )


def get_top_news(
    entity_name: str,
    window: tuple[str, str],
    *,
    client: Any = None,
    k: int = HOLDING_NEWS_TOP_K,
    trading_date: date | None = None,
) -> NewsBundle:
    primary = window
    result = _fetch_rows(entity_name, primary, client=client)
    scanned = result.diagnostics.articles_scanned
    rows = list(result.rows)
    effective_window = primary

    articles = _rows_to_articles(rows, window=primary, k=k, prefer_window=primary)
    if (
        len(articles) < HOLDING_NEWS_MIN_ARTICLES
        and HOLDING_NEWS_EXTENDED_DAYS > HOLDING_LOOKBACK_DAYS
        and trading_date is not None
    ):
        extended = rolling_window(trading_date, days=HOLDING_NEWS_EXTENDED_DAYS)
        ext = _fetch_rows(entity_name, extended, client=client)
        scanned += ext.diagnostics.articles_scanned
        by_url = {str((r.get("article") or {}).get("url") or ""): r for r in rows}
        for row in ext.rows:
            url = str((row.get("article") or {}).get("url") or "")
            if url and url not in by_url:
                by_url[url] = row
        rows = list(by_url.values())
        effective_window = extended
        articles = _rows_to_articles(rows, window=extended, k=k, prefer_window=primary)

    bundle = NewsBundle(
        scanned=scanned,
        after_gate=len(rows),
        window=effective_window,
    )
    bundle.articles = articles
    return bundle