"""O(1) lookup for NSE sector index yfinance symbols (see nse_sector_indices_yfinance.json)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from news_pipeline.config import repo_root

DEFAULT_JSON = "data/fund_holdings_aggregate/nse_sector_indices_yfinance.json"
NIFTY_50_KEY = "Nifty 50"


@lru_cache(maxsize=1)
def _document(path: str | None = None) -> dict[str, Any]:
    rel = path or DEFAULT_JSON
    full = repo_root() / rel
    with full.open(encoding="utf-8") as handle:
        return json.load(handle)


def clear_sector_index_cache() -> None:
    _document.cache_clear()


def sector_index_entry(sector_name: str, *, path: str | None = None) -> dict[str, Any] | None:
    """Return index metadata for a pipeline sector label, or None if unknown."""
    by_sector = _document(path).get("by_sector") or {}
    return by_sector.get(sector_name)


def sector_yfinance_ticker(sector_name: str, *, path: str | None = None) -> str | None:
    row = sector_index_entry(sector_name, path=path)
    if not row:
        return None
    ticker = row.get("yfinance_ticker")
    return ticker if isinstance(ticker, str) and ticker.strip() else None


def benchmark_entry(
    name: str = NIFTY_50_KEY,
    *,
    path: str | None = None,
) -> dict[str, Any] | None:
    benchmarks = _document(path).get("benchmarks") or {}
    return benchmarks.get(name)


def nifty50_ticker(*, path: str | None = None) -> str:
    row = benchmark_entry(NIFTY_50_KEY, path=path)
    if not row:
        raise KeyError(f"benchmark {NIFTY_50_KEY!r} missing from {DEFAULT_JSON}")
    ticker = row.get("yfinance_ticker")
    if not isinstance(ticker, str) or not ticker.strip():
        raise ValueError(f"benchmark {NIFTY_50_KEY!r} has no yfinance_ticker")
    return ticker
