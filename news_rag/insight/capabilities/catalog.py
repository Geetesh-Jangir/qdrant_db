"""Six capability facades — the only tools the planner and wave executor see.

Each capability delegates to existing adapters in layer_tools.py and tool_runners.py.
The planner schema uses these six names; the executor validates args via Pydantic and
enforces fan-out caps from settings.
"""

from __future__ import annotations

from typing import Any

from news_rag.insight.contracts import ToolCall

# ---------------------------------------------------------------------------
# Capability definitions
# ---------------------------------------------------------------------------

CAPABILITIES: dict[str, dict[str, Any]] = {
    "get_fund_data": {
        "description": (
            "One named mutual fund scheme: NAV, day change, benchmark, category, 52-week range, "
            "return windows, optional return series / attribution, optional fund managers."
        ),
        "when_to_use": (
            "User names a specific scheme (e.g. HDFC Large Cap Fund) and asks NAV, returns, "
            "how it is doing, why it moved, or who manages it. NOT for listing unnamed funds."
        ),
        "do_not_use": (
            "Do not use for 'which funds hold banking' or 'top 5 funds in IT sector' — use "
            "screen_funds_by_exposure. Do not use for holdings inside a fund — use get_portfolio_data."
        ),
        "modules": ["snapshot", "return_series", "attribution", "managers"],
        "args_schema": {
            "modules": {"type": "list", "items": ["snapshot", "return_series", "attribution", "managers"]},
            "windows": {"type": "list", "items": ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "5Y"]},
            "periods": {"type": "list", "items": ["1W", "1M", "3M", "6M", "1Y"]},
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
            "Phrases like top stocks/shares/holdings/sectors OF or IN a named fund; "
            "what does [Fund X] hold; portfolio composition of one scheme."
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
        "description": "Side-by-side comparison of two or more funds. "
                       "Overlap shows shared holdings with weights.",
        "args_schema": {
            "mode": {"type": "str", "enum": ["metrics", "overlap", "both"], "default": "both"},
        },
        "per_fund": False,
    },
    "search_financial_news": {
        "description": "Search Qdrant for financial news. Returns compact summaries, "
                       "no full bodies unless gap recovery.",
        "args_schema": {
            "scope": {"type": "str", "enum": ["holdings", "sectors", "macro", "stock", "sector", "market"]},
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
            "Any N funds with exposure to a sector (banking, IT, pharma); funds holding a "
            "stock (HDFC Bank); funds affected by crude/RBI; random/top performers in a category."
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
            "random_sample": {"type": "bool", "default": False},
            "require_positive_1y": {"type": "bool", "default": False},
        },
        "per_fund": False,
    },
    "get_market_snapshot": {
        "description": "Nifty / Sensex / sector index returns, sector ranking, "
                       "macro series (Brent crude BZ=F, WTI, rupee, gold, silver, yield), metals spot.",
        "args_schema": {
            "modules": {"type": "list", "items": [
                "index_return", "sector_ranking", "macro_series", "metals_spot", "stock_quote",
            ]},
            "stock": {"type": "str", "description": "Company name when modules includes stock_quote"},
            "index": {"type": "str", "default": "nifty50"},
            "window_days": {"type": "int", "min": 1, "max": 365, "default": 30},
            "series": {
                "type": "list",
                "items": ["crude", "brent", "wti", "usdinr", "gold", "silver", "yield"],
            },
            "top_n": {"type": "int", "min": 3, "max": 12, "default": 6},
        },
        "per_fund": False,
    },
}

# Short JSON schemas for the stable planner system prompt
CAPABILITY_SCHEMAS: dict[str, dict[str, Any]] = {
    name: {
        "description": cap["description"],
        "args": {k: v for k, v in cap["args_schema"].items()},
    }
    for name, cap in CAPABILITIES.items()
}


def capability_catalog_text() -> str:
    """Compact text for the planner system prompt — six tools only."""
    lines: list[str] = []
    for name, cap in CAPABILITIES.items():
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

_WINDOWS = {"1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "5Y"}
_MACRO_SERIES = {"crude", "brent", "wti", "usdinr", "gold", "silver", "yield"}


def _clamp(value: Any, lo: int, hi: int, default: int) -> int:
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default


def validate_capability_args(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    """Validate and clamp capability arguments. Unknown keys are dropped."""
    src = dict(args or {})
    cap = CAPABILITIES.get(tool)
    if cap is None:
        return {}

    if tool == "get_fund_data":
        allowed = ("snapshot", "return_series", "attribution", "managers")
        modules = [m for m in (src.get("modules") or ["snapshot"]) if m in allowed]
        if not modules:
            modules = ["snapshot"]
        out: dict[str, Any] = {
            "modules": modules,
            "window_days": _clamp(src.get("window_days"), 7, 365, 30),
            "top_n": _clamp(src.get("top_n"), 3, 12, 3),
        }
        if "managers" not in modules:
            windows = [w for w in (src.get("windows") or ["1M"]) if str(w).upper() in _WINDOWS]
            out["windows"] = [w.upper() for w in windows] or ["1M"]
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
        return {"mode": mode if mode in ("metrics", "overlap", "both") else "both"}

    if tool == "search_financial_news":
        scope = str(src.get("scope") or "market").lower()
        direction = str(src.get("direction") or "any").lower()
        topics = [str(t).strip() for t in (src.get("topics") or []) if str(t).strip()][:8]
        return {
            "scope": scope if scope in ("holdings", "sectors", "macro", "stock", "sector", "market") else "market",
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
        if rw in ("1W", "1M", "3M", "1Y"):
            out["return_window"] = rw
        if src.get("random_sample"):
            out["random_sample"] = True
        if src.get("require_positive_1y"):
            out["require_positive_1y"] = True
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
        stock = str(src.get("stock") or "").strip()
        if stock:
            out["stock"] = stock[:80]
        return out

    return {}
