"""Bind planner catalog tools to holdings (names + ISIN) without reading the user question."""

from __future__ import annotations

from typing import Any

from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.memory.fund_context import owned_holding_names, owned_holding_rows

_CATALOG_TOOLS = frozenset({"get_fund_data", "get_portfolio_data", "compare_funds"})
_DAYS_TO_WINDOW = {1: "1D", 7: "1W", 30: "1M", 90: "3M", 180: "6M", 365: "1Y"}


def planner_requested_catalog(plan: ExecutionPlan) -> bool:
    return any(call.tool in _CATALOG_TOOLS for call in plan.tool_calls or [])


def ensure_whole_book_catalog_scope(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> ExecutionPlan:
    """When the user asks for every scheme in holdings_in_chat, bind all_holdings before deictic hooks."""
    if _holding_scope(plan) == "all_holdings":
        return plan
    from news_rag.insight.investor_subject import question_asks_whole_investor_portfolio

    if not question_asks_whole_investor_portfolio(question, plan):
        return plan
    names = owned_holding_names(memory)
    if len(names) < 2:
        return plan
    plan.holding_scope = "all_holdings"
    plan.funds = names
    scope = str(plan.portfolio_scope or "none").lower()
    if scope in ("none", "", "investor") and (
        planner_requested_catalog(plan) or int(plan.window_days or 0) in _DAYS_TO_WINDOW
    ):
        plan.portfolio_scope = "both"
    return plan


def _holding_scope(plan: ExecutionPlan) -> str:
    return str(plan.holding_scope or "none").strip().lower()


def _funds_from_entities(plan: ExecutionPlan, memory: dict[str, Any] | None) -> list[str]:
    known = {row["name"].lower(): row["name"] for row in owned_holding_rows(memory)}
    out: list[str] = []
    for raw in plan.funds or []:
        name = str(raw or "").strip()
        if not name:
            continue
        canonical = known.get(name.lower())
        if canonical and canonical not in out:
            out.append(canonical)
        elif name not in out:
            out.append(name)
    return out


def plan_needs_investor_before_catalog(plan: ExecutionPlan, memory: dict[str, Any] | None) -> bool:
    """Wave 1 must load the book before catalog fan-out when holdings are not in memory yet."""
    if _holding_scope(plan) != "all_holdings":
        return False
    if not any(c.tool == "get_investor_portfolio" for c in plan.tool_calls or []):
        return False
    if not planner_requested_catalog(plan):
        return False
    return not owned_holding_names(memory)


def _bind_fund_list(plan: ExecutionPlan, memory: dict[str, Any] | None) -> None:
    scope = _holding_scope(plan)
    names = owned_holding_names(memory)
    if scope == "all_holdings":
        plan.funds = names if names else []
        return
    if not names:
        return
    bound = _funds_from_entities(plan, memory)
    if bound:
        plan.funds = bound
        return
    if scope == "single" and len(names) == 1:
        plan.funds = names
        return
    if len(plan.funds or []) >= 2:
        return
    count = int(plan.planner_count or 0)
    if count >= len(names) and count > 0:
        plan.funds = names
        plan.holding_scope = "all_holdings"


def _window_codes_from_plan(plan: ExecutionPlan) -> list[str]:
    codes: list[str] = []
    for call in plan.tool_calls or []:
        if call.tool != "get_fund_data":
            continue
        for raw in (call.arguments or {}).get("windows") or []:
            code = str(raw or "").strip().upper()
            if code and code not in codes:
                codes.append(code)
    if codes:
        return codes
    days = int(plan.window_days or 0)
    mapped = _DAYS_TO_WINDOW.get(days)
    return [mapped] if mapped else []


def _ensure_get_fund_data_for_holdings(plan: ExecutionPlan) -> None:
    if not plan.funds:
        return
    windows = _window_codes_from_plan(plan)
    modules = ["snapshot"]
    for call in plan.tool_calls or []:
        if call.tool != "get_fund_data":
            continue
        for mod in (call.arguments or {}).get("modules") or []:
            if str(mod) not in modules:
                modules.append(str(mod))
        return
    if not windows and str(plan.data_need or "").startswith("investor_"):
        windows = _window_codes_from_plan(plan)
    if not windows:
        return
    from news_rag.insight.return_windows import window_to_days

    window_days = window_to_days(windows[0]) or int(plan.window_days or 30)
    plan.tool_calls = [
        ToolCall(
            tool="get_fund_data",
            arguments={"modules": modules, "windows": windows, "window_days": window_days},
            wave=1,
            why="Catalog metrics for holdings (planner time + scope)",
        ),
        *(plan.tool_calls or []),
    ]


def _sector_find_from_plan(plan: ExecutionPlan) -> str:
    for call in plan.tool_calls or []:
        if call.tool != "get_portfolio_data":
            continue
        raw = str((call.arguments or {}).get("find") or "").strip()
        if raw:
            return raw
    for raw in plan.sectors or []:
        token = str(raw or "").strip().lower()
        if not token:
            continue
        if "bank" in token:
            return "banks"
        return token
    return ""


def _ensure_portfolio_data_for_holdings(plan: ExecutionPlan) -> None:
    if not plan.funds:
        return
    scope = _holding_scope(plan)
    sector_find = _sector_find_from_plan(plan)
    wants_sectors = bool(
        sector_find
        or str(plan.planner_portfolio_slice or "") in ("sectors", "both")
        or plan.sectors
    )
    if not wants_sectors:
        if scope != "all_holdings":
            return
        if not any(c.tool == "get_portfolio_data" for c in plan.tool_calls or []):
            return
    if len(plan.funds) < 2 and scope != "all_holdings":
        return
    args: dict[str, Any] = {"sections": ["sectors"], "top_n": 15}
    if sector_find:
        args["find"] = sector_find
    for call in plan.tool_calls or []:
        if call.tool != "get_portfolio_data":
            continue
        merged = dict(call.arguments or {})
        sections = [str(s).lower() for s in (merged.get("sections") or [])]
        if "sectors" not in sections:
            sections.append("sectors")
        merged["sections"] = sections
        merged["top_n"] = max(int(merged.get("top_n") or 0), 15)
        if sector_find and not merged.get("find"):
            merged["find"] = sector_find
        call.arguments = merged
        return
    plan.tool_calls = [
        *plan.tool_calls,
        ToolCall(
            tool="get_portfolio_data",
            arguments=args,
            wave=1,
            why="Sector weights for each owned fund",
        ),
    ]


def _ensure_portfolio_data_for_compare(plan: ExecutionPlan) -> None:
    if not plan.funds or len(plan.funds) < 2:
        return
    intent = str(plan.intent or "").lower()
    if intent not in ("rank", "compare", "lookup"):
        return
    slice_name = str(plan.planner_portfolio_slice or "none").lower()
    sections = ["sectors"] if slice_name in ("sectors", "both") else ["sectors"]
    for call in plan.tool_calls or []:
        if call.tool != "get_portfolio_data":
            continue
        args = dict(call.arguments or {})
        got = [str(s).lower() for s in (args.get("sections") or [])]
        for sec in sections:
            if sec not in got:
                got.append(sec)
        args["sections"] = got
        call.arguments = args
        return
    if intent == "rank" or slice_name in ("sectors", "both", "holdings"):
        plan.tool_calls = [
            *plan.tool_calls,
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": sections, "top_n": 10},
                wave=1,
                why="Sector/stock weights across owned funds",
            ),
        ]


