"""Tool registry for the ask engine."""

from __future__ import annotations

import re
import time
from datetime import date
from typing import Any, Literal, TYPE_CHECKING

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
            "high_52w": detail.get("high_52w"),
            "low_52w": detail.get("low_52w"),
            "scheme_type": detail.get("scheme_type"),
            "category": detail.get("category"),
        },
        elapsed,
    )


def run_fund_holdings(detail: dict[str, Any], need: DataNeed) -> dict[str, Any]:
    started = time.perf_counter()
    rows = extract_top_holdings(detail, limit=need.top_n)
    elapsed = (time.perf_counter() - started) * 1000
    return _ok({"rows": rows, "fund_name": detail.get("fund_short_name")}, elapsed)


def run_compare_funds(
    details: list[dict[str, Any]] | None = None,
    *,
    rows: list[dict[str, Any]] | None = None,
    top_n: int = 5,
    compare_on: str = "all",
    return_window: str = "1M",
) -> dict[str, Any]:
    """Compare named funds or screened rows. Fetch only the blocks compare_on asks for."""
    from concurrent.futures import ThreadPoolExecutor

    from news_rag.fund_search import lookup_extracted_fund

    started = time.perf_counter()
    mode = (compare_on or "all").strip().lower()
    if mode not in ("nav", "sectors", "holdings", "all"):
        mode = "all"
    window = normalize_return_window(return_window)
    field = _window_field(window)
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        isin = str(row.get("isin") or "").strip().upper()
        if not isin or isin in seen:
            continue
        seen.add(isin)
        items.append(
            {
                "isin": isin,
                "fund_name": row.get("fund_name") or isin,
                "detail": None,
                "row": row,
            }
        )
    for detail in details or []:
        if not detail:
            continue
        isin = str(detail.get("isin") or "").strip().upper()
        if isin and isin in seen:
            continue
        if isin:
            seen.add(isin)
        items.append(
            {
                "isin": isin,
                "fund_name": detail.get("fund_short_name") or detail.get("fund_name") or isin,
                "detail": detail,
                "row": {},
            }
        )
    items = items[: max(2, top_n)]

    def _pack(item: dict[str, Any]) -> dict[str, Any]:
        row = item["row"]
        out: dict[str, Any] = {
            "fund_name": item["fund_name"],
            "isin": item["isin"],
            "return_window": window,
            "return_pct": row.get(field),
            "latest_nav": row.get("latest_nav"),
            "category": row.get("category"),
            "scheme_type": row.get("scheme_type"),
        }
        detail = item["detail"]
        need_detail = mode in ("holdings", "sectors", "all") and detail is None and item["isin"]
        if need_detail:
            detail, _ambiguous, _notes = lookup_extracted_fund(isin=item["isin"])
        if detail:
            out["category"] = out.get("category") or detail.get("category")
            out["scheme_type"] = out.get("scheme_type") or detail.get("scheme_type")
        if out["return_pct"] is None and item["isin"]:
            hist = get_fund_nav_history(item["isin"])
            stats = (hist.get("stats") or {}) if hist.get("success") else {}
            block = stats.get(window) or {}
            if block.get("change_pct") is not None:
                out["return_pct"] = float(block["change_pct"])
            out["latest_nav"] = hist.get("latest_nav") if hist.get("success") else out["latest_nav"]
            out["nav"] = {
                "latest_nav": out["latest_nav"],
                "return_pct": out["return_pct"],
                "return_window": window,
                "nav_date": hist.get("latest_date") if hist.get("success") else None,
            }
        elif mode in ("nav", "all"):
            out["nav"] = {
                "latest_nav": out["latest_nav"],
                "return_pct": out["return_pct"],
                "return_window": window,
            }
        if mode in ("holdings", "all") and detail:
            holdings = run_fund_holdings(detail, DataNeed(tool="fund_holdings", top_n=top_n))
            out["holdings"] = ((holdings.get("data") or {}).get("rows") if holdings.get("ok") else [])
        if mode in ("sectors", "all") and detail:
            sectors = run_fund_sectors(detail, DataNeed(tool="fund_sectors", top_n=top_n))
            out["sectors"] = ((sectors.get("data") or {}).get("rows") if sectors.get("ok") else [])
        return out

    funds: list[dict[str, Any]] = []
    if items:
        with ThreadPoolExecutor(max_workers=min(8, len(items))) as pool:
            funds = list(pool.map(_pack, items))
    elapsed = (time.perf_counter() - started) * 1000
    return _ok(
        {"funds": funds, "count": len(funds), "compare_on": mode, "return_window": window},
        elapsed,
    )


def run_fund_sectors(detail: dict[str, Any], need: DataNeed) -> dict[str, Any]:
    started = time.perf_counter()
    rows = extract_top_sectors(detail, limit=need.top_n)
    elapsed = (time.perf_counter() - started) * 1000
    return _ok({"rows": rows, "fund_name": detail.get("fund_short_name")}, elapsed)


def run_fund_universe_discovery(
    *,
    category: str | None = None,
    amc: str | None = None,
    keyword: str | None = None,
    limit: int = 5,
    enrich_nav: bool = True,
) -> dict[str, Any]:
    from news_rag.fund_universe_agent import get_fund_universe_catalog
    started = time.perf_counter()
    catalog = get_fund_universe_catalog()
    funds = catalog.query(
        category=category,
        amc=amc,
        keyword=keyword,
        limit=limit,
        enrich_nav=enrich_nav,
    )
    elapsed = (time.perf_counter() - started) * 1000
    return _ok({"funds": funds, "count": len(funds)}, elapsed)


