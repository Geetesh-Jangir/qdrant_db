"""Portfolio UI cards from date-keyed market / holding JSON stores."""

from __future__ import annotations

from typing import Any

from ai_insight.common.market_daily_store import load_market_daily
from ai_insight.portfolio_insights.config import COMMON_IDS

_COMMON_LABELS = {
    "market_driver_digest": "Market Today",
    "fii_dii_flow_narrative": "Institutional Flows",
    "sector_leaderboard": "Sector Pulse",
}


def load_common_cards(trading_date: str, limit: int) -> list[dict[str, Any]]:
    snap = load_market_daily(trading_date)
    if not snap:
        return []
    by_id = {item.get("insight_id"): item for item in (snap.get("common") or []) if item.get("insight_id")}
    cards: list[dict[str, Any]] = []
    for insight_id in COMMON_IDS[:limit]:
        item = by_id.get(insight_id)
        if not item or item.get("status") not in ("ok", "degraded"):
            continue
        cards.append(
            {
                "insight_id": insight_id,
                "section": insight_id,
                "trading_date": trading_date,
                "status": item.get("status"),
                "headline": item.get("headline") or "",
                "body": item.get("body") or item.get("insight") or "",
                "chips": [],
                "usage": {
                    "input_tokens": item.get("input_tokens") or 0,
                    "output_tokens": item.get("output_tokens") or 0,
                    "calls": item.get("calls") or 0,
                },
                "sources": [{"url": a.get("url"), "published_at": a.get("published_at")} for a in (item.get("articles") or [])],
            }
        )
    return cards