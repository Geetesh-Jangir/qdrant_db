"""NSE provisional FII/FPI and DII buy, sell, net (₹ crore)."""

from __future__ import annotations

import os
import random
import time

import httpx

from ai_insight.data.base import FiiDiiSnapshot, FlowLeg

_NSE_HOME = "https://www.nseindia.com"
_API = "https://www.nseindia.com/api/fiidiiTradeReact"
_REPORT = f"{_NSE_HOME}/reports/fii-dii"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


_failures = 0
_open_until = 0.0


def _nse_json(url: str, timeout: float = 20.0) -> object:
    """Two retries, then a 5-minute circuit. A 403 can fall back to the impit browser session."""
    global _failures, _open_until
    if time.time() < _open_until:
        raise RuntimeError("nse circuit open")
    last: Exception | None = None
    started = time.perf_counter()
    for attempt in range(3):
        try:
            payload, status = _httpx_json(url, timeout)
            _failures = 0
            _log_external(url, status, started, attempt, "")
            return payload
        except httpx.HTTPStatusError as exc:
            last = exc
            status = exc.response.status_code if exc.response is not None else 0
            if status == 403 and os.environ.get("NSE_USE_IMPIT", "auto").lower() != "false":
                payload = _impit_json(url)
                _failures = 0
                _log_external(url, 200, started, attempt, "")
                return payload
            if status not in {403, 429} and status < 500:
                _log_external(url, status, started, attempt, "")
                raise
        except Exception as exc:
            last = exc
        time.sleep((2 if attempt == 0 else 5) + random.random())
    _failures += 1
    if _failures >= 3:
        _open_until = time.time() + 300
        _failures = 0
    _log_external(url, "error", started, 2, str(last)[:120] if last else "")
    raise RuntimeError(f"NSE fetch failed: {last}")


def _httpx_json(url: str, timeout: float) -> tuple[object, int]:
    headers = {
        "User-Agent": _UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json,text/plain,*/*",
    }
    limits = httpx.Timeout(timeout, connect=5.0)
    with httpx.Client(follow_redirects=True, timeout=limits) as client:
        client.get(_NSE_HOME, headers={**headers, "Accept": "text/html"})
        client.get(_REPORT, headers={**headers, "Accept": "text/html", "Referer": _NSE_HOME})
        resp = client.get(url, headers={**headers, "Referer": _REPORT})
        resp.raise_for_status()
        return resp.json(), resp.status_code


def _impit_json(url: str) -> object:
    from lib.fetch import make_session

    session = make_session()
    session.get(_NSE_HOME)
    response = session.get(url)
    status = getattr(response, "status_code", 0)
    if status and status >= 400:
        raise RuntimeError(f"impit NSE status {status}")
    return response.json()


def _log_external(url: str, status, started: float, retries: int, detail: str) -> None:
    try:
        from ai_insight.common.logging import log_external

        log_external(
            service="nse",
            url=url,
            status=status,
            latency_ms=round((time.perf_counter() - started) * 1000, 1),
            retries=retries,
            data_date=detail,
            trading_date="",
        )
    except Exception:
        return


def reset_circuit_for_tests() -> None:
    global _failures, _open_until
    _failures = 0
    _open_until = 0.0


def _num(raw: object) -> float | None:
    if raw is None:
        return None
    try:
        return float(str(raw).replace(",", "").strip())
    except ValueError:
        return None


def _leg(row: dict) -> FlowLeg | None:
    buy = _num(row.get("buyValue"))
    sell = _num(row.get("sellValue"))
    net = _num(row.get("netValue"))
    if buy is None or sell is None or net is None:
        return None
    category = str(row.get("category") or "").strip()
    return FlowLeg(category, buy, sell, net)


def _bucket(category: str) -> str:
    c = category.casefold().replace(" ", "")
    if "dii" in c and "fii" not in c:
        return "dii"
    if "fii" in c or "fpi" in c:
        return "fii"
    return ""


def fetch_fii_dii_snapshot() -> FiiDiiSnapshot:
    source = "nseindia.com:fiidiiTradeReact"
    try:
        payload = _nse_json(_API)
    except Exception as exc:
        return FiiDiiSnapshot("", None, None, source, "unavailable", str(exc)[:240])

    rows = payload if isinstance(payload, list) else []
    if not rows:
        return FiiDiiSnapshot("", None, None, source, "unavailable", "empty response")

    trade_date = ""
    fii: FlowLeg | None = None
    dii: FlowLeg | None = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not trade_date:
            trade_date = str(row.get("date") or row.get("tradeDate") or "").strip()
        leg = _leg(row)
        if leg is None:
            continue
        key = _bucket(leg.category)
        if key == "fii":
            fii = leg
        elif key == "dii":
            dii = leg

    if fii is None and dii is None:
        return FiiDiiSnapshot(trade_date, None, None, source, "unavailable", "no parseable legs")
    if fii is None or dii is None:
        missing = "FII/FPI" if fii is None else "DII"
        return FiiDiiSnapshot(
            trade_date,
            fii,
            dii,
            source,
            "partial",
            f"missing {missing} row",
        )
    return FiiDiiSnapshot(trade_date, fii, dii, source, "ok")