_RETURN_FIELDS = {
    "1W": "return_1w_pct",
    "1M": "return_1m_pct",
    "3M": "return_3m_pct",
    "1Y": "return_1y_pct",
}
_WINDOW_ALIASES = {
    "1WEEK": "1W",
    "WEEK": "1W",
    "7D": "1W",
    "1MONTH": "1M",
    "MONTH": "1M",
    "30D": "1M",
    "3MONTH": "3M",
    "90D": "3M",
    "1YEAR": "1Y",
    "YEAR": "1Y",
    "365D": "1Y",
}
_SCREEN_CANDIDATE_CAP = 40
_PERFORMANCE_SAMPLE = 80
_STALE_NAV_DAYS = 45


def normalize_return_window(value: str | None) -> str:
    raw = re.sub(r"[^A-Z0-9]", "", (value or "").upper())
    if raw in _RETURN_FIELDS:
        return raw
    return _WINDOW_ALIASES.get(raw, "1M")


def infer_return_window(question: str, explicit: str | None = None) -> str:
    if explicit:
        return normalize_return_window(explicit)
    text = (question or "").lower()
    if re.search(r"\b(last|past|this)\s+week\b|\b1\s*week\b|\bone\s+week\b|\b7\s*days?\b", text):
        return "1W"
    if re.search(r"\b3\s*months?\b|\bthree\s+months?\b|\b90\s*days?\b", text):
        return "3M"
    if re.search(r"\b(last|past)\s+year\b|\b1\s*year\b|\bone\s+year\b", text):
        return "1Y"
    return "1M"


def _window_field(window: str) -> str:
    return _RETURN_FIELDS[normalize_return_window(window)]


_PERFORMANCE_QUESTION_RE = re.compile(
    r"\b(best|top|highest|outperform|performed\s+best|performing\s+best|working\s+well|"
    r"last\s+month|1\s*[- ]?month|one\s+month)\b",
    re.I,
)


_FUND_COUNT_RE = re.compile(
    r"\b(\d{1,2})\b(?:\s+\w+){0,4}\s+(?:mutual\s+)?(?:funds?|schemes?)\b",
    re.I,
)
_WORD_FUND_COUNTS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


def explicit_fund_count(question: str) -> int | None:
    """Return a fund count only when the user asked for one."""
    q = question or ""
    m = _FUND_COUNT_RE.search(q)
    if m:
        try:
            return max(1, min(int(m.group(1)), 15))
        except ValueError:
            return None
    for word, n in _WORD_FUND_COUNTS.items():
        if re.search(rf"\b{word}\s+(?:mutual\s+)?(?:funds?|schemes?)\b", q, re.I):
            return n
    return None


def _active_sector_equity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedicated sector/thematic equity only. Never arbitrage, hybrid, or passive."""
    dedicated = [
        r
        for r in rows
        if r.get("sector_purity") == "dedicated_sectoral"
        and r.get("sector_purity") != "defensive_neutral"
    ]
    if dedicated:
        return dedicated
    return [
        r
        for r in rows
        if r.get("sector_purity") == "diversified_equity"
        and not r.get("passive_sector_product")
    ]


def _as_date(value: Any) -> date | None:
    text = str(value or "")[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _drop_stale_nav(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop a NAV that is more than 45 days behind the newest date in this batch."""
    dated = [day for day in (_as_date(row.get("latest_date")) for row in rows) if day is not None]
    if not dated:
        return rows
    newest = max(dated)
    kept: list[dict[str, Any]] = []
    for row in rows:
        day = _as_date(row.get("latest_date"))
        if day is None or (newest - day).days <= _STALE_NAV_DAYS:
            kept.append(row)
    return kept


def _round_fund_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for key in (
        "return_1w_pct",
        "return_1m_pct",
        "return_3m_pct",
        "return_1y_pct",
        "sector_weight_pct",
        "weight_pct",
        "return_pct",
    ):
        value = out.get(key)
        if value is None:
            continue
        try:
            out[key] = round(float(value), 2)
        except (TypeError, ValueError):
            continue
    return out


def _return_direction_in_question(question: str) -> str:
    text = question or ""
    if re.search(r"\b(negatively|negative|hurt|losing|down)\b", text, re.I):
        return "negative"
    if re.search(r"\b(positively|positive|performing|doing\s+well|working\s+well)\b", text, re.I):
        return "positive"
    return ""


def _heavy_and_return(question: str) -> bool:
    text = question or ""
    heavy = bool(re.search(r"\b(heavily\s+invested|exposure|invested\s+in)\b", text, re.I))
    return heavy and bool(_return_direction_in_question(text))


def _exposure_ask(question: str) -> bool:
    text = question or ""
    if re.search(
        r"\b(performing|performance|returns?|doing\s+well|working\s+well|positively|negatively|affected|benefiting|benefit|compare)\b",
        text,
        re.I,
    ):
        return False
    return bool(re.search(r"\b(heavily\s+invested|exposure|allocation|invested\s+in)\b", text, re.I))


