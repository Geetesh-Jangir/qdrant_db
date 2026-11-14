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
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist is None or hist.empty or "Close" not in hist:
            return unavailable(name, f"yfinance:{ticker}", "empty history")
        close = hist["Close"].dropna()
        if close.empty:
            return unavailable(name, f"yfinance:{ticker}", "no close")
        value = float(close.iloc[-1])
        change = None
        if len(close) >= 2 and float(close.iloc[-2]) != 0:
            change = round((value - float(close.iloc[-2])) / float(close.iloc[-2]) * 100.0, 2)
        date = str(close.index[-1].date())
        return NumericRecord(name, date, round(value, 4), change, unit, f"yfinance:{ticker}", "ok")
    except Exception as exc:
        return unavailable(name, f"yfinance:{ticker}", str(exc)[:200])
