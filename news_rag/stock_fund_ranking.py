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


_INITIAL_SKIP = {"of", "and", "the"}


def _initials(name: str) -> str:
    letters: list[str] = []
    for word in _norm(name).split():
        if word in _INITIAL_SKIP or not word:
            continue
        letters.append(word[0])
    return "".join(letters)


def holdings_archive_available() -> bool:
    return bool(_aggregated_map())


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
    if best is not None:
        return best
    token = re.sub(r"[^a-z0-9]", "", needle)
    if " " in needle or not 3 <= len(token) <= 5:
        return None
    initial_best: tuple[str, dict[str, Any]] | None = None
    best_count = -1
    for name, meta in _aggregated_map().items():
        if not isinstance(meta, dict):
            continue
        if _initials(str(name)) != token:
            continue
        try:
            count = int(meta.get("fund_count") or 0)
        except (TypeError, ValueError):
            count = 0
        if count > best_count:
            initial_best = (str(name), meta)
            best_count = count
    return initial_best


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


def holder_candidates_for_stock(stock_name: str, *, limit: int = 40) -> list[dict[str, Any]]:
    """Funds ranked in the stock's industry. A large-cap slice is only the fallback."""
    matched = _match_aggregated(stock_name)
    industry = str(matched[1].get("industry") or "") if matched else ""
    if industry:
        from news_rag.sector_fund_ranking import get_sector_fund_ranking_index, rank_funds_by_sector_exposure

        idx = get_sector_fund_ranking_index()
        keys = idx.resolve_sector_keys([industry]) or idx.resolve_from_question(industry) or []
        if keys:
            ranked = rank_funds_by_sector_exposure(keys, limit=max(1, limit), combine="max")
            rows = [
                {
                    "isin": row.get("isin"),
                    "fund_name": row.get("fund_name"),
                    "category": row.get("category"),
                    "scheme_type": row.get("scheme_type"),
                    "sector_weight_pct": row.get("sector_weight_pct"),
                }
                for row in (ranked.get("rankings") or [])
                if row.get("isin")
            ]
            if rows:
                return rows[:limit]
    return default_holder_candidates(limit=limit, category="Large Cap")


def default_holder_candidates(*, limit: int = 24, category: str = "Large Cap") -> list[dict[str, Any]]:
    """Capped catalog batch. NAV is filled later, once, in parallel."""
    from news_rag.fund_universe_agent import get_fund_universe_catalog

    catalog = get_fund_universe_catalog()
    funds = catalog.query(category=category or None, limit=max(1, limit), enrich_nav=False)
    return [
        {
            "isin": row.get("isin"),
            "fund_name": row.get("fund_name"),
            "amc": row.get("amc"),
            "category": row.get("category"),
            "scheme_type": row.get("scheme_type"),
        }
        for row in funds
        if row.get("isin")
    ]


def scan_schemes_holding_stock(
    stock_name: str,
    candidates: list[dict[str, Any]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Load a capped batch of fund holdings in parallel and keep schemes that hold the stock."""
    from concurrent.futures import ThreadPoolExecutor

    from news_rag.fund_search import extract_top_holdings, lookup_extracted_fund

    needle = _norm(stock_name)
    batch = [row for row in candidates if str(row.get("isin") or "").strip()]
    if not needle or not batch:
        return []

    def _one(row: dict[str, Any]) -> dict[str, Any] | None:
        isin = str(row.get("isin") or "").strip()
        detail, _ambiguous, _notes = lookup_extracted_fund(isin=isin)
        for holding in extract_top_holdings(detail, limit=500):
            name = _norm(str(holding.get("name") or ""))
            if name and (needle in name or name in needle):
                weight = holding.get("percentage")
                try:
                    weight = round(float(weight), 2) if weight is not None else None
                except (TypeError, ValueError):
                    weight = None
                return {
                    **row,
                    "holding_name": holding.get("name"),
                    "weight_pct": weight,
                }
        return None

    found: list[dict[str, Any]] = []
    step = 8
    for start in range(0, len(batch), step):
        chunk = batch[start : start + step]
        with ThreadPoolExecutor(max_workers=min(8, len(chunk))) as pool:
            for item in pool.map(_one, chunk):
                if item:
                    found.append(item)
        if len(found) >= limit:
            break
    found.sort(key=lambda item: float(item.get("weight_pct") or 0), reverse=True)
    return found[: max(1, limit)]


def funds_holding_stock(
    stock_name: str,
    *,
    limit: int = 10,
    candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Count from the archive, and scheme names from a file or a capped holdings scan."""
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
        batch = candidates if candidates is not None else holder_candidates_for_stock(stock_name, limit=40)
        rows = scan_schemes_holding_stock(matched_name or stock_name, batch, limit=limit)
    if not rows:
        note = (
            "The scan did not find named schemes. "
            "The archive count of funds that hold this name is still available."
        )
    elif len(rows) < 2:
        note = (
            "Fewer than two schemes with this holding were confirmed. "
            "The archive count of funds that hold this name is still available."
        )
    return {
        "stock_name": matched_name,
        "industry": industry,
        "fund_count": fund_count,
        "funds": rows,
        "fund_list_available": bool(rows),
        "note": note,
    }