def select_funds_by_nav(
    rows: list[dict[str, Any]],
    *,
    direction: str,
    top_n: int,
    count_explicit: bool,
    return_window: str = "1M",
    sort_by: Literal["performance", "exposure"] = "performance",
) -> tuple[list[dict[str, Any]], bool, str]:
    """
    Sort by the requested NAV window.
    Positive keeps only gains in that window. Negative keeps only declines.
    """
    window = normalize_return_window(return_window)
    field = _window_field(window)
    if not rows:
        return [], False, "No sector equity funds were found."
    ordered = _drop_stale_nav(
        enrich_rankings_with_nav(
            rows,
            direction="any",
            top_n=len(rows),
            sort_by="performance",
        )
    )
    if sort_by == "exposure":
        ordered.sort(key=lambda row: float(row.get("sector_weight_pct") or 0), reverse=True)
        dir_clean = str(direction or "any").strip().lower()
        if dir_clean == "positive":
            ordered = [row for row in ordered if row.get(field) is not None and float(row[field]) > 0]
        elif dir_clean == "negative":
            ordered = [row for row in ordered if row.get(field) is not None and float(row[field]) < 0]
        if not ordered and dir_clean in ("positive", "negative"):
            return [], True, f"No screened funds are both heavy in the sector and {dir_clean} on {window}."
        picked = [_round_fund_row(row) for row in ordered[:top_n]]
        note = "Funds with the heaviest weight in the named sector."
        if dir_clean in ("positive", "negative"):
            note = f"Funds with a heavy sector weight and a {dir_clean} {window} return."
        return picked, False, note
    measured = [r for r in ordered if r.get(field) is not None]
    if not measured:
        return [], False, f"NAV returns were not available for the {window} window."
    dir_clean = str(direction or "any").strip().lower()

    def _ret(row: dict[str, Any]) -> float:
        return float(row[field])

    gainers = [r for r in measured if _ret(r) > 0]
    if dir_clean == "negative":
        losers = [r for r in measured if _ret(r) < 0]
        losers.sort(key=_ret)
        n = top_n if count_explicit else min(5, max(3, len(losers)))
        n = min(n, len(losers)) if losers else 0
        return [_round_fund_row(row) for row in losers[:n]], False, f"Weakest {window} NAV returns among the screened funds."
    if dir_clean == "positive" and gainers:
        gainers.sort(key=_ret, reverse=True)
        n = top_n if count_explicit else min(5, len(gainers))
        return [_round_fund_row(row) for row in gainers[:n]], False, f"Funds with a positive {window} NAV return."
    if dir_clean == "positive":
        return (
            [],
            True,
            f"No screened funds have a positive {window} NAV return.",
        )
    if dir_clean == "any" and not gainers:
        n = top_n if count_explicit else 3
        n = min(n, len(measured))
        return (
            [_round_fund_row(row) for row in measured[:n]],
            True,
            "The sector equity universe is down on a 1-month basis. These are the most resilient names by lowest drawdown.",
        )
    n = top_n if count_explicit else min(5, len(measured))
    return [_round_fund_row(row) for row in measured[:n]], False, "Strongest 1-month NAV returns among dedicated sector equity funds."


def _performance_sort_key(row: dict[str, Any], *, reverse: bool = True) -> tuple:
    """Higher 1M / 1W NAV % first when reverse=True (best performers)."""
    m1 = row.get("return_1m_pct")
    w1 = row.get("return_1w_pct")
    m_val = float(m1) if m1 is not None else (-999.0 if reverse else 999.0)
    w_val = float(w1) if w1 is not None else (-999.0 if reverse else 999.0)
    weight = float(row.get("sector_weight_pct") or 0.0)
    return (m_val, w_val, weight)


def _sort_ranked_by_performance(
    rows: list[dict[str, Any]],
    *,
    direction: str,
    top_n: int,
) -> list[dict[str, Any]]:
    dir_clean = str(direction or "any").strip().lower()
    if dir_clean == "negative":
        pool = [r for r in rows if r.get("nav_direction_match")]
        pool.sort(key=lambda r: _performance_sort_key(r, reverse=False))
        return pool[:top_n]
    if dir_clean == "positive":
        pool = [r for r in rows if r.get("nav_direction_match")]
        pool.sort(key=lambda r: _performance_sort_key(r, reverse=True), reverse=True)
        return pool[:top_n]
    rows.sort(key=lambda r: _performance_sort_key(r, reverse=True), reverse=True)
    return rows[:top_n]


