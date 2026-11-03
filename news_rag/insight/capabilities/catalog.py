"""Six capability facades — the only tools the planner and wave executor see.

Each capability delegates to existing adapters in layer_tools.py and tool_runners.py.
The planner schema uses these six names; the executor validates args via Pydantic and
enforces fan-out caps from settings.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Capability definitions
# ---------------------------------------------------------------------------

CAPABILITIES: dict[str, dict[str, Any]] = {
    "get_fund_data": {
        "description": (
            "One named mutual fund scheme: NAV, day change, benchmark, category, 52-week range, "
            "regular expense ratio, exit load, AUM, return windows, minimum investment, asset mix, "
            "market-cap mix, holding count, top-5 and top-10 weights, maximum drawdown, "
            "the SEBI riskometer, and the RupeeStop score. "
            "Request only the modules the question needs. "
            "Direct expense ratio is included only when the user asks for the direct plan. "
            "When no return period is named, windows are 1Y, 3Y, and 5Y. "
            "When the user names a period, windows is only that period."
        ),
        "when_to_use": (
            "User names a specific scheme (e.g. HDFC Large Cap Fund) and asks NAV, returns, "
            "how it is doing, why it moved, or who manages it. NOT for listing unnamed funds."
        ),
        "do_not_use": (
            "Do not use for 'which funds hold banking' or 'top 5 funds in IT sector' — use "
            "screen_funds_by_exposure. Do not use for holdings inside a fund — use get_portfolio_data."
        ),
        "modules": ["snapshot", "return_series", "attribution", "managers", "drawdown", "risk", "vs_benchmark", "rating", "limits", "composition"],
        "args_schema": {
            "modules": {"type": "list", "items": ["snapshot", "return_series", "attribution", "managers", "drawdown", "risk", "vs_benchmark", "rating", "limits", "composition"]},
            "include_category": {"type": "bool", "default": False},
            "pillars": {"type": "bool", "default": False},
            "windows": {
                "type": "list",
                "items": "A period code: 1D, 1W, 2W, 1M, 2M, 6M, 8M, 1Y, 3Y, or YTD. Default 1Y, 3Y, 5Y when the user names no period. List only the periods the user named.",
            },
            "periods": {"type": "list", "items": ["1y", "3y", "5y", "10y", "inception"]},
            "window_days": {"type": "int", "min": 7, "max": 365, "default": 30},
            "top_n": {"type": "int", "min": 3, "max": 12, "default": 3},
        },
        "per_fund": True,
    },
    "get_portfolio_data": {
        "description": (
            "What a named mutual fund holds: top stocks and/or sector weights inside that scheme."
        ),
        "when_to_use": (
            "Top stocks, shares, or holdings inside one named fund: sections [\"holdings\"] and top_n from the question. "
            "Top sectors inside one fund: sections [\"sectors\"] only. "
            "Both only when the user asked for the whole portfolio. A misspelled word still means the slice they intended."
        ),
        "do_not_use": (
            "NOT when user asks which funds are invested in banking/HDFC Bank/ a sector — "
            "that is screen_funds_by_exposure (reverse lookup across many funds)."
        ),
        "args_schema": {
            "sections": {"type": "list", "items": ["holdings", "sectors", "count"]},
            "top_n": {"type": "int", "min": 1, "max": 50, "default": 3},
            "find": {"type": "str", "max_len": 80},
        },
        "per_fund": True,
    },
    "compare_funds": {
        "description": (
            "One call comparing two or more named funds. "
            "mode is metrics, overlap, or both. Do not pass modules."
        ),
        "when_to_use": "The user names two or more schemes and asks to compare them.",
        "do_not_use": "Do not call get_fund_data once per fund instead of this tool.",
        "args_schema": {
            "mode": {"type": "str", "enum": ["metrics", "overlap", "both"], "default": "both"},
        },
        "per_fund": False,
    },
    "get_macro_news": {
        "description": (
            "Fresh news for every macro topic, two articles each. "
            "Topics are gold, crude, rupee, RBI, inflation, Nifty, Bank Nifty, and the other named macro parameters."
        ),
        "when_to_use": (
            "A sector overview, or a market-wide question such as what is happening in the market "
            "or why returns are weak, when no single macro topic was already searched."
        ),
        "do_not_use": (
            "Do not use for one named topic such as gold, for a company, or for a fund fact. "
            "Those already have their own news search."
        ),
        "args_schema": {
            "window_days": {"type": "int", "min": 1, "max": 180, "default": 30},
        },
        "per_fund": False,
    },
    "search_financial_news": {
        "description": (
            "News search. scope is all, fund, holdings, sectors, macro, stock, sector, or market. "
            "top_n is at most 8. Use wave 2."
        ),
        "when_to_use": "The user asked for news, or why a move happened and metrics alone are not enough.",
        "do_not_use": "Do not use for a pure NAV, holdings, or sector-weight lookup.",
        "args_schema": {
            "scope": {
                "type": "str",
                "enum": ["all", "fund", "holdings", "sectors", "macro", "stock", "sector", "market"],
            },
            "topics": {"type": "list", "max_items": 8},
            "top_n": {"type": "int", "min": 1, "max": 8, "default": 3},
            "window_days": {"type": "int", "min": 1, "max": 180, "default": 14},
            "direction": {"type": "str", "enum": ["any", "positive", "negative"], "default": "any"},
        },
        "per_fund": False,
    },
    "screen_funds_by_exposure": {
        "description": (
            "Find multiple funds from the catalog: by sector weight, by holding a stock, "
            "by macro driver impact, or by return window when no single fund is named."
        ),
        "when_to_use": (
            "Unnamed funds: sector exposure (argument sector), a stock they hold, or a macro driver. "
            "driver must be a lowercase id such as crude_oil or rbi_repo, with direction positive, negative, or any. "
            "top_n is how many funds to return, from 1 to 20."
        ),
        "do_not_use": (
            "NOT for top holdings inside one named fund — use get_portfolio_data. "
            "NOT for NAV of one fund — use get_fund_data snapshot."
        ),
        "args_schema": {
            "sector": {"type": "str"},
            "driver": {"type": "str"},
            "direction": {"type": "str", "enum": ["positive", "negative", "any"], "default": "any"},
            "top_n": {"type": "int", "min": 1, "max": 20, "default": 5},
            "return_window": {
                "type": "str",
                "enum": ["1W", "1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y"],
                "default": "1M",
            },
            "focus_question": {
                "type": "str",
                "description": "The one part of a multi-part question this screen should match, such as naming one multi cap fund.",
            },
            "random_sample": {"type": "bool", "default": False},
            "require_positive_1y": {"type": "bool", "default": False},
            "rating_screen": {
                "type": "bool",
                "default": False,
                "description": "Use RupeeStop rs-rating/by-category for the scheme category in the question.",
            },
            "pick_alternate": {
                "type": "bool",
                "default": False,
                "description": (
                    "With rating_screen: user wants a different fund in that category, not the top-rated repeat. "
                    "Pair with request.fund_pick alternate_in_category and focus_question set to the category slug only."
                ),
            },
            "compare_pair": {
                "type": "bool",
                "default": False,
                "description": (
                    "With rating_screen: pick two distinct funds in the same category (walk RS label tiers) "
                    "for an unnamed compare-two-funds question."
                ),
            },
            "rating_fetch_n": {
                "type": "int",
                "min": 1,
                "max": 25,
                "description": "How many rated rows to consider before label filtering.",
            },
            "rs_label": {
                "type": "str",
                "description": (
                    "RupeeStop label filter: Best in category, Recommended, Good Choice, Average, or Underperformer. "
                    "When no other fund exists at this label, the server may show the next lower label in the same category."
                ),
            },
        },
        "per_fund": False,
    },
    "get_market_snapshot": {
        "description": (
            "Index returns, sector ranking, macro series, and India 24K gold (INR per 10g). "
            "modules: index_return, sector_ranking, macro_series, metals_spot, stock_quote. "
            "series: crude, brent, wti, usdinr, gold, yield. Gold uses the India 24K per-10g series, not a USD futures price. "
            "metals_spot takes metal gold, windows, and history_months. Do not request silver prices; silver is news only."
        ),
        "when_to_use": "Market or macro level, with no single fund named, or as context next to fund news.",
        "do_not_use": "Do not use this to list funds affected by a driver. That is screen_funds_by_exposure.",
        "args_schema": {
            "modules": {"type": "list", "items": [
                "index_return", "sector_ranking", "macro_series", "metals_spot", "stock_quote",
            ]},
            "stock": {"type": "str", "description": "Company name when modules includes stock_quote"},
            "index": {"type": "str", "default": "nifty50"},
            "window_days": {"type": "int", "min": 1, "max": 365, "default": 30},
            "series": {
                "type": "list",
                "items": ["crude", "brent", "wti", "usdinr", "gold", "yield"],
            },
            "top_n": {"type": "int", "min": 3, "max": 12, "default": 6},
            "metal": {"type": "str", "enum": ["gold", "silver"], "default": "gold"},
            "windows": {
                "type": "list",
                "items": "1D, 1W, 1M, 3M, 6M, 1Y, 3Y, 5Y, or YTD. Used by metals_spot.",
            },
            "history_months": {"type": "int", "min": 1, "max": 240},
        },
        "per_fund": False,
    },
}

INVESTOR_PORTFOLIO_CAPABILITY: dict[str, Any] = {
    "description": (
        "The logged-in investor's own mutual fund book (AUM, holdings, SIP/STP, P&L, XIRR, allocation). "
        "Requires modules — request only what the question needs. "
        "NOT for stocks/sectors inside a catalog scheme (that is get_portfolio_data)."
    ),
    "when_to_use": (
        "portfolio_scope is investor or both: my/I/me/mine + AUM, holdings, SIP, XIRR, allocation, "
        "or a follow-up on holdings_in_chat."
    ),
    "do_not_use": (
        "When portfolio_scope is none or catalog-only. "
        "Do not use for generic fund NAV, compare two unnamed funds, or scheme composition without 'my'."
    ),
    "modules": [
        "meta", "summary", "allocation", "holdings", "pnl_summary", "pnl_scheme",
        "sip", "stp", "xirr", "profile_risk", "concentration",
    ],
    "args_schema": {
        "modules": {
            "type": "list",
            "items": [
                "meta", "summary", "allocation", "holdings", "pnl_summary", "pnl_scheme",
                "sip", "stp", "xirr", "profile_risk", "concentration",
            ],
        },
        "scheme_filter": {"type": "str", "max_len": 120},
        "top_n": {"type": "int", "min": 1, "max": 50, "default": 10},
        "sort_by": {"type": "str", "enum": ["aum", "gain_loss", "xirr"], "default": "aum"},
        "holdings_fields": {"type": "str", "enum": ["minimal", "standard", "full"], "default": "minimal"},
        "transaction_limit": {"type": "int", "min": 1, "max": 15, "default": 5},
        "live_only": {"type": "bool", "default": True},
        "include_meta": {"type": "bool", "default": True},
    },
    "per_fund": False,
}

# Short JSON schemas for the stable planner system prompt
def _capabilities_for_planner(*, portfolio_enabled: bool) -> dict[str, dict[str, Any]]:
    caps = dict(CAPABILITIES)
    if portfolio_enabled:
        caps["get_investor_portfolio"] = INVESTOR_PORTFOLIO_CAPABILITY
    return caps


CAPABILITY_SCHEMAS: dict[str, dict[str, Any]] = {
    name: {
        "description": cap["description"],
        "args": {k: v for k, v in cap["args_schema"].items()},
    }
    for name, cap in CAPABILITIES.items()
}


def capability_catalog_text(*, portfolio_enabled: bool | None = None) -> str:
    """Compact text for the planner system prompt."""
    if portfolio_enabled is None:
        from news_rag.config import get_settings

        portfolio_enabled = get_settings().portfolio_enabled
    lines: list[str] = []
    for name, cap in _capabilities_for_planner(portfolio_enabled=portfolio_enabled).items():
        args = ", ".join(
            f"{k}: {v.get('type', 'str')}" for k, v in cap["args_schema"].items()
        )
        block = f"- **{name}**: {cap['description']}\n  args: {args}"
        if cap.get("when_to_use"):
            block += f"\n  USE WHEN: {cap['when_to_use']}"
        if cap.get("do_not_use"):
            block += f"\n  AVOID WHEN: {cap['do_not_use']}"
        lines.append(block)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------

_MACRO_SERIES = {"crude", "brent", "wti", "usdinr", "gold", "yield"}


def _clamp(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def validate_capability_args(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Validate and clamp capability arguments. Unknown keys are dropped."""
    src = dict(args or {})
    cap = CAPABILITIES.get(tool)
    if cap is None and tool == "get_investor_portfolio":
        cap = INVESTOR_PORTFOLIO_CAPABILITY
    if cap is None:
        return {}

    if tool == "get_fund_data":
        allowed = ("snapshot", "return_series", "attribution", "managers", "drawdown", "risk", "vs_benchmark", "rating", "limits", "composition")
        modules = [m for m in (src.get("modules") or ["snapshot"]) if m in allowed]
        if not modules:
            modules = ["snapshot"]
        out: dict[str, Any] = {
            "modules": modules,
            "window_days": _clamp(src.get("window_days"), 7, 365, 30),
            "top_n": _clamp(src.get("top_n"), 3, 12, 3),
        }
        periods = [str(p).lower() for p in (src.get("periods") or []) if str(p).lower() in ("1y", "3y", "5y", "10y", "inception")]
        if periods:
            out["periods"] = periods
        if src.get("include_category"):
            out["include_category"] = True
        if src.get("pillars"):
            out["pillars"] = True
        if "snapshot" in modules:
            from news_rag.insight.return_windows import DEFAULT_RETURN_WINDOWS, normalize_window_code

            windows = []
            for raw in src.get("windows") or DEFAULT_RETURN_WINDOWS:
                code = normalize_window_code(str(raw))
                if code and code not in windows:
                    windows.append(code)
            if windows:
                out["windows"] = windows
        return out

    if tool == "get_portfolio_data":
        sections = [s for s in (src.get("sections") or ["holdings", "sectors"]) if s in ("holdings", "sectors", "count")]
        out: dict[str, Any] = {
            "sections": sections or ["holdings", "sectors"],
            "top_n": _clamp(src.get("top_n"), 1, 50, 3),
        }
        find = str(src.get("find") or "").strip()
        if find:
            out["find"] = find[:80]
        return out

    if tool == "compare_funds":
        mode = str(src.get("mode") or "both").lower()
        out = {"mode": mode if mode in ("metrics", "overlap", "both") else "both"}
        periods = [
            str(p).lower()
            for p in (src.get("drawdown_periods") or [])
            if str(p).lower() in ("1y", "3y", "5y")
        ]
        if periods:
            out["drawdown_periods"] = periods
        return out

    if tool == "search_financial_news":
        scope = str(src.get("scope") or "market").lower()
        direction = str(src.get("direction") or "any").lower()
        topics = [str(t).strip() for t in (src.get("topics") or []) if str(t).strip()][:8]
        return {
            "scope": scope
            if scope
            in ("all", "fund", "holdings", "sectors", "macro", "stock", "sector", "market")
            else "market",
            "topics": topics,
            "top_n": _clamp(src.get("top_n"), 1, 8, 3),
            "window_days": _clamp(src.get("window_days"), 1, 180, 14),
            "direction": direction if direction in ("any", "positive", "negative") else "any",
        }

    if tool == "screen_funds_by_exposure":
        direction = str(src.get("direction") or "any").lower()
        driver_move = str(src.get("driver_move") or src.get("driver_direction") or "").strip().lower()
        out = {
            "sector": str(src.get("sector") or "").strip()[:80],
            "driver": str(src.get("driver") or "").strip()[:80],
            "direction": direction if direction in ("positive", "negative", "any") else "any",
            "top_n": _clamp(src.get("top_n"), 1, 20, 5),
        }
        if driver_move in ("up", "down", "tighten", "ease", "weaken", "strengthen"):
            out["driver_move"] = driver_move
        rw = str(src.get("return_window") or "").strip().upper()
        if rw in ("1W", "1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y"):
            out["return_window"] = rw
        if src.get("random_sample"):
            out["random_sample"] = True
        if src.get("require_positive_1y"):
            out["require_positive_1y"] = True
        focus = str(src.get("focus_question") or "").strip()
        if focus:
            out["focus_question"] = focus[:180]
        if src.get("rating_screen"):
            out["rating_screen"] = True
        if src.get("pick_alternate"):
            out["pick_alternate"] = True
        if src.get("compare_pair"):
            out["compare_pair"] = True
        rs_label = str(src.get("rs_label") or "").strip()
        if rs_label:
            from news_rag.fund_rating_labels import normalize_rs_label

            out["rs_label"] = normalize_rs_label(rs_label)[:40]
        ex_isins = [str(x).strip().upper() for x in (src.get("exclude_isins") or []) if str(x).strip()]
        if ex_isins:
            out["exclude_isins"] = ex_isins[:20]
        ex_names = [str(x).strip()[:120] for x in (src.get("exclude_names") or []) if str(x).strip()]
        if ex_names:
            out["exclude_names"] = ex_names[:20]
        if src.get("rating_fetch_n") is not None:
            out["rating_fetch_n"] = _clamp(src.get("rating_fetch_n"), 1, 25, 15)
        return out

    if tool == "get_market_snapshot":
        modules = [
            m
            for m in (src.get("modules") or ["index_return"])
            if m in ("index_return", "sector_ranking", "macro_series", "metals_spot", "stock_quote")
        ]
        series = [s for s in (src.get("series") or ["crude", "usdinr"]) if s in _MACRO_SERIES]
        out = {
            "modules": modules or ["index_return"],
            "index": str(src.get("index") or "nifty50").strip()[:80],
            "window_days": _clamp(src.get("window_days"), 1, 365, 30),
            "series": series or ["crude", "usdinr"],
            "top_n": _clamp(src.get("top_n"), 3, 12, 6),
        }
        metal = str(src.get("metal") or "").strip().lower()
        if metal in ("gold", "silver"):
            out["metal"] = metal
        windows = []
        for raw in src.get("windows") or []:
            code = str(raw or "").strip().upper()
            if code and code not in windows:
                windows.append(code)
        if windows:
            out["windows"] = windows[:8]
        if src.get("history_months") is not None:
            out["history_months"] = _clamp(src.get("history_months"), 1, 240, 12)
        stock = str(src.get("stock") or "").strip()
        if stock:
            out["stock"] = stock[:80]
        return out

    if tool == "get_investor_portfolio":
        allowed = set(INVESTOR_PORTFOLIO_CAPABILITY["modules"])
        modules = [m for m in (src.get("modules") or []) if m in allowed]
        out = {
            "modules": modules,
            "top_n": _clamp(src.get("top_n"), 1, 50, 10),
            "sort_by": str(src.get("sort_by") or "aum").lower(),
            "holdings_fields": str(src.get("holdings_fields") or "minimal").lower(),
            "transaction_limit": _clamp(src.get("transaction_limit"), 1, 15, 5),
            "live_only": bool(src.get("live_only", True)),
            "include_meta": bool(src.get("include_meta", True)),
        }
        if out["sort_by"] not in ("aum", "gain_loss", "xirr"):
            out["sort_by"] = "aum"
        if out["holdings_fields"] not in ("minimal", "standard", "full"):
            out["holdings_fields"] = "minimal"
        scheme_filter = str(src.get("scheme_filter") or "").strip()
        if scheme_filter:
            out["scheme_filter"] = scheme_filter[:120]
        return out

    return {}
