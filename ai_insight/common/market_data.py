"""Nifty, FII/DII, and USDINR. Each call returns a status and never raises."""

from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Literal

from ai_insight.common.config import CommonConfig, load_config

Status = Literal["ok", "stale", "unavailable", "error"]
_NIFTY = "Macro - Nifty 50"
_USDINR = "Macro - Rupee / USD"
_MONTHS = {
    name: index
    for index, name in enumerate(
        ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"),
        start=1,
    )
}


@dataclass
class MarketResult:
    status: Status
    data: dict[str, Any] | None
    detail: str
    source: str
    elapsed_ms: float


def get_nifty(
    trading_date: str,
    *,
    fetch: Callable[[], Any] | None = None,
    timeout: float | None = None,
    config: CommonConfig | None = None,
    history: list[tuple[str, float]] | None = None,
) -> MarketResult:
    from ai_insight.data.yfinance_source import fetch_history, fetch_series

    if history is not None or fetch is None:
        rows = history if history is not None else fetch_history(_NIFTY)
        if rows:
            return _from_history(trading_date, rows, "yfinance:^NSEI")
        if fetch is None:
            return _quote(
                trading_date,
                source="yfinance:^NSEI",
                fetch=lambda: fetch_series(_NIFTY),
                timeout=timeout,
                config=config,
            )
    return _quote(
        trading_date,
        source="yfinance:^NSEI",
        fetch=fetch or (lambda: fetch_series(_NIFTY)),
        timeout=timeout,
        config=config,
    )


def get_series(
    entity_name: str,
    trading_date: str,
    *,
    history: list[tuple[str, float]] | None = None,
) -> MarketResult:
    """Close and change for one macro series on trading_date, from daily history."""
    from ai_insight.data.yfinance_source import YF_SERIES, fetch_history

    ticker = next((row[1] for row in YF_SERIES if row[0] == entity_name), entity_name)
    rows = history if history is not None else fetch_history(entity_name)
    return _from_history(trading_date, rows, f"yfinance:{ticker}")


def get_usdinr(
    trading_date: str,
    *,
    fetch: Callable[[], Any] | None = None,
    timeout: float | None = None,
    config: CommonConfig | None = None,
) -> MarketResult:
    from ai_insight.data.yfinance_source import fetch_series

    return _quote(
        trading_date,
        source="yfinance:INR=X",
        fetch=fetch or (lambda: fetch_series(_USDINR)),
        timeout=timeout,
        config=config,
    )


def get_fii_dii_today(
    trading_date: str,
    *,
    fetch: Callable[[], Any] | None = None,
    timeout: float | None = None,
    config: CommonConfig | None = None,
) -> MarketResult:
    from ai_insight.data.nse_fii_dii import fetch_fii_dii_snapshot

    cfg = config or load_config()
    limit = cfg.market_timeout_sec if timeout is None else timeout
    started = time.perf_counter()
    loader = fetch or fetch_fii_dii_snapshot
    try:
        snapshot = _run_bounded(loader, limit)
    except TimeoutError as exc:
        return _done("error", None, str(exc), "nseindia.com:fiidiiTradeReact", started)
    except Exception as exc:
        return _done("error", None, f"{type(exc).__name__}: {exc}", "nseindia.com:fiidiiTradeReact", started)
    source = str(getattr(snapshot, "source", "") or "nseindia.com:fiidiiTradeReact")
    raw_status = str(getattr(snapshot, "status", "") or "")
    trade_date = _iso_date(str(getattr(snapshot, "trade_date", "") or ""))
    data = _flow_data(snapshot, trade_date)
    if raw_status != "ok" or data.get("fii") is None or data.get("dii") is None:
        detail = str(getattr(snapshot, "detail", "") or raw_status or "unavailable")
        return _done("unavailable", data, detail, source, started)
    if trade_date != trading_date:
        return _done("stale", data, f"NSE date {trade_date or 'unknown'} != {trading_date}", source, started)
    return _done("ok", data, "", source, started)


def _from_history(trading_date: str, rows: list[tuple[str, float]], source: str) -> MarketResult:
    started = time.perf_counter()
    ordered = [(day, close) for day, close in rows if day and close is not None]
    ordered.sort(key=lambda item: item[0])
    match = next((item for item in ordered if item[0] == trading_date), None)
    if match is None:
        latest = ordered[-1][0] if ordered else "unknown"
        data = {"date": latest, "close": ordered[-1][1], "change_pct": None, "source": source} if ordered else None
        return _done("stale" if ordered else "unavailable", data, f"data date {latest} != {trading_date}", source, started)
    index = ordered.index(match)
    prev = ordered[index - 1][1] if index else None
    change = None
    if prev:
        change = round((match[1] - prev) / prev * 100.0, 2)
    data = {
        "date": trading_date,
        "close": round(match[1], 4),
        "change_pct": change,
        "prev_close": None if prev is None else round(prev, 4),
        "source": source,
    }
    return _done("ok", data, "", source, started)


