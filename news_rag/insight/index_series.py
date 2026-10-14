"""Sector / benchmark index returns with disk cache."""

from __future__ import annotations

import json
import time
from datetime import timedelta
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
        # `days` are calendar days: use the last bar on or before (last date - days)
        cutoff = hist.index[-1] - timedelta(days=max(days, 5))
        earlier = hist[hist.index <= cutoff]
        start = float(earlier["Close"].iloc[-1]) if not earlier.empty else float(hist["Close"].iloc[0])
        if start == 0:
            return None
        return round(((end - start) / start) * 100.0, 2)
    except Exception:
        return None


# ETFs that track a sector index and have clean price history when the index symbol does not.
_SECTOR_ETF_FALLBACK = {
    "automobiles": ("AUTOBEES.NS", "Nifty Auto (via ETF)"),
    "auto components": ("AUTOBEES.NS", "Nifty Auto (via ETF)"),
    "banks": ("BANKBEES.NS", "Nifty Bank (via ETF)"),
    "information technology": ("ITBEES.NS", "Nifty IT (via ETF)"),
    "it - software": ("ITBEES.NS", "Nifty IT (via ETF)"),
    "pharmaceuticals & biotechnology": ("PHARMABEES.NS", "Nifty Pharma (via ETF)"),
    "construction": ("INFRABEES.NS", "Nifty Infra (via ETF)"),
}


_RANK_SECTORS = (
    "Banks",
    "It - Software",
    "Pharmaceuticals & Biotechnology",
    "Automobiles",
    "Telecom - Services",
    "Petroleum Products",
    "Cement & Cement Products",
    "Diversified Fmcg",
)


def worst_sector_by_return(window_days: int = 365) -> tuple[str, float | None]:
    """Sector with the lowest index return over the window. Empty if none could be priced."""
    ranked: list[tuple[str, float]] = []
    for name in _RANK_SECTORS:
        row = index_return_for_sector(name, window_days=window_days)
        if row.get("substituted_broad_index"):
            continue
        pct = row.get("return_pct")
        if isinstance(pct, (int, float)):
            ranked.append((name, float(pct)))
    if not ranked:
        return "", None
    ranked.sort(key=lambda item: item[1])
    return ranked[0]


def benchmark_return_for_scheme(
    benchmark_name: str,
    *,
    category: str = "",
    window_days: int = 30,
) -> dict[str, Any]:
    """Scheme benchmark from the fund catalog; uses Nifty 50 when the index has no price feed."""
    raw = (benchmark_name or "").strip()
    low = raw.lower()
    cat = (category or "").lower()
    ticker = nifty50_ticker()
    label = raw or "Nifty 50"
    proxy_note = ""
    if "bse 100" in low or "large cap" in cat or "mid cap" in cat:
        proxy_note = " (Nifty 50 used as a tradable proxy for the move)"
    elif "nifty 50" not in low and "sensex" not in low and raw:
        proxy_note = " (Nifty 50 used as a broad-market proxy)"
    key = f"scheme_bench_{label}_{window_days}"
    cached = _read_cache(key)
    if cached is not None:
        return cached
    pct = _yf_return_pct(ticker, window_days)
    out = {
        "benchmark_label": label + proxy_note,
        "return_pct": pct,
        "yfinance_ticker": ticker,
        "window_days": window_days,
        "scheme_benchmark_raw": raw,
    }
    if pct is not None:
        _write_cache(key, out)
    return out


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
        etf = _SECTOR_ETF_FALLBACK.get(sector_label.strip().lower())
        if etf:
            etf_pct = _yf_return_pct(etf[0], window_days)
            if etf_pct is not None:
                ticker, label, pct = etf[0], etf[1], etf_pct
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
