"""Underlying stock and sector concentration from the app top-holdings endpoint."""

from __future__ import annotations

import threading
import time
from typing import Any

import httpx

from news_rag.config import get_settings

_lock = threading.Lock()
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def fetch_top_holdings(crn: str) -> dict[str, Any]:
    crn = str(crn or "").strip()
    if not crn:
        return {}
    settings = get_settings()
    ttl = float(getattr(settings, "portfolio_ttl_sec", 180) or 180)
    now = time.time()
    with _lock:
        cached = _cache.get(crn)
        if cached and now - cached[0] < ttl:
            return cached[1]
    base = str(getattr(settings, "rupeestop_backend_base", "") or "https://backend.rupeestop.com").rstrip("/")
    url = f"{base}/api/v1/app/portfolio/top-holdings/{crn}"
    timeout = float(getattr(settings, "portfolio_http_timeout_sec", 15) or 15)
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return {}
    data = payload.get("data") if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        return {}
    with _lock:
        _cache[crn] = (now, data)
    return data


def project_concentration(raw: dict[str, Any], *, top_n: int = 6) -> dict[str, Any]:
    """Top weights across all instrument types, including cash and debt."""
    rows = raw.get("top_holdings") if isinstance(raw.get("top_holdings"), list) else []
    ranked = [row for row in rows if isinstance(row, dict) and row.get("percentage") is not None]
    ranked.sort(key=lambda row: float(row.get("percentage") or 0), reverse=True)
    limit = max(5, min(int(top_n or 6), 8))
    top = []
    for row in ranked[:limit]:
        top.append({
            "name": str(row.get("instrument_name") or "").strip(),
            "weight_pct": row.get("percentage"),
            "fund_count": row.get("fund_count"),
            "industry": str(row.get("industry") or "").strip(),
            "type": str(row.get("type") or "").strip(),
        })
    weight_sum = round(sum(float(row["weight_pct"] or 0) for row in top), 2)
    sectors = raw.get("sector_allocation") if isinstance(raw.get("sector_allocation"), list) else []
    sector_rows = [
        {"sector": str(row.get("sector") or "").strip(), "weight_pct": row.get("percentage")}
        for row in sectors
        if isinstance(row, dict)
    ]
    sector_rows.sort(key=lambda row: float(row.get("weight_pct") or 0), reverse=True)
    return {
        "as_of_date": raw.get("as_of_date"),
        "total_current_value": raw.get("total_current_value"),
        "top_holdings": top,
        "top_holdings_weight_pct": weight_sum,
        "top_holdings_count": len(top),
        "sectors": sector_rows[:5],
    }
