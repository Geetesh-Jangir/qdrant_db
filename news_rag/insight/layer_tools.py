"""Layer-1 data tools the planner can call with typed arguments.

Old news tools stay registered for the legacy pipeline. This module adds the data tools
the new path needs and is the only catalog the planner is shown.
"""

from __future__ import annotations

from typing import Any

from news_rag.insight.planner_policy import horizon_code
from news_rag.insight.registry import ToolSpec, register

# Default `crude` uses ICE Brent (BZ=F) — closer to India import basket than WTI.
_SERIES_TICKER = {
    "crude": ("BZ=F", "Brent crude (ICE)"),
    "brent": ("BZ=F", "Brent crude (ICE)"),
    "wti": ("CL=F", "WTI crude (NYMEX)"),
    "usdinr": ("INR=X", "USD/INR"),
    "gold": ("GC=F", "Gold"),
    "silver": ("SI=F", "Silver"),
    "yield": ("^TNX", "US 10-year yield"),
}

# Tools the planner may name. Old blended news tools are intentionally absent.
PLANNER_TOOLS = (
    "fund_snapshot",
    "fund_portfolio",
    "fund_return_series",
    "fund_attribution",
    "sector_alignment",
    "compare_funds",
    "stock_snapshot",
    "stock_holders",
    "index_return",
    "sector_ranking",
    "macro_series",
    "metals_spot",
    "sector_holdings",
    "screen_funds",
    "sector_funds",
    "driver_affected_funds",
    "macro_sector_impact",
    "trace_relationships",
)

ARG_HELP: dict[str, str] = {
    "fund_snapshot": "windows: 1Y 3Y 5Y when no period is named. A named period such as 1W or 1M is that code only. NAV, day change, and published returns come from the fund payload. NAV history is only for a window the payload does not publish.",
    "fund_portfolio": "top_n_holdings 1-50 (default 3), top_n_sectors 1-20 (default 3). Use a higher count only when the user asks for a number, such as top 15. find: a company name to look up its weight. include_count: true to also return how many stocks the fund holds.",
    "fund_return_series": "window_days 7-365 (default 180). Monthly NAV path.",
    "fund_attribution": "window_days 7-365 (default 30), top_n 3-12 (default 3). Holding contribution = weight x stock return, computed in code. Include this for any 'how is the fund doing' or 'why did it move' question.",
    "index_return": "index: nifty50, sensex, benchmark (the fund's own), or a sector name. window_days 1-365.",
    "sector_ranking": "window_days 7-365, top_n 3-12. Index return for the main sectors, best and worst.",
    "macro_series": "series: crude (Brent BZ=F), brent, wti (CL=F), usdinr, gold, silver, yield. window_days 1-365.",
    "stock_snapshot": "windows: 1W 1M. One call per stock already named.",
    "compare_funds": "overlap: true to add shared holdings. Needs at least two funds.",
    "sector_holdings": "top_n 1-15 companies in the sector.",
    "stock_holders": "top_n 1-20 funds that hold the stock.",
    "screen_funds": "category or amc or sector is taken from the question; return_window 1W 1M 3M 1Y.",
    "sector_funds": "Needs a sector. Ranks funds by weight in it.",
    "driver_affected_funds": "Needs macro_sector_impact first. direction positive or negative.",
    "macro_sector_impact": "Needs a driver. Rule table of sectors that usually gain or lose.",
    "sector_alignment": "One fund. Holdings versus the sector index.",
    "trace_relationships": "Needs a driver or sector plus a fund.",
    "metals_spot": "No args. Gold and silver spot.",
}


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------


def _detail(ctx: dict[str, Any]) -> dict[str, Any] | None:
    from news_rag.insight.tool_runners import _resolve_fund_detail

    return _resolve_fund_detail(ctx)


