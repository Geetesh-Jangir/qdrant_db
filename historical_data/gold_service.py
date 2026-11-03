"""India 24K gold prices (INR per 10g) from the RupeeStop market API.

Daily points cover the last few sessions. Longer windows use month-end prices
and are marked approximate. Silver has no price feed yet and is news-only.
"""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)

_TTL_SECONDS = 20 * 60
_WINDOW_DAYS = {
    "1D": 1,
    "1W": 7,
    "1M": 30,
    "3M": 91,
    "6M": 182,
    "1Y": 365,
    "3Y": 365 * 3,
    "5Y": 365 * 5,
}
_SHORT_WINDOWS = frozenset({"1D", "1W", "1M"})
_RANK = {"month_end": 0, "day": 1, "live": 2}

_CACHE: dict[str, Any] = {"at": 0.0, "payload": None}


def get_silver_snapshot() -> dict[str, Any]:
    """No silver price API yet. Callers must answer from news only."""
    from news_rag.config import get_settings

    url = str(get_settings().silver_price_api_url or "").strip()
    if not url:
        return {
            "available": False,
            "metal": "silver",
            "route": "news_only",
            "message": "Silver price data is not available. Answer from news only and do not quote a silver price or return.",
        }
    return {
        "available": False,
        "metal": "silver",
        "route": "news_only",
        "message": "Silver price feed is configured but not wired yet. Answer from news only.",
        "source": url,
    }


