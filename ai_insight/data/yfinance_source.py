"""Daily close and percent change for exchange-quoted macro series. Gold is not included."""

from __future__ import annotations

from ai_insight.data.base import NumericRecord, unavailable

# Entity names match news_pipeline.config.MACRO_ENTITIES.
YF_SERIES: tuple[tuple[str, str, str], ...] = (
    ("Macro - Nifty 50", "^NSEI", "index"),
    ("Macro - Bank Nifty", "^NSEBANK", "index"),
    ("Macro - Sensex", "^BSESN", "index"),
    ("Macro - India VIX", "^INDIAVIX", "index"),
    ("Macro - Rupee / USD", "INR=X", "inr_per_usd"),
    ("Macro - Crude Oil", "BZ=F", "usd"),
)


def fetch_history(entity_name: str, period: str = "6mo") -> list[tuple[str, float]]:
    """Daily closes up to the latest bar Yahoo has. Empty when the series is unknown or down."""
    match = next((row for row in YF_SERIES if row[0] == entity_name), None)
    if match is None:
        return []
    try:
        import yfinance as yf
    except ImportError:
        return []
    try:
        hist = yf.Ticker(match[1]).history(period=period)
        if hist is None or hist.empty or "Close" not in hist:
            return []
        close = hist["Close"].dropna()
        return [(str(index.date()), float(value)) for index, value in close.items()]
    except Exception:
        return []


def fetch_series(entity_name: str) -> NumericRecord:
    """One YF_SERIES row. Unknown names come back unavailable and do not hit the network."""
    match = next((row for row in YF_SERIES if row[0] == entity_name), None)
    if match is None:
        return unavailable(entity_name, "yfinance", "unknown series")
    try:
        import yfinance as yf
    except ImportError:
        return unavailable(entity_name, "yfinance", "yfinance is not installed")
    name, ticker, unit = match
    return _one(yf, name, ticker, unit)


def fetch_yfinance() -> list[NumericRecord]:
    try:
        import yfinance as yf
    except ImportError:
        return [unavailable(name, "yfinance", "yfinance is not installed") for name, _, _ in YF_SERIES]

    rows: list[NumericRecord] = []
    for name, ticker, unit in YF_SERIES:
        rows.append(_one(yf, name, ticker, unit))
    return rows


def _one(yf, name: str, ticker: str, unit: str) -> NumericRecord:
    from datetime import date as date_cls

    from ai_insight.common.yahoo_live import latest_quote

    try:
        live, live_day = latest_quote(ticker, trading_date=date_cls.today())
        hist = yf.Ticker(ticker).history(period="5d", prepost=True, interval="1d")
        if hist is None or hist.empty or "Close" not in hist:
            if live is None:
                return unavailable(name, f"yfinance:{ticker}", "empty history")
            value = live
            traded = live_day or ""
            prev = None
        else:
            close = hist["Close"].dropna()
            if close.empty and live is None:
                return unavailable(name, f"yfinance:{ticker}", "no close")
            value = float(live if live is not None else close.iloc[-1])
            traded = live_day or str(close.index[-1].date())
            prev = float(close.iloc[-2]) if len(close) >= 2 else None
        change = None
        if prev and prev != 0:
            change = round((value - prev) / prev * 100.0, 2)
        return NumericRecord(name, traded, round(value, 4), change, unit, f"yfinance:{ticker}", "ok")
    except Exception as exc:
        return unavailable(name, f"yfinance:{ticker}", str(exc)[:200])
