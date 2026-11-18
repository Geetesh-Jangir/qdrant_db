"""Fetch portfolio concentration from RupeeStop backend."""

from __future__ import annotations

import re
import threading
import time
from typing import Any

import httpx

_CRN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,63}$")

_lock = threading.Lock()
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def valid_crn(crn: str) -> bool:
    return bool(_CRN_RE.match((crn or "").strip()))


def fetch_portfolio(crn: str) -> dict[str, Any]:
    crn = str(crn or "").strip()
    if not valid_crn(crn):
        return {}
    try:
        from news_rag.config import get_settings

        settings = get_settings()
        ttl = float(getattr(settings, "portfolio_ttl_sec", 180) or 180)
        base = str(getattr(settings, "rupeestop_backend_base", "") or "https://backend.rupeestop.com").rstrip("/")
        timeout = float(getattr(settings, "portfolio_http_timeout_sec", 15) or 15)
    except Exception:
        ttl = 180.0
        base = "https://backend.rupeestop.com"
        timeout = 15.0

    now = time.time()
    with _lock:
        cached = _cache.get(crn)
        if cached and now - cached[0] < ttl:
            return cached[1]

    url = f"{base}/api/v1/app/portfolio/top-holdings/{crn}"
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return {}

    data = payload.get("data") if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        data = {}
    with _lock:
        _cache[crn] = (now, data)
    return data