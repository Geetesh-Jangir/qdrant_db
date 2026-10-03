"""Tool registry for the ask engine."""

from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING

from historical_data.metals_service import get_latest_metals_spot
from historical_data.nav_service import get_fund_nav_history
from historical_data.stocks_service import get_stock_profile
from news_rag.fund_search import extract_top_holdings, extract_top_sectors, lookup_extracted_fund
from news_rag.query_plan import DataNeed, ScopeRefinement
from news_rag.scoped_retrieve import retrieve_scoped_news
from news_rag.sector_fund_ranking import get_sector_fund_ranking_index, rank_funds_by_sector_exposure

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger


def _ok(data: Any, elapsed_ms: float) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": "", "elapsed_ms": elapsed_ms}


def _err(message: str, elapsed_ms: float) -> dict[str, Any]:
    return {"ok": False, "data": None, "error": message, "elapsed_ms": elapsed_ms}


def run_fund_nav(detail: dict[str, Any], need: DataNeed) -> dict[str, Any]:
    started = time.perf_counter()
    isin = str(detail.get("isin") or "")
    if need.scope and need.scope not in ("latest_only", "with_returns") and isin:
        hist = get_fund_nav_history(isin)
        elapsed = (time.perf_counter() - started) * 1000
        return _ok({"detail": detail, "history": hist}, elapsed)
    nav = detail.get("nav")
    nav_date = detail.get("nav_date") or detail.get("as_on") or ""
    rets = detail.get("returns") if isinstance(detail.get("returns"), dict) else {}
    elapsed = (time.perf_counter() - started) * 1000
    return _ok(
        {
            "fund_name": detail.get("fund_short_name") or detail.get("fund_name"),
            "isin": isin,
            "nav": nav,
            "nav_date": nav_date,
            "day_change_pct": detail.get("nav_day_change_pct"),
            "returns": rets,
            "benchmark": detail.get("benchmark"),
        },
        elapsed,
    )


def run_fund_holdings(detail: dict[str, Any], need: DataNeed) -> dict[str, Any]:
    started = time.perf_counter()
    rows = extract_top_holdings(detail, limit=need.top_n)
    elapsed = (time.perf_counter() - started) * 1000
    return _ok({"rows": rows, "fund_name": detail.get("fund_short_name")}, elapsed)


def run_fund_sectors(detail: dict[str, Any], need: DataNeed) -> dict[str, Any]:
    started = time.perf_counter()
    rows = extract_top_sectors(detail, limit=need.top_n)
    elapsed = (time.perf_counter() - started) * 1000
    return _ok({"rows": rows, "fund_name": detail.get("fund_short_name")}, elapsed)


def run_sector_funds(need: DataNeed) -> dict[str, Any]:
    started = time.perf_counter()
    idx = get_sector_fund_ranking_index()
    text = (need.sector_name or need.semantic_query or "").strip()
    keys = idx.resolve_from_question(text) if text else []
    if not keys:
        lower = text.lower()
        if any(w in lower for w in ("gold", "silver", "bullion", "precious")):
            keys = idx.resolve_sector_keys(["Non - Ferrous Metals", "Ferrous Metals"])
        elif any(w in lower for w in ("oil", "crude", "energy", "barrel", "petroleum", "power")):
            keys = idx.resolve_sector_keys(["Petroleum Products", "Power"])
        else:
            keys = []
    ranked = rank_funds_by_sector_exposure(keys, limit=need.top_n or 10, combine="max")
    from news_rag.fund_search import get_fund_index

    index = get_fund_index()
    rankings = []
    for row in ranked.get("rankings") or []:
        isin = row.get("isin")
        detail = index.get_fund_detail(str(isin)) if isin else None
        name = (
            (detail or {}).get("fund_short_name")
            or (detail or {}).get("fund_name")
            or isin
        )
        rankings.append({**row, "fund_name": name})
    elapsed = (time.perf_counter() - started) * 1000
    return _ok(
        {
            "sector_keys": ranked.get("sector_keys"),
            "rankings": rankings,
            "query": text,
        },
        elapsed,
    )


def run_metals_spot() -> dict[str, Any]:
    started = time.perf_counter()
    spot = get_latest_metals_spot()
    elapsed = (time.perf_counter() - started) * 1000
    return _ok(spot, elapsed)


def run_stock_snapshot(need: DataNeed) -> dict[str, Any]:
    started = time.perf_counter()
    name = need.stock_name or need.semantic_query
    profile = get_stock_profile(name)
    elapsed = (time.perf_counter() - started) * 1000
    if not profile:
        return _err(f"No market data for {name}", elapsed)
    return _ok(profile, elapsed)


def run_news_search(
    need: DataNeed,
    *,
    scope: ScopeRefinement | None,
    question: str,
    query_log: QueryLogger | None = None,
    **filter_kwargs: Any,
) -> dict[str, Any]:
    started = time.perf_counter()
    if (need.scope or "").strip() == "macro_bullion":
        from news_rag.bullion_retrieve import retrieve_bullion_macro_news

        articles = retrieve_bullion_macro_news(
            need.semantic_query or question,
            question=question,
            window_days=need.window_days,
            query_log=query_log,
        )
    else:
        articles = retrieve_scoped_news(
            need.semantic_query or question,
            scope=scope,
            question=question,
            window_days=need.window_days,
            query_log=query_log,
            **filter_kwargs,
        )
    elapsed = (time.perf_counter() - started) * 1000
    return _ok({"articles": articles}, elapsed)


def resolve_fund_for_need(
    fund_raw: str,
    *,
    query_log: QueryLogger | None = None,
) -> tuple[dict[str, Any] | None, bool, list[str], str]:
    """Returns detail, ambiguous, close_matches, match_method."""
    detail, amb, close = lookup_extracted_fund(name=fund_raw)
    if fund_raw.upper().startswith("INF"):
        detail, amb, close = lookup_extracted_fund(isin=fund_raw.upper())
    if query_log is not None:
        query_log.log_fund_lookup(
            extracted_isin="",
            extracted_name=fund_raw,
            resolved=detail is not None,
            ambiguous=amb,
            close_matches=close,
            fund_isin=str(detail.get("isin") or "") if detail else "",
            fund_name=str(detail.get("fund_short_name") or "") if detail else "",
        )
    method = "catalog"
    return detail, amb, close, method
