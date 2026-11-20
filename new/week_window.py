"""Seven-day window helpers for equity fund week pipeline."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from ai_insight.common.time_ist import rolling_window
from news_pipeline.textutil import parse_time

EQUITY_WEEK_DAYS = 7

_PORTFOLIO_PCT_RE = re.compile(
    r",?\s*which makes up [\d.,]+% of your portfolio,?\s*",
    re.I,
)


def equity_week_window(trading_date: date | None = None) -> tuple[str, str]:
    from ai_insight.common.time_ist import ist_now

    day = trading_date or ist_now().date()
    return rolling_window(day, days=EQUITY_WEEK_DAYS)


def published_in_equity_week(published_at: str, window: tuple[str, str]) -> bool:
    ts = parse_time(published_at)
    start = parse_time(window[0])
    end = parse_time(window[1])
    if ts is None or start is None or end is None:
        return bool(str(published_at or "").strip())
    return start <= ts <= end


def filter_articles_to_week(
    articles: list[dict[str, Any]],
    window: tuple[str, str],
) -> list[dict[str, Any]]:
    if not articles:
        return []
    return [
        a
        for a in articles
        if isinstance(a, dict) and published_in_equity_week(str(a.get("published_at") or ""), window)
    ]


def strip_portfolio_pct_prose(text: str) -> str:
    if not text:
        return text
    cleaned = _PORTFOLIO_PCT_RE.sub(" ", text)
    return re.sub(r"\s{2,}", " ", cleaned).strip()