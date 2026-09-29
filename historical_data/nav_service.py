"""Historical NAV data fetcher, cache manager, and performance analyzer."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parents[1]
_CACHE_DIR = _ROOT / "data" / "nav_cache"
_CACHE_TTL_HOURS = 12.0
_RUPEESTOP_NAV_API = "https://backend.rupeestop.com/api/nav/{isin}/HISTORY"


def _ensure_cache_dir() -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR


def _cache_path(isin: str) -> Path:
    clean = "".join(c for c in isin if c.isalnum() or c in ("-", "_")).upper()
    return _ensure_cache_dir() / f"{clean}.json"


def _read_cache(isin: str) -> list[dict[str, Any]] | None:
    path = _cache_path(isin)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at = float(data.get("cached_at") or 0.0)
        age_hours = (time.time() - cached_at) / 3600.0
        if age_hours > _CACHE_TTL_HOURS:
            return None
        records = data.get("records")
        if isinstance(records, list) and records:
            return records
    except Exception as exc:
        logger.warning("Failed to read NAV cache for %s: %s", isin, exc)
    return None


def _write_cache(isin: str, records: list[dict[str, Any]]) -> None:
    try:
        path = _cache_path(isin)
        payload = {
            "isin": isin.upper(),
            "cached_at": time.time(),
            "cached_at_iso": datetime.now(timezone.utc).isoformat(),
            "count": len(records),
            "records": records,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to write NAV cache for %s: %s", isin, exc)


def fetch_raw_nav_history(isin: str, *, use_cache: bool = True) -> list[dict[str, Any]]:
    """Fetches raw NAV records from RupeeStop API or local disk cache."""
    clean_isin = isin.strip().upper()
    if use_cache:
        cached = _read_cache(clean_isin)
        if cached is not None:
            return cached

    url = _RUPEESTOP_NAV_API.format(isin=clean_isin)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }
    
    with httpx.Client(timeout=15.0) as client:
        resp = client.get(url, headers=headers)
        if resp.status_code != 200:
            # If API fails but stale cache exists, fall back gracefully
            stale_path = _cache_path(clean_isin)
            if stale_path.is_file():
                try:
                    data = json.loads(stale_path.read_text(encoding="utf-8"))
                    return data.get("records") or []
                except Exception:
                    pass
            raise RuntimeError(f"RupeeStop NAV API returned status {resp.status_code} for ISIN {clean_isin}")
        
        payload = resp.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        records = []
        if isinstance(data, dict):
            records = data.get("records") or []
        elif isinstance(payload, list):
            records = payload

        # Clean and parse records
        cleaned_records: list[dict[str, Any]] = []
        for r in records:
            if not isinstance(r, dict):
                continue
            date_str = str(r.get("nav_date") or r.get("date") or "").strip()
            nav_val = r.get("nav_value") if r.get("nav_value") is not None else r.get("nav")
            if not date_str or nav_val is None:
                continue
            try:
                val = float(nav_val)
                cleaned_records.append({
                    "nav_date": date_str,
                    "nav_value": val,
                })
            except (ValueError, TypeError):
                continue

        # Sort ascending by date (oldest to newest)
        cleaned_records.sort(key=lambda item: item["nav_date"])
        if cleaned_records:
            _write_cache(clean_isin, cleaned_records)
        return cleaned_records


def _calculate_window_stats(
    records_asc: list[dict[str, Any]],
    days: int | None,
) -> dict[str, Any] | None:
    if not records_asc:
        return None
    latest = records_asc[-1]
    latest_date_str = latest["nav_date"]
    try:
        latest_dt = datetime.strptime(latest_date_str, "%Y-%m-%d")
    except ValueError:
        return None

    if days is None:
        subset = records_asc
    else:
        cutoff_dt = latest_dt - timedelta(days=days)
        cutoff_str = cutoff_dt.strftime("%Y-%m-%d")
        subset = [r for r in records_asc if r["nav_date"] >= cutoff_str]
        # Ensure we have at least 2 points if total records >= 2
        if len(subset) < 2 and len(records_asc) >= 2:
            subset = records_asc[-min(len(records_asc), max(2, days // 2)):]

    if not subset:
        return None

    start_point = subset[0]
    end_point = subset[-1]

    start_nav = float(start_point["nav_value"])
    end_nav = float(end_point["nav_value"])
    change = end_nav - start_nav
    change_pct = ((change / start_nav) * 100.0) if start_nav > 0 else 0.0

    nav_values = [r["nav_value"] for r in subset]
    min_nav = min(nav_values)
    max_nav = max(nav_values)

    return {
        "start_date": start_point["nav_date"],
        "start_nav": round(start_nav, 4),
        "end_date": end_point["nav_date"],
        "end_nav": round(end_nav, 4),
        "change": round(change, 4),
        "change_pct": round(change_pct, 2),
        "is_positive": change >= 0,
        "min_nav": round(min_nav, 4),
        "max_nav": round(max_nav, 4),
        "point_count": len(subset),
        "points": [
            {
                "date": r["nav_date"],
                "nav": round(float(r["nav_value"]), 4),
            }
            for r in subset
        ],
    }


def get_fund_nav_history(isin: str, *, use_cache: bool = True) -> dict[str, Any]:
    """
    Returns full structured NAV analytics for an ISIN with period slices:
    1W (7D), 1M (30D), 3M (90D), 6M (180D), 1Y (365D), ALL.
    """
    clean_isin = isin.strip().upper()
    records_asc = fetch_raw_nav_history(clean_isin, use_cache=use_cache)
    if not records_asc:
        return {
            "isin": clean_isin,
            "success": False,
            "error": f"No NAV records found for ISIN {clean_isin}",
            "latest_nav": None,
            "latest_date": None,
            "stats": {},
        }

    latest = records_asc[-1]
    stats = {
        "1W": _calculate_window_stats(records_asc, days=7),
        "1M": _calculate_window_stats(records_asc, days=30),
        "3M": _calculate_window_stats(records_asc, days=90),
        "6M": _calculate_window_stats(records_asc, days=180),
        "1Y": _calculate_window_stats(records_asc, days=365),
        "ALL": _calculate_window_stats(records_asc, days=None),
    }

    return {
        "isin": clean_isin,
        "success": True,
        "total_records": len(records_asc),
        "latest_nav": round(float(latest["nav_value"]), 4),
        "latest_date": latest["nav_date"],
        "stats": stats,
    }
