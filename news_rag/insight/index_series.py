"""Sector / benchmark index returns with disk cache."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from lib.nse_sector_indices import nifty50_ticker, sector_yfinance_ticker

_ROOT = Path(__file__).resolve().parents[2]
_CACHE_DIR = _ROOT / "data" / "index_cache"
_TTL_HOURS = 6.0


def _cache_path(key: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in key)[:120]
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{safe}.json"


def _read_cache(key: str) -> dict[str, Any] | None:
    path = _cache_path(key)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        age = (time.time() - float(data.get("cached_at") or 0)) / 3600.0
        if age > _TTL_HOURS:
            return None
        return data
    except Exception:
        return None


def _write_cache(key: str, payload: dict[str, Any]) -> None:
    payload["cached_at"] = time.time()
    _cache_path(key).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _yf_return_pct(ticker: str, days: int) -> float | None:
    if not ticker:
        return None
    try:
        import yfinance as yf
    except ImportError:
        return None
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2y")
        if hist is None or hist.empty or len(hist) < 2:
            hist = t.history(period="max")
        if hist is None or hist.empty or len(hist) < 2:
            return None
        end = float(hist["Close"].iloc[-1])
        lookback = min(max(days, 5), len(hist) - 1)
        start = float(hist["Close"].iloc[-1 - lookback])
        if start == 0:
            return None
        return round(((end - start) / start) * 100.0, 2)
    except Exception:
        return None


def index_return_for_sector(
    sector_label: str,
    *,
    window_days: int = 180,
) -> dict[str, Any]:
    """Return index performance for a sector label; falls back to Nifty 50."""
    key = f"{sector_label}_{window_days}"
    cached = _read_cache(key)
    if cached is not None:
        return cached

    ticker = sector_yfinance_ticker(sector_label) or ""
    label = sector_label
    substituted = False
    if not ticker:
        ticker = nifty50_ticker()
        label = "Nifty 50 (broad market proxy)"
        substituted = True

    pct = _yf_return_pct(ticker, window_days)
    if pct is None and not substituted:
        ticker = nifty50_ticker()
        label = "Nifty 50 (broad proxy; sector index history unavailable)"
        substituted = True
        pct = _yf_return_pct(ticker, window_days)
    out = {
        "sector_label": sector_label,
        "benchmark_label": label,
        "yfinance_ticker": ticker,
        "return_pct": pct,
        "window_days": window_days,
        "substituted_broad_index": substituted,
    }
    if pct is not None:
        _write_cache(key, out)
    return out
