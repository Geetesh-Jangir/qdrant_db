"""Date-keyed holding-insights snapshots for portfolio matching."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_insight.holding_insights.atomic_io import atomic_write_json
from ai_insight.holding_insights.config import holding_data_dir


def _daily_path(trading_date: str) -> Path:
    if len(trading_date) != 10 or trading_date[4] != "-" or trading_date[7] != "-":
        raise ValueError(f"trading_date must be YYYY-MM-DD, got {trading_date!r}")
    return holding_data_dir() / "daily" / f"{trading_date}.json"


def save_daily(trading_date: str, outcome: dict[str, Any]) -> Path:
    path = _daily_path(trading_date)
    atomic_write_json(path, outcome)
    return path


def load_daily(trading_date: str) -> dict[str, Any] | None:
    path = _daily_path(trading_date)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None