"""Yahoo quotes: daily history plus last price when the session is live."""

from __future__ import annotations

from datetime import date
from typing import Any


def history_closes(ticker: str, *, period: str = "1mo") -> list[dict[str, Any]]:
    try:
        import yfinance as yf
    except ImportError:
        return []
    try:
        hist = yf.Ticker(ticker).history(period=period, interval="1d", prepost=True, actions=False)
    except Exception:
        return []
    if hist is None or hist.empty:
        return []
    rows: list[dict[str, Any]] = []
    for index, row in hist.dropna(subset=["Close"]).iterrows():
        rows.append(
            {
                "date": str(index.date()),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
            }
        )
    return rows


def latest_quote(ticker: str, trading_date: date | None = None) -> tuple[float | None, str | None]:
    """Last price from fast_info when possible, else the latest daily close."""
    try:
        import yfinance as yf
    except ImportError:
        return None, None
    t = yf.Ticker(ticker)
    price: float | None = None
    try:
        info = t.fast_info
        raw = getattr(info, "last_price", None) or getattr(info, "lastPrice", None)
        if raw is None and isinstance(info, dict):
            raw = info.get("last_price") or info.get("lastPrice")
        if raw is not None:
            price = float(raw)
    except Exception:
        price = None
    day = trading_date.isoformat() if trading_date else None
    if price is not None:
        return price, day
    rows = history_closes(ticker, period="5d")
    if not rows:
        return None, None
    last = rows[-1]
    return float(last["close"]), str(last["date"])