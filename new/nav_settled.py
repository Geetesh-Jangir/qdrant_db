"""NAV 1W change using last settled NAV (exclude today)."""

from __future__ import annotations

from datetime import date
from typing import Any

from ai_insight.common.time_ist import ist_now
from historical_data.nav_service import _calculate_window_stats

from new.week_window import EQUITY_WEEK_DAYS


def settled_nav_records(
    records_asc: list[dict[str, Any]],
    *,
    as_of: date | None = None,
) -> list[dict[str, Any]]:
    today = as_of or ist_now().date()
    today_s = today.isoformat()
    trimmed = list(records_asc)
    while trimmed and str(trimmed[-1].get("nav_date") or "") >= today_s:
        trimmed.pop()
    return trimmed


def nav_change_1w_settled(
    records_asc: list[dict[str, Any]],
    *,
    as_of: date | None = None,
) -> dict[str, Any] | None:
    trimmed = settled_nav_records(records_asc, as_of=as_of)
    if len(trimmed) < 2:
        return None
    return _calculate_window_stats(trimmed, days=EQUITY_WEEK_DAYS)


def nav_daily_week_settled(
    records_asc: list[dict[str, Any]],
    *,
    as_of: date | None = None,
) -> list[dict[str, Any]]:
    stats = nav_change_1w_settled(records_asc, as_of=as_of)
    if not stats:
        return []
    pts = stats.get("points")
    if isinstance(pts, list) and pts:
        return pts
    return []