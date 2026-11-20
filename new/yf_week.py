"""Yahoo 1-week % change ending on last settled session (exclude today IST)."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from ai_insight.common.time_ist import ist_now

logger = logging.getLogger(__name__)


def _bars_before_today(hist, today: date, *, with_volume: bool = False) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in hist.dropna(subset=["Close"]).iterrows():
        d = index.date()
        if d >= today:
            continue
        item: dict[str, Any] = {"date": d.isoformat(), "close": round(float(row["Close"]), 2)}
        if with_volume:
            vol = row.get("Volume")
            try:
                item["volume"] = int(vol) if vol is not None and vol == vol else None
            except (TypeError, ValueError):
                item["volume"] = None
        rows.append(item)
    return rows


def _history_settled_bars(sym: str, *, today: date, with_volume: bool) -> list[dict[str, Any]]:
    try:
        import yfinance as yf
    except ImportError:
        return []
    try:
        hist = yf.Ticker(sym).history(period="2mo", interval="1d", actions=False)
    except Exception as exc:
        logger.debug("yfinance history failed %s: %s", sym, exc)
        return []
    if hist is None or hist.empty:
        return []
    return _bars_before_today(hist, today, with_volume=with_volume)


def stock_change_1w_settled(ticker: str, *, as_of: date | None = None) -> float | None:
    try:
        import yfinance as yf
    except ImportError:
        return None
    today = as_of or ist_now().date()
    for sym in [ticker] if ticker.endswith((".NS", ".BO")) else [f"{ticker}.NS", f"{ticker}.BO"]:
        try:
            hist = yf.Ticker(sym).history(period="2mo", interval="1d", actions=False)
        except Exception as exc:
            logger.debug("yfinance history failed %s: %s", sym, exc)
            continue
        if hist is None or hist.empty:
            continue
        bars = _bars_before_today(hist, today)
        if len(bars) < 6:
            continue
        end = bars[-1]["close"]
        start = bars[-6]["close"]
        if start <= 0:
            continue
        return round(((end - start) / start) * 100.0, 2)
    return None


def stock_daily_week_settled(
    ticker: str,
    *,
    as_of: date | None = None,
    trading_days: int = 6,
) -> list[dict[str, Any]]:
    """Daily close (+ volume) for the last settled week, excluding today IST."""
    today = as_of or ist_now().date()
    want = max(2, min(int(trading_days), 10))
    for sym in [ticker] if ticker.endswith((".NS", ".BO")) else [f"{ticker}.NS", f"{ticker}.BO"]:
        bars = _history_settled_bars(sym, today=today, with_volume=True)
        if len(bars) < want:
            continue
        return bars[-want:]
    return []