def enrich_rankings_with_nav(
    rankings: list[dict[str, Any]],
    *,
    direction: str = "any",
    top_n: int = 5,
    sort_by: Literal["exposure", "performance"] = "exposure",
) -> list[dict[str, Any]]:
    """
    Enriches candidate funds with 1-week and 1-month NAV returns from live/cached NAV service.
    If direction is 'positive' or 'negative', prioritizes funds whose return matches the direction.
    When sort_by=performance, orders by 1M then 1W NAV.
    Positive keeps only funds with a positive 1-month return. Negative keeps only declines.
    Unspecified direction returns the strongest 1-month results, gains or losses.
    """
    enriched: list[dict[str, Any]] = []
    dir_clean = str(direction or "any").strip().lower()

    from concurrent.futures import ThreadPoolExecutor

    def _fetch_nav_one(row: dict[str, Any]) -> dict[str, Any]:
        isin = str(row.get("isin") or "").strip().upper()
        if not isin:
            return {**row, "nav_direction_match": False}
        ret_1w = None
        ret_1m = None
        ret_3m = None
        ret_1y = None
        latest_nav = None
        latest_date = None
        try:
            nav_res = get_fund_nav_history(isin)
            if nav_res.get("success"):
                latest_nav = nav_res.get("latest_nav")
                latest_date = nav_res.get("latest_date")
                stats = nav_res.get("stats") or {}
                parsed: dict[str, float | None] = {}
                for label, stat_key in (("1W", "1W"), ("1M", "1M"), ("3M", "3M"), ("1Y", "1Y")):
                    block = stats.get(stat_key) or {}
                    if "change_pct" in block and block["change_pct"] is not None:
                        parsed[label] = float(block["change_pct"])
                    else:
                        parsed[label] = None
                ret_1w = parsed["1W"]
                ret_1m = parsed["1M"]
                ret_3m = parsed["3M"]
                ret_1y = parsed["1Y"]
        except Exception:
            pass

        chosen = ret_1m if ret_1m is not None else ret_1w
        match_direction = True
        if dir_clean == "positive":
            match_direction = chosen is not None and chosen > 0
        elif dir_clean == "negative":
            match_direction = chosen is not None and chosen < 0

        return {
            **row,
            "latest_nav": latest_nav,
            "latest_date": latest_date,
            "return_1w_pct": ret_1w,
            "return_1m_pct": ret_1m,
            "return_3m_pct": ret_3m,
            "return_1y_pct": ret_1y,
            "nav_direction_match": match_direction,
        }

    valid_rankings = [r for r in rankings if str(r.get("isin") or "").strip()]
    if not valid_rankings:
        return []

    with ThreadPoolExecutor(max_workers=min(12, len(valid_rankings))) as pool:
        enriched = list(pool.map(_fetch_nav_one, valid_rankings))

    if sort_by == "performance":
        return _sort_ranked_by_performance(enriched, direction=dir_clean, top_n=top_n)

    if dir_clean == "positive":
        matching = [r for r in enriched if r.get("nav_direction_match")]
        matching.sort(
            key=lambda r: _performance_sort_key(r, reverse=True),
            reverse=True,
        )
        return matching[:top_n]

    if dir_clean == "negative":
        matching = [r for r in enriched if r.get("nav_direction_match")]
        matching.sort(key=lambda r: _performance_sort_key(r, reverse=False))
        return matching[:top_n]

    return enriched[:top_n]