def run_fund_snapshot(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.insight.tool_runners import _fail, run_fund_nav_adapter

    out = run_fund_nav_adapter(ctx)
    if not out.get("ok"):
        return out
    data = dict(out.get("data") or {})
    from news_rag.insight.return_windows import (
        DEFAULT_RETURN_WINDOWS,
        normalize_window_code,
        published_return,
        returns_for_windows,
    )

    windows: list[str] = []
    for raw in ctx.get("windows") or DEFAULT_RETURN_WINDOWS:
        code = normalize_window_code(str(raw))
        if code and code not in windows:
            windows.append(code)
    if not windows:
        windows = list(DEFAULT_RETURN_WINDOWS)
    published = data.get("returns") if isinstance(data.get("returns"), dict) else {}
    found: dict[str, float] = {}
    missing: list[str] = []
    for code in windows:
        if code == "1D":
            day = data.get("day_change_pct")
            if day is not None:
                try:
                    found["1D"] = float(day)
                except (TypeError, ValueError):
                    missing.append(code)
            else:
                missing.append(code)
            continue
        value = published_return(published, code)
        if value is None:
            missing.append(code)
        else:
            found[code] = value
    isin = str(data.get("isin") or "")
    limits: list[dict[str, str]] = []
    if missing and isin:
        measured, limits = returns_for_windows(
            isin,
            missing,
            inception_date=str(data.get("inception_date") or ""),
        )
        found.update(measured)
    data["returns"] = found
    if limits:
        data["unavailable_returns"] = limits
    data.pop("isin", None)
    from news_rag.fund_rupeestop_metrics import expense_ratio_for_question

    data["expense_ratio"] = expense_ratio_for_question(
        data.get("expense_ratio") if isinstance(data.get("expense_ratio"), dict) else {},
        str(ctx.get("question") or ""),
    )
    return {"ok": True, "data": data}


def run_fund_portfolio(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.fund_search import (
        aggregate_sectors_from_holdings,
        extract_top_holdings,
        extract_top_sectors,
        normalize_holding_row,
        normalize_sector_row,
    )
    from news_rag.insight.tool_runners import _fail

    detail = _detail(ctx)
    if not detail:
        return _fail("fund_not_found")
    sections = list(ctx.get("portfolio_sections") or ["holdings", "sectors"])
    n_hold = int(ctx.get("top_n_holdings") or 3) if "holdings" in sections else 0
    n_sec = int(ctx.get("top_n_sectors") or 3) if "sectors" in sections else 0
    holdings = (
        [normalize_holding_row(h) for h in extract_top_holdings(detail, limit=max(n_hold, 50))]
        if n_hold
        else []
    )
    sectors = (
        [normalize_sector_row(s) for s in extract_top_sectors(detail, limit=max(n_sec, 20))]
        if n_sec
        else []
    )
    sectors_from_holdings = False
    holdings_fallback = False
    if n_sec and not sectors:
        rolled = aggregate_sectors_from_holdings(
            extract_top_holdings(detail, limit=300),
            limit=max(n_sec, 20),
        )
        if rolled:
            sectors = [normalize_sector_row(s) for s in rolled]
            sectors_from_holdings = True
        elif not n_hold:
            n_hold = n_sec
            holdings = [
                normalize_holding_row(h)
                for h in extract_top_holdings(detail, limit=max(n_hold, 50))
            ][:n_hold]
            holdings_fallback = True
    find = str(ctx.get("find") or "").strip().lower()
    matched = [h for h in holdings if find and find in str(h.get("name") or "").lower()] if find else []
    data: dict[str, Any] = {
        "fund_name": detail.get("fund_short_name") or detail.get("fund_name"),
        "as_on": detail.get("as_on"),
        "holdings": (matched or holdings)[:n_hold] if n_hold else [],
        "sectors": sectors[:n_sec] if n_sec else [],
        "sectors_from_holdings": sectors_from_holdings,
        "holdings_fallback": holdings_fallback,
    }
    if ctx.get("include_count") or find:
        count = detail.get("holding_count")
        data["holding_count"] = count if count is not None else len(extract_top_holdings(detail, limit=500))
    if find:
        data["find"] = ctx.get("find")
        data["matches"] = matched[:5]
    return {"ok": True, "data": data}


def run_fund_attribution_tool(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.fund_search import extract_top_holdings
    from news_rag.insight.fund_why import _price_holdings
    from news_rag.insight.holding_attribution import attribute_rows
    from news_rag.insight.tool_runners import _fail, run_fund_nav_adapter

    detail = _detail(ctx)
    if not detail:
        return _fail("fund_not_found")
    window = int(ctx.get("window_days") or 30)
    nav = run_fund_nav_adapter({**ctx, "return_window": "1W" if window <= 10 else "1M"})
    fund_ret = None
    if nav.get("ok"):
        fund_ret = (nav.get("data") or {}).get("window_pct")
    priced = _price_holdings(extract_top_holdings(detail, limit=30), window)
    attr = attribute_rows(priced, fund_return_pct=fund_ret if isinstance(fund_ret, (int, float)) else None)
    top_n = int(ctx.get("top_n") or 6)
    return {
        "ok": True,
        "data": {
            "fund_name": detail.get("fund_short_name") or detail.get("fund_name"),
            "window_days": window,
            "fund_return_pct": attr.get("fund_return_pct"),
            "explained_pct": attr.get("explained_pct"),
            "unexplained_pct": attr.get("unexplained_pct"),
            "detractors": (attr.get("detractors") or [])[:top_n],
            "contributors": (attr.get("contributors") or [])[:top_n],
            "rows": (attr.get("rows") or [])[:top_n],
        },
    }


def run_index_return_tool(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.insight.index_series import benchmark_return_for_scheme, index_return_for_sector
    from lib.nse_sector_indices import nifty50_ticker

    index = str(ctx.get("index") or "nifty50").strip()
    window = int(ctx.get("window_days") or 30)
    low = index.lower()
    if low in ("benchmark", "scheme") and ctx.get("fund_names"):
        from news_rag.insight.index_series import nifty50_reference_returns, scheme_benchmark_metadata

        detail = _detail(ctx)
        bench = str((detail or {}).get("benchmark") or "")
        meta = scheme_benchmark_metadata(bench)
        nifty_by_window: dict[str, float | None] = {}
        for label, days in (("1W", 7), ("1M", 30), ("3M", 90), ("6M", 180), ("1Y", 365)):
            ref = nifty50_reference_returns(window_days=days)
            nifty_by_window[label] = ref.get("return_pct")
        row = {
            **meta,
            "nifty50_reference": {
                "name": "Nifty 50",
                "returns_pct": nifty_by_window,
                "note": "Broad market reference only — not the scheme benchmark index return.",
            },
        }
        return {
            "ok": any(v is not None for v in nifty_by_window.values()),
            "data": row,
            "error": "",
        }
    if low in ("nifty", "nifty50", "nifty 50"):
        row = dict(index_return_for_sector("Nifty 50", window_days=window))
        row["benchmark_label"] = "Nifty 50"
        row["horizon"] = horizon_code(window)
        return {"ok": row.get("return_pct") is not None, "data": row}
    if low in ("sensex", "bse"):
        from news_rag.insight.index_series import _yf_return_pct

        pct = _yf_return_pct("^BSESN", window)
        return {
            "ok": pct is not None,
            "data": {
                "benchmark_label": "Sensex",
                "return_pct": pct,
                "window_days": window,
                "horizon": horizon_code(window),
                "yfinance_ticker": "^BSESN",
            },
        }
    row = dict(index_return_for_sector(index, window_days=window))
    if not row.get("yfinance_ticker"):
        row["yfinance_ticker"] = nifty50_ticker()
    row["horizon"] = horizon_code(window)
    return {"ok": row.get("return_pct") is not None, "data": row, "error": "" if row.get("return_pct") is not None else "no_price"}


def run_sector_ranking_tool(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.insight.index_series import _RANK_SECTORS, index_return_for_sector

    window = int(ctx.get("window_days") or 30)
    rows = []
    for name in _RANK_SECTORS:
        row = index_return_for_sector(name, window_days=window)
        if isinstance(row.get("return_pct"), (int, float)) and not row.get("substituted_broad_index"):
            rows.append({"sector": name, "return_pct": row["return_pct"]})
    rows.sort(key=lambda r: r["return_pct"], reverse=True)
    n = int(ctx.get("top_n") or 6)
    return {
        "ok": bool(rows),
        "data": {
            "leaders": rows[:n],
            "laggards": list(reversed(rows[-n:])),
            "window_days": window,
            "horizon": horizon_code(window),
        },
    }


def run_macro_series_tool(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.insight.index_series import _yf_return_pct

    window = int(ctx.get("window_days") or 30)
    series = []
    raw = ctx.get("series") or ["crude", "usdinr"]
    if isinstance(raw, str):
        series_keys = [k.strip().lower() for k in raw.split(",") if k.strip()]
    elif isinstance(raw, (list, tuple, set)):
        series_keys = [str(k).strip().lower() for k in raw if str(k).strip()]
    else:
        series_keys = ["crude", "usdinr"]
    for key in series_keys:
        ticker, label = _SERIES_TICKER.get(str(key), ("", ""))
        if not ticker:
            continue
        series.append(
            {
                "series": key,
                "label": label,
                "yfinance_ticker": ticker,
                "change_pct": _yf_return_pct(ticker, window),
                "window_days": window,
                "horizon": horizon_code(window),
            }
        )
    return {"ok": any(s.get("change_pct") is not None for s in series), "data": {"series": series}}


def register_layer_tools() -> None:
    specs = [
        ToolSpec(
            name="fund_snapshot",
            provides=frozenset({"fund_facts_nav"}),
            description="NAV, day change, benchmark, category, 52-week range and the returns for the windows asked.",
            when_to_use="Any question about one fund's price, return, benchmark or category. No news.",
            args=(("windows", ARG_HELP["fund_snapshot"]),),
            run=run_fund_snapshot,
            cost=1,
        ),
        ToolSpec(
            name="fund_portfolio",
            provides=frozenset({"fund_composition"}),
            description="Top holdings and top sectors of one fund, with weights. Can look up one company or return the holding count.",
            when_to_use="What a fund holds, its sector mix, the weight of one stock, or how many stocks it owns.",
            args=(("top_n_holdings", "1-50"), ("top_n_sectors", "1-20"), ("find", "company name"), ("include_count", "true/false")),
            run=run_fund_portfolio,
            cost=1,
        ),
        ToolSpec(
            name="fund_attribution",
            provides=frozenset({"fund_attribution"}),
            description="Each large holding's contribution to the fund return (weight times the stock's own return), plus detractors and contributors. Computed in code.",
            when_to_use="Why a fund moved, or which holdings hurt or helped.",
            args=(("window_days", "7-365"), ("top_n", "3-12")),
            run=run_fund_attribution_tool,
            cost=2,
        ),
        ToolSpec(
            name="index_return",
            provides=frozenset({"benchmark"}),
            description="Percent change of Nifty 50, Sensex, a sector index, or the fund's own benchmark.",
            when_to_use="How the market or a sector index did, or whether a fund beat its benchmark.",
            args=(("index", "nifty50 | sensex | benchmark | sector name"), ("window_days", "1-365")),
            run=run_index_return_tool,
            cost=2,
        ),
        ToolSpec(
            name="sector_ranking",
            provides=frozenset({"benchmark"}),
            description="Which of the main sector indexes led and lagged over the window.",
            when_to_use="Which sectors are working and which are not, with numbers.",
            args=(("window_days", "7-365"), ("top_n", "3-12")),
            run=run_sector_ranking_tool,
            cost=3,
        ),
        ToolSpec(
            name="macro_series",
            provides=frozenset({"commodity_spot"}),
            description="Recent percent change in Brent/WTI crude, the rupee, gold, silver or the US 10-year yield (Yahoo Finance).",
            when_to_use="The user asks how crude, the rupee, gold or yields have moved.",
            args=(("series", "crude brent wti usdinr gold silver yield"), ("window_days", "1-365")),
            run=run_macro_series_tool,
            cost=2,
        ),
    ]
    for spec in specs:
        register(spec)