def _quote(
    trading_date: str,
    *,
    source: str,
    fetch: Callable[[], Any],
    timeout: float | None,
    config: CommonConfig | None,
) -> MarketResult:
    cfg = config or load_config()
    limit = cfg.market_timeout_sec if timeout is None else timeout
    started = time.perf_counter()
    try:
        record = _run_bounded(fetch, limit)
    except TimeoutError as exc:
        return _done("error", None, str(exc), source, started)
    except Exception as exc:
        return _done("error", None, f"{type(exc).__name__}: {exc}", source, started)
    record_source = str(getattr(record, "source", "") or source)
    if str(getattr(record, "status", "")) != "ok" or getattr(record, "value", None) is None:
        return _done("unavailable", None, str(getattr(record, "detail", "") or "unavailable"), record_source, started)
    data = {
        "date": str(getattr(record, "date", "") or ""),
        "close": getattr(record, "value", None),
        "change_pct": getattr(record, "change_pct", None),
        "source": record_source,
    }
    if data["date"] != trading_date:
        return _done("stale", data, f"data date {data['date'] or 'unknown'} != {trading_date}", record_source, started)
    return _done("ok", data, "", record_source, started)


def _flow_data(snapshot: Any, trade_date: str) -> dict[str, Any]:
    def leg(value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if hasattr(value, "as_dict"):
            return value.as_dict()
        return dict(value)

    return {
        "trade_date": trade_date,
        "fii": leg(getattr(snapshot, "fii", None)),
        "dii": leg(getattr(snapshot, "dii", None)),
        "source": str(getattr(snapshot, "source", "") or ""),
    }


def _iso_date(raw: str) -> str:
    """English month names, not the machine locale. NSE writes dates as 13-Nov-2026."""
    text = raw.strip()
    if not text:
        return ""
    named = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3,9})-(\d{4})", text)
    if named:
        month = _MONTHS.get(named.group(2)[:3].lower())
        if month is None:
            return ""
        try:
            return date(int(named.group(3)), month, int(named.group(1))).isoformat()
        except ValueError:
            return ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _done(status: Status, data: dict[str, Any] | None, detail: str, source: str, started: float) -> MarketResult:
    return MarketResult(status, data, detail[:240], source, round((time.perf_counter() - started) * 1000, 1))


def get_index_history(entity_name: str, days: int = 20, *, config: CommonConfig | None = None) -> dict[str, Any]:
    from ai_insight.data.yfinance_source import YF_SERIES, fetch_history

    period = f"{max(days * 3, 60)}d"
    rows = fetch_history(entity_name, period=period)
    if not rows:
        return {"status": "unavailable", "entity": entity_name}
    daily: list[dict[str, Any]] = []
    for index, (day, close) in enumerate(rows):
        prev = rows[index - 1][1] if index else None
        chg = None
        if prev and prev != 0:
            chg = round((close - prev) / prev * 100.0, 2)
        daily.append({"date": day, "close": round(close, 4), "change_pct": chg})
    window = daily[-days:]
    first = window[0]["close"] if window else None
    last = window[-1]["close"] if window else None
    total_chg = None
    if first and last and first != 0:
        total_chg = round((last - first) / first * 100.0, 2)
    highs = [row["close"] for row in window]
    return {
        "status": "ok",
        "entity": entity_name,
        "ticker": next((r[1] for r in YF_SERIES if r[0] == entity_name), ""),
        "daily": window,
        "return_pct": total_chg,
        "high": max(highs) if highs else None,
        "low": min(highs) if highs else None,
    }


def build_aligned_table(
    trading_date: str,
    flows: list[Any],
    *,
    config: CommonConfig | None = None,
) -> list[dict[str, Any]]:
    from ai_insight.data.yfinance_source import YF_SERIES

    cfg = config or load_config()
    by_date = {day.date: day for day in flows if getattr(day, "date", "")}
    names = ("Macro - Nifty 50", "Macro - India VIX", "Macro - Rupee / USD", "Macro - Crude Oil")
    series: dict[str, dict[str, Any]] = {}
    for entity in names:
        hist = get_index_history(entity, days=12, config=cfg)
        if hist.get("status") != "ok":
            continue
        for row in hist.get("daily") or []:
            series.setdefault(row["date"], {})[entity] = row
    dates = sorted(set(by_date) | set(series))
    table: list[dict[str, Any]] = []
    for day in dates[-12:]:
        flow = by_date.get(day)
        prices = series.get(day, {})
        nifty = prices.get("Macro - Nifty 50") or {}
        table.append(
            {
                "date": day,
                "nifty_close": nifty.get("close"),
                "nifty_pct": nifty.get("change_pct"),
                "fii_net": None if flow is None else flow.fii_net,
                "dii_net": None if flow is None else flow.dii_net,
                "vix_pct": (prices.get("Macro - India VIX") or {}).get("change_pct"),
                "usdinr": (prices.get("Macro - Rupee / USD") or {}).get("close"),
                "crude_pct": (prices.get("Macro - Crude Oil") or {}).get("change_pct"),
            }
        )
    if trading_date not in {row["date"] for row in table} and table:
        pass
    return table


def _run_bounded(fn: Callable[[], Any], timeout_sec: float) -> Any:
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(fn)
    try:
        return future.result(timeout=timeout_sec)
    except TimeoutError as exc:
        raise TimeoutError(f"timed out after {timeout_sec:g}s") from exc
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
