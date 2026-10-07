"""Tool registry for the ask engine."""

from __future__ import annotations

import re
import time
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


def run_compare_funds(details: list[dict[str, Any]], *, top_n: int = 5) -> dict[str, Any]:
    """Side-by-side NAV, sector weights, and holdings for funds the agent already resolved."""
    started = time.perf_counter()
    funds: list[dict[str, Any]] = []
    for detail in details:
        if not detail:
            continue
        nav = run_fund_nav(detail, DataNeed(tool="fund_nav", scope="with_returns"))
        holdings = run_fund_holdings(detail, DataNeed(tool="fund_holdings", top_n=top_n))
        sectors = run_fund_sectors(detail, DataNeed(tool="fund_sectors", top_n=top_n))
        funds.append(
            {
                "nav": (nav.get("data") if nav.get("ok") else None),
                "holdings": ((holdings.get("data") or {}).get("rows") if holdings.get("ok") else []),
                "sectors": ((sectors.get("data") or {}).get("rows") if sectors.get("ok") else []),
                "scheme_type": detail.get("scheme_type"),
                "category": detail.get("category"),
            }
        )
    elapsed = (time.perf_counter() - started) * 1000
    return _ok({"funds": funds, "count": len(funds)}, elapsed)


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


def select_funds_by_nav(
    rows: list[dict[str, Any]],
    *,
    direction: str,
    top_n: int,
    count_explicit: bool,
) -> tuple[list[dict[str, Any]], bool, str]:
    """
    Sort by 1-month NAV.
    Positive: only funds with a positive 1-month NAV. A working-well question never lists declines.
    """
    if not rows:
        return [], False, "No sector equity funds were found."
    ordered = enrich_rankings_with_nav(
        rows,
        direction="any",
        top_n=len(rows),
        sort_by="performance",
    )
    measured = [r for r in ordered if r.get("return_1m_pct") is not None]
    if not measured:
        return [], False, "NAV returns were not available for these sector funds."
    dir_clean = str(direction or "any").strip().lower()
    gainers = [r for r in measured if float(r["return_1m_pct"]) > 0]
    if dir_clean == "negative":
        losers = [r for r in measured if float(r["return_1m_pct"]) < 0]
        losers.sort(key=lambda r: float(r["return_1m_pct"]))
        n = top_n if count_explicit else min(5, max(3, len(losers)))
        n = min(n, len(losers)) if losers else 0
        return losers[:n], False, "Weakest 1-month NAV returns among dedicated sector equity funds."
    if dir_clean == "positive" and gainers:
        n = top_n if count_explicit else min(5, len(gainers))
        return gainers[:n], False, "Dedicated sector equity funds with positive 1-month NAV returns."
    if dir_clean == "positive":
        n = top_n if count_explicit else min(3, len(measured))
        return (
            measured[:n],
            True,
            "The broader sector equity universe is down on a 1-month basis. These are the most resilient performers by lowest drawdown.",
        )
    if dir_clean == "any" and not gainers:
        n = top_n if count_explicit else 3
        n = min(n, len(measured))
        return (
            measured[:n],
            True,
            "The sector equity universe is down on a 1-month basis. These are the most resilient names by lowest drawdown.",
        )
    n = top_n if count_explicit else min(5, len(measured))
    return measured[:n], False, "Strongest 1-month NAV returns among dedicated sector equity funds."


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
        latest_nav = None
        latest_date = None
        try:
            nav_res = get_fund_nav_history(isin)
            if nav_res.get("success"):
                latest_nav = nav_res.get("latest_nav")
                latest_date = nav_res.get("latest_date")
                stats = nav_res.get("stats") or {}
                w1 = stats.get("1W")
                m1 = stats.get("1M")
                if w1 and "change_pct" in w1 and w1["change_pct"] is not None:
                    ret_1w = float(w1["change_pct"])
                if m1 and "change_pct" in m1 and m1["change_pct"] is not None:
                    ret_1m = float(m1["change_pct"])
        except Exception:
            pass

        match_direction = True
        if dir_clean == "positive":
            if ret_1m is not None:
                match_direction = ret_1m > 0
            else:
                match_direction = ret_1w is not None and ret_1w > 0
        elif dir_clean == "negative":
            if ret_1m is not None:
                match_direction = ret_1m < 0
            else:
                match_direction = ret_1w is not None and ret_1w < 0

        return {
            **row,
            "latest_nav": latest_nav,
            "latest_date": latest_date,
            "return_1w_pct": ret_1w,
            "return_1m_pct": ret_1m,
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
) -> dict[str, Any]:
    started = time.perf_counter()
    idx = get_sector_fund_ranking_index()
    text = (need.sector_name or need.semantic_query or "").strip()
    perf_blob = f"{question} {text}".strip()
    performance_query = bool(_PERFORMANCE_QUESTION_RE.search(perf_blob))
    rank_direction = str(direction or "any").strip().lower() or "any"
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
    )
    elapsed = (time.perf_counter() - started) * 1000
    return _ok(
        {
            "sector_keys": ranked.get("sector_keys"),
            "rankings": final_rankings,
            "defensive_alternatives": ranked.get("defensive_alternatives") or [],
            "query": text,
            "direction": rank_direction,
            "ranking_basis": "1M_NAV_direction_filter",
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


def run_affected_funds(
    *,
    sector_names: list[str],
    top_n: int = 5,
    semantic_query: str = "",
    direction: str = "any",
    count_explicit: bool = False,
) -> dict[str, Any]:
    started = time.perf_counter()
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
    )
    if str(direction).strip().lower() == "positive" and not final_rankings:
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