def get_gold_snapshot(
    windows: list[str] | None = None,
    history_months: int | None = None,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """24K gold in INR per 10 grams, with window returns and optional month-end history."""
    stale = False
    if payload is None:
        payload, stale = _load_payload()
    if not payload:
        return {
            "available": False,
            "metal": "gold",
            "unit": "INR per 10g (24K)",
            "stale": True,
            "error": "gold_price_unavailable",
        }
    return snapshot_from_payload(payload, windows=windows, history_months=history_months, stale=stale)


def snapshot_from_payload(
    payload: dict[str, Any],
    *,
    windows: list[str] | None = None,
    history_months: int | None = None,
    stale: bool = False,
) -> dict[str, Any]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    series = _merged_series(data)
    if not series:
        return {
            "available": False,
            "metal": "gold",
            "unit": "INR per 10g (24K)",
            "stale": True,
            "error": "gold_price_empty",
        }

    codes = _normalize_windows(windows)
    end = series[-1]
    want_monthly = history_months is not None or any(code not in _SHORT_WINDOWS for code in codes)
    months = int(history_months or 12)
    months = max(1, min(240, months))

    daily = [
        {"date": row["date"].isoformat(), "price_24k_10g": row["price"], "basis": row["basis"]}
        for row in series
        if row["basis"] in ("day", "live")
    ][-12:]

    out: dict[str, Any] = {
        "available": True,
        "metal": "gold",
        "unit": "INR per 10g (24K)",
        "purity": "24K",
        "latest": {
            "price_24k_10g": end["price"],
            "as_of": end["date"].isoformat(),
            "source_basis": end["basis"],
        },
        "returns": {code: _window_return(series, end, code) for code in codes},
        "stale": stale,
        "source_note": (
            "24K gold in INR per 10 grams. Windows inside the last month use daily prices. "
            "Longer windows use the nearest month-end price and are approximate."
        ),
    }
    if any(code in _SHORT_WINDOWS for code in codes) or not codes:
        out["daily"] = daily
    if want_monthly:
        month_rows = [row for row in series if row["basis"] == "month_end"]
        out["monthly"] = [
            {
                "date": row["date"].isoformat(),
                "price_24k_10g": row["price"],
                "basis": "month_end",
            }
            for row in month_rows[-months:]
        ]
    return out


def _load_payload() -> tuple[dict[str, Any] | None, bool]:
    now = time.time()
    cached = _CACHE.get("payload")
    if isinstance(cached, dict) and (now - float(_CACHE.get("at") or 0)) < _TTL_SECONDS:
        return cached, False
    fresh = _fetch()
    if fresh is not None:
        _CACHE["payload"] = fresh
        _CACHE["at"] = now
        return fresh, False
    if isinstance(cached, dict):
        return cached, True
    return None, True


def _fetch() -> dict[str, Any] | None:
    from news_rag.config import get_settings

    settings = get_settings()
    url = str(settings.gold_price_api_url or "").strip()
    if not url:
        return None
    headers = {"Accept": "application/json"}
    token = str(settings.rupeestop_admin_token or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    last_error = ""
    for _ in range(2):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            body = response.json()
            if isinstance(body, dict) and isinstance(body.get("data"), dict):
                return body
            last_error = "unexpected_shape"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)[:160]
    logger.warning("gold price fetch failed: %s", last_error)
    return None


def _merged_series(data: dict[str, Any]) -> list[dict[str, Any]]:
    points: dict[date, dict[str, Any]] = {}

    def add(raw_date: Any, price: Any, basis: str) -> None:
        day = _parse_date(raw_date)
        try:
            value = round(float(price), 2)
        except (TypeError, ValueError):
            return
        if day is None or value <= 0:
            return
        current = points.get(day)
        if current is None or _RANK[basis] >= _RANK[current["basis"]]:
            points[day] = {"date": day, "price": value, "basis": basis}

    for row in data.get("monthlyHistory") or []:
        if isinstance(row, dict):
            add(row.get("date"), row.get("pricePer10g"), "month_end")
    for row in data.get("recentDays") or []:
        if isinstance(row, dict):
            add(row.get("date"), row.get("pricePer10g"), "day")
    latest = data.get("latestEndOfDay")
    if isinstance(latest, dict):
        add(latest.get("date"), latest.get("pricePer10g"), "day")
    today = data.get("todayPrice")
    if isinstance(today, dict):
        add(today.get("date") or today.get("dateText"), today.get("price24kPer10g"), "live")
    return [points[key] for key in sorted(points)]


def _window_return(series: list[dict[str, Any]], end: dict[str, Any], code: str) -> dict[str, Any] | None:
    if code == "1D":
        prior = [row for row in series if row["date"] < end["date"] and row["basis"] in ("day", "live")]
        start = prior[-1] if prior else None
        approx = False
    elif code == "YTD":
        target = date(end["date"].year, 1, 1)
        start, approx = _point_on_or_before(series, target, prefer_day=False)
    else:
        days = _WINDOW_DAYS.get(code)
        if days is None:
            return None
        target = end["date"] - timedelta(days=days)
        prefer_day = code in _SHORT_WINDOWS
        start, approx = _point_on_or_before(series, target, prefer_day=prefer_day)
    if start is None or start["price"] <= 0:
        return None
    pct = round((end["price"] - start["price"]) / start["price"] * 100.0, 2)
    return {
        "pct": pct,
        "from_date": start["date"].isoformat(),
        "from_price": start["price"],
        "to_date": end["date"].isoformat(),
        "to_price": end["price"],
        "basis": start["basis"],
        "approx": approx or start["basis"] == "month_end",
        "horizon": code,
    }


def _point_on_or_before(
    series: list[dict[str, Any]],
    target: date,
    *,
    prefer_day: bool,
) -> tuple[dict[str, Any] | None, bool]:
    eligible = [row for row in series if row["date"] <= target]
    if prefer_day:
        daily = [row for row in eligible if row["basis"] in ("day", "live")]
        if daily and (target - daily[-1]["date"]).days <= 4:
            return daily[-1], False
    monthly = [row for row in eligible if row["basis"] == "month_end"]
    if monthly:
        chosen = monthly[-1]
        return chosen, True
    if eligible:
        return eligible[-1], eligible[-1]["basis"] == "month_end"
    return None, True


def _normalize_windows(windows: list[str] | None) -> list[str]:
    if not windows:
        return ["1D", "1W", "1M"]
    out: list[str] = []
    for raw in windows:
        code = str(raw or "").strip().upper()
        if code in _WINDOW_DAYS or code == "YTD":
            if code not in out:
                out.append(code)
    return out or ["1D", "1W", "1M"]


def _parse_date(raw: Any) -> date | None:
    text = str(raw or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
