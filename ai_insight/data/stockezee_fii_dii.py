"""StockeZee historical FII/DII cash net (₹ crore) from the public historical page."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone

import httpx

_PAGE = "https://www.stockezee.com/fii-dii-historical-data"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_SOURCE = "stockezee.com:fii-dii-historical"


@dataclass(frozen=True)
class StockeZeeDay:
    date: str
    fii_net: float
    dii_net: float


def fetch_stockezee_history(*, timeout: float = 30.0) -> list[StockeZeeDay]:
    """Parse embedded Next.js page data (no separate API)."""
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        resp = client.get(_PAGE, headers={"User-Agent": _UA, "Accept": "text/html"})
        resp.raise_for_status()
        text = resp.text
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if not match:
        raise RuntimeError("stockezee: missing __NEXT_DATA__")
    initial = json.loads(match.group(1)).get("props", {}).get("pageProps", {}).get("initialData") or []
    days: list[StockeZeeDay] = []
    for row in initial:
        if not isinstance(row, dict):
            continue
        iso = _iso_date(str(row.get("date") or ""))
        fii, dii = _cash_nets(row.get("fii_cash") or [])
        if not iso or fii is None or dii is None:
            continue
        days.append(StockeZeeDay(iso, fii, dii))
    days.sort(key=lambda item: item.date)
    return days


def history_record(day: StockeZeeDay) -> dict:
    """Net-only row for dates before full NSE buy/sell is available."""
    return {
        "date": day.date,
        "fii": {"buy": None, "sell": None, "net": day.fii_net},
        "dii": {"buy": None, "sell": None, "net": day.dii_net},
        "source": _SOURCE,
        "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "provisional": False,
    }


def _iso_date(raw: str) -> str:
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        return raw[:10]
    return ""


def _cash_nets(rows: list) -> tuple[float | None, float | None]:
    fii = dii = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        cat = str(row.get("category") or "").upper()
        try:
            net = float(row["net_value"])
        except (KeyError, TypeError, ValueError):
            continue
        if "FII" in cat or "FPI" in cat:
            fii = net
        elif cat == "DII":
            dii = net
    return fii, dii


def days_in_range(days: list[StockeZeeDay], *, from_date: date, before_date: date) -> list[StockeZeeDay]:
    start, end = from_date.isoformat(), before_date.isoformat()
    return [day for day in days if start <= day.date < end]