"""Layer-1 data tools the planner can call with typed arguments.

Old news tools stay registered for the legacy pipeline. This module adds the data tools
the new path needs and is the only catalog the planner is shown.
"""

from __future__ import annotations

from typing import Any

from news_rag.insight.registry import ToolSpec, register

WINDOWS = ("1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "5Y")
MACRO_SERIES = ("crude", "usdinr", "gold", "silver", "yield")
_SERIES_TICKER = {
    "crude": ("CL=F", "Crude oil"),
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
    "fund_snapshot": "windows: list from 1D 1W 1M 3M 6M 1Y 3Y 5Y (default 1M). Returns NAV, day change, benchmark, category, 52-week range and those returns.",
    "fund_portfolio": "top_n_holdings 1-50 (default 3), top_n_sectors 1-20 (default 3). Use a higher count only when the user asks for a number, such as top 15. find: a company name to look up its weight. include_count: true to also return how many stocks the fund holds.",
    "fund_return_series": "window_days 7-365 (default 180). Monthly NAV path.",
    "fund_attribution": "window_days 7-365 (default 30), top_n 3-12 (default 3). Holding contribution = weight x stock return, computed in code. Include this for any 'how is the fund doing' or 'why did it move' question.",
    "index_return": "index: nifty50, sensex, benchmark (the fund's own), or a sector name. window_days 1-365.",
    "sector_ranking": "window_days 7-365, top_n 3-12. Index return for the main sectors, best and worst.",
    "macro_series": "series: any of crude, usdinr, gold, silver, yield. window_days 1-365.",
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


def _clamp_int(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, number))


def _windows(value: Any, default: tuple[str, ...]) -> list[str]:
    raw = value if isinstance(value, list) else []
    out = [str(v).strip().upper() for v in raw if str(v).strip().upper() in WINDOWS]
    return out or list(default)


def clamp_tool_args(name: str, args: Any) -> dict[str, Any]:
    """Keep only known args and force them into range. Unknown keys are dropped."""
    src = args if isinstance(args, dict) else {}
    if name == "fund_snapshot":
        return {"windows": _windows(src.get("windows"), ("1M",))}
    if name == "fund_portfolio":
        out: dict[str, Any] = {
            "top_n_holdings": _clamp_int(src.get("top_n_holdings"), 1, 50, 3),
            "top_n_sectors": _clamp_int(src.get("top_n_sectors"), 1, 20, 3),
            "include_count": bool(src.get("include_count")),
        }
        find = str(src.get("find") or "").strip()
        if find:
            out["find"] = find[:80]
        return out
    if name == "fund_return_series":
        return {"window_days": _clamp_int(src.get("window_days"), 7, 365, 180)}
    if name == "fund_attribution":
        return {
            "window_days": _clamp_int(src.get("window_days"), 7, 365, 30),
            "top_n": _clamp_int(src.get("top_n"), 3, 12, 3),
        }
    if name == "index_return":
        return {
            "index": str(src.get("index") or "nifty50").strip()[:80] or "nifty50",
            "window_days": _clamp_int(src.get("window_days"), 1, 365, 30),
        }
    if name == "sector_ranking":
        return {
            "window_days": _clamp_int(src.get("window_days"), 7, 365, 30),
            "top_n": _clamp_int(src.get("top_n"), 3, 12, 6),
        }
    if name == "macro_series":
        series = [str(v).strip().lower() for v in (src.get("series") or []) if str(v).strip().lower() in MACRO_SERIES]
        return {
            "series": series or ["crude", "usdinr"],
            "window_days": _clamp_int(src.get("window_days"), 1, 365, 30),
        }
    if name == "stock_snapshot":
        return {"windows": _windows(src.get("windows"), ("1W", "1M"))}
    if name == "compare_funds":
        return {"overlap": bool(src.get("overlap"))}
    if name in ("sector_holdings", "stock_holders"):
        return {"top_n": _clamp_int(src.get("top_n"), 1, 20, 5)}
    if name == "screen_funds":
        window = str(src.get("return_window") or "1M").strip().upper()
        return {"return_window": window if window in WINDOWS else "1M"}
    return {}


NEWS_SCOPES = ("holdings", "sectors", "macro", "stock", "sector", "market")


def clamp_news_scope(raw: Any, *, default_window: int) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    scope = str(raw.get("scope") or "").strip().lower()
    if scope not in NEWS_SCOPES:
        return None
    source = raw.get("source")
    if isinstance(source, list):
        topics = [str(v).strip() for v in source if str(v).strip()][:8]
        source_kind = "list"
    else:
        topics = []
        source_kind = "layer1"
    direction = str(raw.get("direction") or "any").strip().lower()
    if direction not in ("any", "positive", "negative"):
        direction = "any"
    if scope == "market":
        if source_kind == "list" and topics:
            default_top = min(len(topics), 8)
        else:
            from news_rag.insight.market_news import MARKET_PULSE_THEME_COUNT

            default_top = MARKET_PULSE_THEME_COUNT
        top_n = _clamp_int(raw.get("top_n"), 1, 8, default_top)
        default_articles = 3
    else:
        top_n = _clamp_int(raw.get("top_n"), 1, 15, 3)
        default_articles = 2
    return {
        "scope": scope,
        "source": source_kind,
        "topics": topics,
        "top_n": top_n,
        "window_days": _clamp_int(raw.get("window_days"), 1, 180, default_window),
        "direction": direction,
        "articles_per_entity": _clamp_int(raw.get("articles_per_entity"), 1, 4, default_articles),
        "chars_per_article": _clamp_int(raw.get("chars_per_article"), 200, 1600, 900),
        "required": bool(raw.get("required", True)),
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
    windows = set(ctx.get("windows") or ["1M"])
    rets = data.get("returns") if isinstance(data.get("returns"), dict) else {}
    key_map = {
        "1D": "1D", "1W": "1W", "1M": "1M", "3M": "3M", "6M": "6M",
        "1Y": "1Y", "3Y": "3Y", "5Y": "5Y",
    }
    picked = {key_map[w]: rets.get(key_map[w]) for w in windows if key_map.get(w) and rets.get(key_map[w]) is not None}
    # Catalog keys vary (return_1m, 1M, ...). Keep any key that mentions the window.
    if not picked and rets:
        for key, val in rets.items():
            label = str(key).upper().replace("RETURN_", "").replace("_PCT", "")
            if label in windows or any(w in label for w in windows):
                picked[str(key)] = val
    data["returns"] = picked or rets
    data.pop("isin", None)
    return {"ok": True, "data": data}


def run_fund_portfolio(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.fund_search import extract_top_holdings, extract_top_sectors
    from news_rag.insight.tool_runners import _fail

    detail = _detail(ctx)
    if not detail:
        return _fail("fund_not_found")
    n_hold = int(ctx.get("top_n_holdings") or 3)
    n_sec = int(ctx.get("top_n_sectors") or 3)
    holdings = extract_top_holdings(detail, limit=max(n_hold, 50))
    sectors = extract_top_sectors(detail, limit=max(n_sec, 20))
    find = str(ctx.get("find") or "").strip().lower()
    matched = [h for h in holdings if find and find in str(h.get("name") or "").lower()] if find else []
    data: dict[str, Any] = {
        "fund_name": detail.get("fund_short_name") or detail.get("fund_name"),
        "as_on": detail.get("as_on"),
        "holdings": (matched or holdings)[:n_hold],
        "sectors": sectors[:n_sec],
    }
    if ctx.get("include_count") or find:
        data["holding_count"] = len(extract_top_holdings(detail, limit=500))
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
        detail = _detail(ctx)
        bench = str((detail or {}).get("benchmark") or "Nifty 50")
        row = benchmark_return_for_scheme(bench, category=str((detail or {}).get("category") or ""), window_days=window)
        return {"ok": row.get("return_pct") is not None, "data": row, "error": "" if row.get("return_pct") is not None else "no_price"}
    if low in ("nifty", "nifty50", "nifty 50"):
        row = index_return_for_sector("Nifty 50", window_days=window)
        row["benchmark_label"] = "Nifty 50"
        return {"ok": row.get("return_pct") is not None, "data": row}
    if low in ("sensex", "bse"):
        from news_rag.insight.index_series import _yf_return_pct

        pct = _yf_return_pct("^BSESN", window)
        return {"ok": pct is not None, "data": {"benchmark_label": "Sensex", "return_pct": pct, "window_days": window, "yfinance_ticker": "^BSESN"}}
    row = index_return_for_sector(index, window_days=window)
    if not row.get("yfinance_ticker"):
        row["yfinance_ticker"] = nifty50_ticker()
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
    return {"ok": bool(rows), "data": {"leaders": rows[:n], "laggards": list(reversed(rows[-n:])), "window_days": window}}


def run_macro_series_tool(ctx: dict[str, Any]) -> dict[str, Any]:
    from news_rag.insight.index_series import _yf_return_pct

    window = int(ctx.get("window_days") or 30)
    series = []
    for key in ctx.get("series") or ["crude", "usdinr"]:
        ticker, label = _SERIES_TICKER.get(str(key), ("", ""))
        if not ticker:
            continue
        series.append({"series": key, "label": label, "change_pct": _yf_return_pct(ticker, window), "window_days": window})
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
            description="Recent percent change in crude, the rupee, gold, silver or the US 10-year yield.",
            when_to_use="The user asks how crude, the rupee, gold or yields have moved.",
            args=(("series", "crude usdinr gold silver yield"), ("window_days", "1-365")),
            run=run_macro_series_tool,
            cost=2,
        ),
    ]
    for spec in specs:
        register(spec)
