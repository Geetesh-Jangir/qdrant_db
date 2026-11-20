"""Yahoo 1-week % change ending on last settled session (exclude today IST)."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from ai_insight.common.time_ist import ist_now

logger = logging.getLogger(__name__)


def _bars_before_today(hist, today: date) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, row in hist.dropna(subset=["Close"]).iterrows():
        d = index.date()
        if d >= today:
            continue
        rows.append({"date": d.isoformat(), "close": float(row["Close"])})
    return rows


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