def _sector_fund_candidate_pool(rankings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Prefer dedicated sector/thematic schemes; drop arbitrage/hybrid and passive products."""
    sectoral = [r for r in rankings if r.get("sector_purity") == "dedicated_sectoral"]
    if sectoral:
        return sectoral
    active = [
        r
        for r in rankings
        if r.get("sector_purity") not in ("defensive_neutral", "passive", "debt")
    ]
    return active or [r for r in rankings if r.get("sector_purity") != "defensive_neutral"]


def run_sector_funds(
    need: DataNeed,
    *,
    direction: str = "any",
    question: str = "",
    return_window: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    idx = get_sector_fund_ranking_index()
    text = (need.sector_name or need.semantic_query or "").strip()
    perf_blob = f"{question} {text}".strip()
    performance_query = bool(_PERFORMANCE_QUESTION_RE.search(perf_blob))
    rank_direction = str(direction or "any").strip().lower() or "any"
    window = infer_return_window(question, return_window)
    keys = idx.resolve_from_question(text) if text else []
    if not keys:
        lower = text.lower()
        if any(w in lower for w in ("gold", "silver", "bullion", "precious")):
            keys = idx.resolve_sector_keys(["Non - Ferrous Metals", "Ferrous Metals"])
        elif any(w in lower for w in ("oil", "crude", "energy", "barrel", "petroleum", "power")):
            keys = idx.resolve_sector_keys(["Petroleum Products", "Power"])
        else:
            keys = []
    limit = 80
    ranked = rank_funds_by_sector_exposure(keys, limit=limit, combine="max")
    from news_rag.fund_search import get_fund_index

    index = get_fund_index()
    rankings = []
    for row in ranked.get("rankings") or []:
        isin = row.get("isin")
        catalog = index.catalog_entry(str(isin)) if isin else None
        name = (
            row.get("fund_name")
            or (catalog or {}).get("fund_short_name")
            or (catalog or {}).get("fund_name")
            or isin
        )
        breakdown = row.get("sector_breakdown") or {}
        matched = list(breakdown.keys())[:5] if isinstance(breakdown, dict) else []
        rankings.append(
            {
                **row,
                "fund_name": name,
                "matched_sectors": matched,
                "category": row.get("category") or (catalog or {}).get("category") or "",
                "scheme_type": row.get("scheme_type") or (catalog or {}).get("scheme_type") or "",
            }
        )
    explicit = explicit_fund_count(question)
    count_explicit = explicit is not None
    top_n = explicit if explicit is not None else max(need.top_n or 0, 5)
    pool = _active_sector_equity(rankings)
    final_rankings, all_drawdown, ranking_note = select_funds_by_nav(
        pool,
        direction=rank_direction,
        top_n=top_n,
        count_explicit=count_explicit,
        return_window=window,
    )
    elapsed = (time.perf_counter() - started) * 1000
    return _ok(
        {
            "sector_keys": ranked.get("sector_keys"),
            "rankings": final_rankings,
            "defensive_alternatives": ranked.get("defensive_alternatives") or [],
            "query": text,
            "direction": rank_direction,
            "return_window": window,
            "ranking_basis": f"{window}_NAV_direction_filter",
            "ranking_note": ranking_note,
            "all_drawdown": all_drawdown,
            "performance_query": performance_query,
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


def run_fund_portfolio_news(
    detail: dict[str, Any],
    need: DataNeed,
    *,
    question: str,
    query_log: QueryLogger | None = None,
    **filter_kwargs: Any,
) -> dict[str, Any]:
    """Layered retrieval: top holdings, sectors, then macro."""
    from news_rag.fund_portfolio_news import retrieve_layered_fund_news

    started = time.perf_counter()
    holdings = extract_top_holdings(detail, limit=max(need.top_n, 10))
    sectors = extract_top_sectors(detail, limit=8)
    fund_name = str(detail.get("fund_short_name") or detail.get("fund_name") or "")
    window = need.window_days or 30
    articles = retrieve_layered_fund_news(
        holdings=holdings,
        sectors=sectors,
        question=question,
        fund_name=fund_name,
        window_days=window,
        query_log=query_log,
    )
    elapsed = (time.perf_counter() - started) * 1000
    return _ok(
        {
            "articles": articles,
            "fund_name": fund_name,
            "holdings_count": len(holdings),
            "sectors_count": len(sectors),
        },
        elapsed,
    )


def _direction_from_sentiment(sentiment: str | None, api_direction: str | None = None) -> str | None:
    if api_direction and api_direction.strip().lower() in ("positive", "negative"):
        return api_direction.strip().lower()
    if sentiment in ("positive", "negative"):
        return sentiment
    return None


def _layered_news_topics(layer: str, semantic_query: str) -> list[str]:
    """Vector search already scopes the query. A full sentence as a topic filter drops every hit."""
    if layer == "macro_news":
        return []
    query = (semantic_query or "").strip()
    if not query or len(query.split()) > 3 or "?" in query:
        return []
    return [query]


def run_layered_news(
    *,
    layer: str,
    semantic_query: str,
    question: str,
    entity_filters: list[str] | None = None,
    window_days: int | None = None,
    sentiment: str = "any",
    search_focus: str = "",
    query_log: QueryLogger | None = None,
    **filter_kwargs: Any,
) -> dict[str, Any]:
    """holdings_news | sector_news | macro_news retrieval."""
    started = time.perf_counter()
    mode = "event_only"
    entities = list(entity_filters or [])
    if entities:
        from news_rag.news_entity_resolve import resolve_corpus_entities

        entities = resolve_corpus_entities(entities)
    if layer == "holdings_news" and entities:
        mode = "event_plus_entities"
    elif layer == "sector_news" and entities:
        mode = "event_plus_entities"
    elif layer == "macro_news":
        mode = "event_only"
        entities = []
    scope = ScopeRefinement(
        news_entities=entities[:10],
        news_topics=_layered_news_topics(layer, semantic_query),
        search_mode=mode,
    )
    explicit_direction = filter_kwargs.get("direction")
    direction = explicit_direction.strip().lower() if isinstance(explicit_direction, str) else None
    if direction not in ("positive", "negative"):
        direction = None
    if window_days is not None:
        window_days = max(7, int(window_days))
    focus = (search_focus or "").strip().lower()
    blob = f"{semantic_query} {question}".lower()
    use_bullion = layer == "macro_news" and (
        focus in ("gold", "silver")
        or any(w in blob for w in ("gold", "silver", "bullion", "precious metal"))
    )
    if use_bullion and focus in ("gold", "silver"):
        from news_rag.bullion_retrieve import retrieve_bullion_metal_news

        articles = retrieve_bullion_metal_news(
            focus,
            semantic_query or question,
            question=question,
            window_days=window_days,
            query_log=query_log,
        )
    elif use_bullion:
        from news_rag.bullion_retrieve import retrieve_bullion_macro_news

        articles = retrieve_bullion_macro_news(
            semantic_query or question,
            question=question,
            window_days=window_days,
            query_log=query_log,
        )
    else:
        articles = retrieve_scoped_news(
            semantic_query or question,
            scope=scope,
            question=question,
            window_days=window_days,
            direction=direction,
            query_log=query_log,
            **{k: v for k, v in filter_kwargs.items() if k != "direction"},
        )
    for art in articles:
        art["_news_layer"] = layer.replace("_news", "")
        if focus:
            art["_search_focus"] = focus
    elapsed = (time.perf_counter() - started) * 1000
    return _ok({"articles": articles, "layer": layer, "search_focus": focus}, elapsed)


def _broad_working_well_keys(idx) -> list[str]:
    """Sector keys used when the news-led sector has no fund up on the month."""
    labels = (
        "It - Software",
        "Pharmaceuticals & Biotechnology",
        "Healthcare Services",
        "Banks",
        "Automobiles",
        "Capital Goods",
        "FMCG",
        "Consumer Durables",
        "Power",
        "Realty",
    )
    return [name for name in labels if idx.has_sector(name)]


_STYLE_CATEGORIES = (
    "Large Cap",
    "Mid Cap",
    "Small Cap",
    "Large & Mid Cap",
    "Flexi Cap",
    "Multi Cap",
    "ELSS / Tax Saver",
    "Focused",
    "Value / Contra",
    "Dividend Yield",
    "Arbitrage",
    "Balanced Advantage / Dynamic Asset",
    "Aggressive Hybrid",
    "Conservative Hybrid",
    "Multi Asset Allocation",
    "Equity Savings",
)
_AMC_SKIP = {
    "bank",
    "finance",
    "capital",
    "trust",
    "asset",
    "mutual",
    "fund",
    "india",
    "limited",
    "amc",
    "management",
    "the",
    "and",
    "for",
    "from",
    "with",
    "that",
    "this",
    "any",
    "are",
    "who",
    "how",
    "due",
    "not",
    "all",
    "its",
    "was",
    "has",
    "have",
    "what",
    "when",
    "where",
    "which",
    "by",
    "price",
    "one",
    "two",
    "name",
    "last",
    "news",
    "week",
    "month",
    "year",
    "sector",
    "scheme",
    "schemes",
    "funds",
    "stock",
    "stocks",
    "holds",
    "compare",
}


def _catalog_candidates(*, category: str = "", amc: str = "", limit: int = _SCREEN_CANDIDATE_CAP) -> list[dict[str, Any]]:
    from news_rag.fund_universe_agent import get_fund_universe_catalog

    catalog = get_fund_universe_catalog()
    funds = catalog.query(
        category=category or None,
        amc=amc or None,
        limit=max(1, limit),
        enrich_nav=False,
    )
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


def _sector_candidates(sector_name: str, *, question: str, limit: int) -> list[dict[str, Any]]:
    idx = get_sector_fund_ranking_index()
    keys = idx.resolve_sector_keys([sector_name]) if sector_name else []
    if not keys:
        keys = idx.resolve_from_question(sector_name or question) or []
    if not keys:
        return []
    ranked = rank_funds_by_sector_exposure(keys, limit=limit, combine="max")
    rows: list[dict[str, Any]] = []
    for row in ranked.get("rankings") or []:
        breakdown = row.get("sector_breakdown") or {}
        rows.append(
            {
                **row,
                "matched_sectors": list(breakdown.keys())[:5] if isinstance(breakdown, dict) else [],
            }
        )
    return rows


def screen_hints_from_question(question: str) -> dict[str, str]:
    """Sector, category, AMC, and stock written in the question. No example query is special-cased."""
    from news_rag.fund_universe_agent import _CATEGORY_PATTERNS, get_fund_universe_catalog
    from news_rag.sector_fund_ranking import _SECTOR_ALIASES

    text = question or ""
    low = text.lower()
    hints = {"sector_name": "", "category": "", "amc": "", "stock_name": ""}
    best = ""
    for alias in sorted(_SECTOR_ALIASES, key=len, reverse=True):
        if alias == "it":
            if not re.search(r"\bIT\b|it sector|information technology", text):
                continue
        elif not re.search(rf"\b{re.escape(alias)}\b", low):
            continue
        best = alias
        break
    hints["sector_name"] = best
    for name in _STYLE_CATEGORIES:
        patterns = next((pats for cat, _stype, _sub, pats in _CATEGORY_PATTERNS if cat == name), [])
        if any(re.search(pat, low) for pat in patterns):
            hints["category"] = name
            break
    stock = re.search(
        r"\bhold(?:s|ing)?\s+([A-Za-z][A-Za-z0-9&.\- ]{1,40}?)(?:\s+stocks?|\s+shares|\s+and\b|\s+how\b|[?.]|$)",
        text,
        re.I,
    )
    if stock:
        hints["stock_name"] = stock.group(1).strip(" .")
    catalog = get_fund_universe_catalog()
    catalog.ensure_loaded()
    amc_best = ""
    for amc in catalog.amcs:
        for token in re.split(r"[^A-Za-z0-9]+", amc):
            if len(token) < 3 or token.lower() in _AMC_SKIP:
                continue
            if hints["stock_name"] and token.lower() in hints["stock_name"].lower():
                continue
            if re.search(rf"\b{re.escape(token)}\b", text, re.I) and len(token) > len(amc_best):
                amc_best = token
    hints["amc"] = amc_best
    return hints


def _args_from_question(
    *,
    sector_name: str,
    category: str,
    amc: str,
    stock_name: str,
    direction: str,
    question: str,
) -> tuple[str, str, str, str, str, bool]:
    """The sector, category, or stock written in the question overrides a large-cap guess."""
    if not question:
        asked = str(direction or "any").strip().lower() or "any"
        return sector_name, category, amc, stock_name, asked, False
    hints = screen_hints_from_question(question)
    sector = hints.get("sector_name") or ""
    if not sector and sector_name and re.search(rf"\b{re.escape(sector_name)}\b", question, re.I):
        sector = sector_name
    category_out = hints.get("category") or ""
    amc_out = hints.get("amc") or ""
    if amc and re.search(rf"\b{re.escape(amc)}\b", question, re.I):
        amc_out = amc
    stock = hints.get("stock_name") or ""
    if stock_name and stock_name.lower() in question.lower():
        stock = stock_name
    asked = str(direction or "any").strip().lower() or "any"
    heavy_return = bool(sector) and _heavy_and_return(question)
    exposure = bool(sector) and (_exposure_ask(question) or heavy_return)
    if heavy_return:
        asked = _return_direction_in_question(question) or asked
    elif exposure:
        asked = "any"
    return sector, category_out, amc_out, stock, asked, exposure


def _articles_for_affected_question(question: str, articles: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if articles:
        return articles
    news = run_layered_news(
        layer="macro_news",
        semantic_query=question,
        question=question,
        window_days=7,
    )
    found = (news.get("data") or {}).get("articles") or []
    return found if isinstance(found, list) else []


def run_funds_for_affected_question(
    *,
    question: str,
    direction: str = "any",
    articles: list[dict[str, Any]] | None = None,
    top_n: int = 5,
    return_window: str | None = None,
    query_log: Any = None,
) -> dict[str, Any]:
    """Pick sectors from the news, then rank funds in those sectors and that direction."""
    from news_rag.affected_sectors import pick_affected_sectors

    started = time.perf_counter()
    window = infer_return_window(question, return_window)
    asked = str(direction or "any").strip().lower() or "any"
    n = max(1, int(top_n or 5))
    packed = _articles_for_affected_question(question, articles)
    picks = pick_affected_sectors(
        question=question,
        articles=packed,
        direction=asked,
        query_log=query_log,
    )
    groups: dict[str, list[str]] = {"positive": [], "negative": []}
    reasons: dict[str, str] = {}
    for pick in picks:
        groups.setdefault(pick["direction"], []).append(pick["name"])
        reasons[pick["name"]] = pick.get("reason") or ""
    rankings: list[dict[str, Any]] = []
    notes: list[str] = []
    order = ["positive", "negative"] if asked == "any" else [asked]
    for group_direction in order:
        names = groups.get(group_direction) or []
        if not names:
            continue
        ranked = run_affected_funds(
            sector_names=names,
            top_n=n,
            direction=group_direction,
            count_explicit=True,
            return_window=window,
            question=question,
            allow_broad_fallback=False,
        )
        data = ranked.get("data") or {}
        rows = data.get("rankings") or []
        if not rows:
            notes.append(
                f"No fund in {', '.join(names)} has a {group_direction} {window} return."
            )
            continue
        for row in rows:
            matched = row.get("matched_sectors") or names
            sector = matched[0] if matched else names[0]
            rankings.append(
                {
                    **row,
                    "affected_direction": group_direction,
                    "sector_reason": reasons.get(sector) or reasons.get(names[0]) or "",
                }
            )
    if not rankings and packed:
        from news_rag.affected_sectors import pick_affected_companies
        from news_rag.stock_fund_ranking import funds_holding_stock

        for company in pick_affected_companies(
            question=question,
            articles=packed,
            direction=asked,
            query_log=query_log,
        ):
            payload = funds_holding_stock(company, limit=max(n, 2))
            holders = list(payload.get("funds") or [])
            if not holders:
                notes.append(str(payload.get("note") or f"No scheme holding {company} was confirmed."))
                continue
            holder_rows, _draw, holder_note = select_funds_by_nav(
                holders,
                direction=asked if asked in ("positive", "negative") else "any",
                top_n=n,
                count_explicit=True,
                return_window=window,
            )
            if not holder_rows and asked in ("positive", "negative"):
                notes.append(holder_note)
                continue
            chosen = holder_rows or holders[:n]
            for row in chosen:
                rankings.append(
                    {
                        **row,
                        "stock_name": payload.get("stock_name") or company,
                        "affected_direction": asked,
                        "sector_reason": f"Holds {payload.get('stock_name') or company}.",
                    }
                )
            if rankings:
                break
    note = " ".join(notes)
    if not picks and not rankings:
        note = "No sector from the news list matched the asked direction."
    elapsed = (time.perf_counter() - started) * 1000
    return _ok(
        {
            "rankings": rankings[:n] if asked != "any" else rankings[: max(n, n * 2)],
            "funds": rankings[:n] if asked != "any" else rankings[: max(n, n * 2)],
            "direction": asked,
            "return_window": window,
            "ranking_note": note,
            "all_drawdown": False,
            "sector_picks": picks,
            "sectors": [pick["name"] for pick in picks],
        },
        elapsed,
    )


def run_screen_funds(
    *,
    sector_name: str = "",
    category: str = "",
    amc: str = "",
    stock_name: str = "",
    direction: str = "any",
    return_window: str | None = None,
    top_n: int = 5,
    question: str = "",
) -> dict[str, Any]:
    """Filter the catalog and sector weights locally, then keep rows whose window return matches direction."""
    from news_rag.affected_sectors import question_needs_affected_sectors
    from news_rag.stock_fund_ranking import funds_holding_stock, holder_candidates_for_stock

    if question and question_needs_affected_sectors(question):
        return run_funds_for_affected_question(
            question=question,
            direction=direction,
            top_n=top_n,
            return_window=return_window,
        )
    started = time.perf_counter()
    sector_name, category, amc, stock_name, asked, exposure = _args_from_question(
        sector_name=sector_name,
        category=category,
        amc=amc,
        stock_name=stock_name,
        direction=direction,
        question=question,
    )
    window = infer_return_window(question, return_window)
    n = max(1, int(top_n or 5))
    sector_rows = (
        _sector_candidates(sector_name, question=question or sector_name, limit=_SCREEN_CANDIDATE_CAP)
        if sector_name
        else []
    )
    catalog_rows = (
        _catalog_candidates(category=category, amc=amc, limit=_SCREEN_CANDIDATE_CAP)
        if category or amc
        else []
    )
    if sector_rows and catalog_rows:
        allowed = {str(row.get("isin") or "") for row in catalog_rows}
        candidates = [row for row in sector_rows if str(row.get("isin") or "") in allowed]
    elif sector_rows:
        candidates = sector_rows
    else:
        candidates = catalog_rows
    archive_count = None
    scan_note = ""
    if stock_name:
        batch = candidates[:_SCREEN_CANDIDATE_CAP] if sector_name and candidates else holder_candidates_for_stock(
            stock_name,
            limit=_SCREEN_CANDIDATE_CAP,
        )
        payload = funds_holding_stock(stock_name, limit=max(n, 2), candidates=batch)
        archive_count = payload.get("fund_count")
        scan_note = str(payload.get("note") or "")
        candidates = list(payload.get("funds") or [])
    elif not candidates and not any((sector_name, category, amc)):
        candidates = _catalog_candidates(limit=_PERFORMANCE_SAMPLE)
    broad = candidates[:_PERFORMANCE_SAMPLE]
    pool = broad
    if sector_name and not category and not amc and not stock_name:
        pool = _active_sector_equity(broad)
    rankings, all_drawdown, ranking_note = select_funds_by_nav(
        pool,
        direction=asked,
        top_n=n,
        count_explicit=True,
        return_window=window,
        sort_by="exposure" if exposure else "performance",
    )
    if exposure and asked in ("positive", "negative") and not rankings and pool is not broad:
        rankings, all_drawdown, ranking_note = select_funds_by_nav(
            broad,
            direction=asked,
            top_n=n,
            count_explicit=True,
            return_window=window,
            sort_by="exposure",
        )
    if scan_note and not rankings:
        ranking_note = f"{ranking_note} {scan_note}".strip()
    elapsed = (time.perf_counter() - started) * 1000
    return _ok(
        {
            "rankings": rankings,
            "funds": rankings,
            "direction": asked,
            "return_window": window,
            "ranking_note": ranking_note,
            "all_drawdown": all_drawdown,
            "fund_count": archive_count,
            "sector_name": sector_name,
            "category": category,
            "amc": amc,
            "stock_name": stock_name,
        },
        elapsed,
    )


def run_affected_funds(
    *,
    sector_names: list[str],
    top_n: int = 5,
    semantic_query: str = "",
    direction: str = "any",
    count_explicit: bool = False,
    return_window: str | None = None,
    question: str = "",
    allow_broad_fallback: bool = True,
) -> dict[str, Any]:
    started = time.perf_counter()
    window = infer_return_window(question or semantic_query, return_window)
    idx = get_sector_fund_ranking_index()
    keys = idx.resolve_sector_keys(sector_names) if sector_names else []
    if not keys and semantic_query:
        keys = idx.resolve_from_question(semantic_query) or []
    limit = 80
    ranked = rank_funds_by_sector_exposure(keys, limit=limit, combine="max")
    from news_rag.fund_search import get_fund_index

    index = get_fund_index()
    rankings = []
    for row in ranked.get("rankings") or []:
        isin = row.get("isin")
        catalog = index.catalog_entry(str(isin)) if isin else None
        name = (
            row.get("fund_name")
            or (catalog or {}).get("fund_short_name")
            or (catalog or {}).get("fund_name")
            or isin
        )
        breakdown = row.get("sector_breakdown") or {}
        matched = list(breakdown.keys())[:5] if isinstance(breakdown, dict) else []
        rankings.append(
            {
                **row,
                "fund_name": name,
                "matched_sectors": matched,
                "category": row.get("category") or (catalog or {}).get("category") or "",
                "scheme_type": row.get("scheme_type") or (catalog or {}).get("scheme_type") or "",
            }
        )
    pool = _active_sector_equity(rankings)
    display_n = top_n if count_explicit else max(top_n, 3)
    final_rankings, all_drawdown, ranking_note = select_funds_by_nav(
        pool,
        direction=direction,
        top_n=display_n,
        count_explicit=count_explicit,
        return_window=window,
    )
    if allow_broad_fallback and str(direction).strip().lower() == "positive" and not final_rankings:
        broad_ranked = rank_funds_by_sector_exposure(
            _broad_working_well_keys(idx),
            limit=60,
            combine="max",
        )
        broad_rows = []
        seen = {str(r.get("isin") or "") for r in rankings}
        for row in broad_ranked.get("rankings") or []:
            isin = str(row.get("isin") or "")
            if not isin or isin in seen:
                continue
            catalog = index.catalog_entry(isin)
            name = row.get("fund_name") or (catalog or {}).get("fund_short_name") or isin
            breakdown = row.get("sector_breakdown") or {}
            broad_rows.append(
                {
                    **row,
                    "fund_name": name,
                    "matched_sectors": list(breakdown.keys())[:5] if isinstance(breakdown, dict) else [],
                    "category": row.get("category") or (catalog or {}).get("category") or "",
                    "scheme_type": row.get("scheme_type") or (catalog or {}).get("scheme_type") or "",
                }
            )
        extra_pool = _active_sector_equity(broad_rows)
        final_rankings, all_drawdown, ranking_note = select_funds_by_nav(
            extra_pool,
            direction="positive",
            top_n=display_n,
            count_explicit=count_explicit,
            return_window=window,
        )
        if final_rankings:
            ranking_note = (
                "Dedicated funds in the news-led sectors are not up on a 1-month basis. "
                "These names are sector equity funds with a positive 1-month NAV."
            )
    elapsed = (time.perf_counter() - started) * 1000
    return _ok(
        {
            "sector_keys": ranked.get("sector_keys"),
            "rankings": final_rankings,
            "defensive_alternatives": [],
            "sectors": sector_names,
            "direction": direction,
            "return_window": window,
            "ranking_note": ranking_note,
            "all_drawdown": all_drawdown,
        },
        elapsed,
    )


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
