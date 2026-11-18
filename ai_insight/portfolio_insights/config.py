from __future__ import annotations

import os

COMMON_IDS = ("market_driver_digest", "fii_dii_flow_narrative", "sector_leaderboard")
SECTOR_BUNDLE_ID = "sector_index_insights"


def _int(key: str, default: int) -> int:
    raw = os.environ.get(key, "").strip()
    return int(raw) if raw.isdigit() else default


MAX_COMMON = _int("PORTFOLIO_INSIGHTS_MAX_COMMON", 3)
MAX_SECTOR = _int("PORTFOLIO_INSIGHTS_MAX_SECTOR", 3)
MAX_HOLDING = _int("PORTFOLIO_INSIGHTS_MAX_HOLDING", 3)