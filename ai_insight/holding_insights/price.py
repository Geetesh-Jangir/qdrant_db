"""Session-aware Yahoo OHLCV snapshot for one stock."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from ai_insight.common.time_ist import ist_now
from ai_insight.common.yahoo_live import latest_quote
from ai_insight.holding_insights.config import HOLDING_PRICE_BARS


@dataclass
class DayBar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    session_state: str  # live | settled


def _consecutive_down_days(closes: list[float]) -> int:
    streak = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] < closes[i - 1]:
            streak += 1
        else:
            break
    return streak


def get_price_snapshot(yfinance_ticker: str, *, trading_date: date | None = None) -> dict[str, Any] | None:
    """Last 7 sessions OHLCV + 52w range and pattern hints. None if Yahoo unusable."""
    try:
        import yfinance as yf
    except ImportError:
        return None

    today = trading_date or ist_now().date()
    try:
        hist = yf.Ticker(yfinance_ticker).history(period="3mo", interval="1d", prepost=True, actions=False)
    except Exception:
        return None
    if hist is None or hist.empty:
        return None

    rows: list[dict[str, Any]] = []
    for index, row in hist.dropna(subset=["Close"]).iterrows():
        vol_raw = row.get("Volume")
        volume = 0 if vol_raw is None or (isinstance(vol_raw, float) and vol_raw != vol_raw) else int(vol_raw)
        rows.append(
            {
                "date": str(index.date()),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": volume,
            }
        )
    if not rows:
        return None

    live_price, live_day = latest_quote(yfinance_ticker, trading_date=today)
    latest_price = float(rows[-1]["close"])
    price_as_of = rows[-1]["date"]
    session_state = "settled"

    if live_price is not None:
        latest_price = float(live_price)
        live_day_s = live_day or today.isoformat()
        price_as_of = live_day_s
        if live_day_s == today.isoformat():
            session_state = "live"
            last = rows[-1]
            if last["date"] == today.isoformat():
                rows[-1] = {
                    **last,
                    "close": latest_price,
                    "high": max(last["high"], latest_price),
                    "low": min(last["low"], latest_price),
                }
            else:
                rows.append(
                    {
                        "date": today.isoformat(),
                        "open": latest_price,
                        "high": latest_price,
                        "low": latest_price,
                        "close": latest_price,
                        "volume": 0,
                    }
                )

    last_seven = rows[-HOLDING_PRICE_BARS:]
    bars = [
        DayBar(
            r["date"],
            r["open"],
            r["high"],
            r["low"],
            r["close"],
            r["volume"],
            "live" if (i == len(last_seven) - 1 and session_state == "live") else "settled",
        )
        for i, r in enumerate(last_seven)
    ]

    year_rows = rows[-252:] if len(rows) >= 252 else rows
    low_52 = min(r["low"] for r in year_rows)
    high_52 = max(r["high"] for r in year_rows)
    pct_below_high = round((high_52 - latest_price) / high_52 * 100.0, 2) if high_52 else 0.0
    pct_above_low = round((latest_price - low_52) / low_52 * 100.0, 2) if low_52 else 0.0

    closes = [b.close for b in bars]
    week_base = closes[0] if closes else latest_price
    week_change_pct = round((latest_price - week_base) / week_base * 100.0, 2) if week_base else None

    return {
        "ticker": yfinance_ticker,
        "latest_price": round(latest_price, 4),
        "price_as_of": price_as_of,
        "session_state": session_state,
        "bars": [asdict(b) for b in bars],
        "fifty_two_week": {"low": round(low_52, 4), "high": round(high_52, 4)},
        "pct_from_52w_high": pct_below_high,
        "pct_from_52w_low": pct_above_low,
        "pattern_hints": {
            "week_change_pct": week_change_pct,
            "consecutive_down_days": _consecutive_down_days(closes),
        },
    }