def enforce_planner_catalog_plan(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> ExecutionPlan:
    """Align funds + catalog tools with planner holding_scope, entities, and tool_calls."""
    scope = str(plan.portfolio_scope or "none").lower()
    if planner_requested_catalog(plan) or _holding_scope(plan) == "all_holdings":
        if scope in ("none", "", "investor"):
            plan.portfolio_scope = "both"
    _bind_fund_list(plan, memory)
    if planner_requested_catalog(plan) or _holding_scope(plan) in ("all_holdings", "single"):
        _ensure_get_fund_data_for_holdings(plan)
        _ensure_portfolio_data_for_holdings(plan)
        _ensure_portfolio_data_for_compare(plan)
        plan.requires_compose = True
    elif plan.funds and int(plan.window_days or 0) in _DAYS_TO_WINDOW:
        _ensure_get_fund_data_for_holdings(plan)
        plan.portfolio_scope = "both"
        plan.requires_compose = True
    return plan


def plan_targets_catalog_on_holdings(plan: ExecutionPlan) -> bool:
    """True when catalog tools must not be stripped for an investor-book ask."""
    if planner_requested_catalog(plan):
        return True
    if _holding_scope(plan) in ("all_holdings", "single") and plan.funds:
        return True
    return bool(plan.funds and any(call.tool == "get_fund_data" for call in plan.tool_calls or []))
