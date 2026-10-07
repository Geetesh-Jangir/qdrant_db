"""Funds that hold a named stock, when a holdings file is on disk.

aggregated_holdings_map.json only has industry and fund_count. The fund list
comes from allisin_sectors_with_holdings.json or the portfolio subset.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from news_rag.config import get_settings

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _path(relative: str) -> Path:
    path = Path(relative)
    if path.is_file():
        return path
    return _REPO_ROOT / relative


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


@lru_cache(maxsize=1)
def _aggregated_map() -> dict[str, Any]:
    path = _path(get_settings().aggregated_holdings_map)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _match_aggregated(stock_name: str) -> tuple[str, dict[str, Any]] | None:
    needle = _norm(stock_name)
    if not needle:
        return None
    best: tuple[str, dict[str, Any]] | None = None
    for name, meta in _aggregated_map().items():
        if not isinstance(meta, dict):
            continue
        folded = _norm(str(name))
        if folded == needle or needle in folded or folded in needle:
            if best is None or len(folded) < len(_norm(best[0])):
                best = (str(name), meta)
            if folded == needle:
                return str(name), meta
    return best


def _holdings_file() -> Path | None:
    settings = get_settings()
    for relative in (settings.allisin_sectors_holdings_json, settings.portfolio_allisin_holdings_json):
        path = _path(relative)
        if path.is_file():
            return path
    return None


def _funds_from_holdings_file(stock_name: str, *, limit: int) -> list[dict[str, Any]]:
    path = _holdings_file()
    if path is None:
        return []
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(document, dict):
        return []
    needle = _norm(stock_name)
    found: list[dict[str, Any]] = []
    for isin, row in document.items():
        if not isinstance(row, dict):
            continue
        holdings = row.get("holdings") or {}
        if not isinstance(holdings, dict):
            continue
        for holding_name, meta in holdings.items():
            if needle not in _norm(str(holding_name)) and _norm(str(holding_name)) not in needle:
                continue
            weight = meta.get("percentage") if isinstance(meta, dict) else None
            found.append(
                {
                    "isin": isin,
                    "fund_name": row.get("fund_short_name") or "",
                    "holding_name": holding_name,
                    "weight_pct": weight,
                    "category": row.get("category") or "",
                    "scheme_type": row.get("scheme_type") or "",
                }
            )
            break
    found.sort(key=lambda item: float(item.get("weight_pct") or 0), reverse=True)
    return found[:limit]


def funds_holding_stock(stock_name: str, *, limit: int = 10) -> dict[str, Any]:
    """Count and industry always; fund rows only when a holdings file exists."""
    stock_name = (stock_name or "").strip()
    matched = _match_aggregated(stock_name)
    industry = ""
    fund_count = None
    matched_name = stock_name
    if matched:
        matched_name, meta = matched
        industry = str(meta.get("industry") or "")
        fund_count = meta.get("fund_count")
    rows = _funds_from_holdings_file(stock_name, limit=max(1, limit))
    note = ""
    if not rows:
        note = (
            "The fund list is unavailable. The archive has an industry and a count of funds "
            "that hold this name, not the scheme names."
        )
    return {
        "stock_name": matched_name,
        "industry": industry,
        "fund_count": fund_count,
        "funds": rows,
        "fund_list_available": bool(rows),
        "note": note,
    }
