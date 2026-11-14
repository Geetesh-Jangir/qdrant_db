"""NSE provisional FII/FPI and DII buy, sell, net (₹ crore)."""

from __future__ import annotations

import json

import httpx

from ai_insight.data.base import FiiDiiSnapshot, FlowLeg

_NSE_HOME = "https://www.nseindia.com"
_API = "https://www.nseindia.com/api/fiidiiTradeReact"
_REPORT = f"{_NSE_HOME}/reports/fii-dii"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _nse_json(url: str, timeout: float = 20.0) -> object:
    headers = {
        "User-Agent": _UA,
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json,text/plain,*/*",
    }
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        client.get(_NSE_HOME, headers={**headers, "Accept": "text/html"})
        client.get(_REPORT, headers={**headers, "Accept": "text/html", "Referer": _NSE_HOME})
        resp = client.get(url, headers={**headers, "Referer": _REPORT})
        resp.raise_for_status()
        return resp.json()


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