"""Settings for holding insights (moderate news gate, parallelism)."""

from __future__ import annotations

import os
from pathlib import Path

from ai_insight.common.config import _REPO_ROOT, load_config
from ai_insight.common.qdrant_access import GateConfig

HOLDING_INSIGHT_GATE = GateConfig(
    min_relevance=1,
    min_impact=1,
    min_about=0.25,
    drop_event_types=("price_recap",),
    opinion_min_impact=2,
)

HOLDING_LOOKBACK_DAYS = 7
HOLDING_NEWS_EXTENDED_DAYS = 14
HOLDING_NEWS_MIN_ARTICLES = 5
HOLDING_NEWS_LOOKBACK_DAYS = HOLDING_LOOKBACK_DAYS
HOLDING_PRICE_BARS = 7
HOLDING_NEWS_TOP_K = 20
HOLDING_PARALLEL = 5
MAX_STOCK_LIMIT = 99

TOP_HOLDINGS_PATH = _REPO_ROOT / "data" / "fund_holdings_aggregate" / "top_100_holdings.json"


def holding_data_dir() -> Path:
    return load_config().data_dir / "holding_insights"


def llm_allow_fallback() -> bool:
    return os.environ.get("HOLDING_INSIGHT_LLM_ALLOW_FALLBACK", "true").lower() in {"1", "true", "yes", "on"}