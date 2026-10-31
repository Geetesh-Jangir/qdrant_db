"""Deterministic enforcement of planner portfolio_scope vs tool calls (no question regex)."""

from __future__ import annotations

from news_rag.insight.contracts import ExecutionPlan, ToolCall

_INVESTOR_TOOL = "get_investor_portfolio"

_MODULES_BY_DATA_NEED: dict[str, list[str]] = {
    "investor_summary": ["summary"],
    "investor_holding": ["holdings"],
    "investor_sip": ["sip"],
    "investor_pnl": ["pnl_summary"],
    "investor_xirr": ["xirr"],
    "investor_hybrid": ["summary", "holdings"],
}


def _data_need_is_investor(plan: ExecutionPlan) -> bool:
    need = str(plan.data_need or "").lower().strip()
    return need.startswith("investor_")


def _scope(plan: ExecutionPlan) -> str:
    return str(plan.portfolio_scope or "none").lower().strip()


def _plan_wants_investor_book(plan: ExecutionPlan) -> bool:
    scope = _scope(plan)
    if scope == "catalog":
        return False
    if scope in ("investor", "both"):
        return True
    return _data_need_is_investor(plan)


def _modules_for_investor_plan(plan: ExecutionPlan) -> list[str]:
    need = str(plan.data_need or "").lower().strip()
    intent = str(plan.intent or "").lower().strip()
    if intent == "overview" and _data_need_is_investor(plan):
        return ["summary", "allocation", "holdings", "xirr"]
    modules = list(_MODULES_BY_DATA_NEED.get(need) or [])
    if not modules and _data_need_is_investor(plan):
        modules = ["summary"]
    return modules


def _investor_tool_args(plan: ExecutionPlan) -> dict:
    modules = _modules_for_investor_plan(plan)
    args: dict = {"modules": modules, "include_meta": True}
    if "holdings" in modules:
        args["holdings_fields"] = "standard"
        args["top_n"] = 20
        args["sort_by"] = "aum"
    if "sip" in modules:
        args["live_only"] = True
    return args


def _has_investor_tool(plan: ExecutionPlan) -> bool:
    return any(c.tool == _INVESTOR_TOOL for c in plan.tool_calls)


def ensure_investor_portfolio_tool(plan: ExecutionPlan) -> ExecutionPlan:
    """If the planner marked investor intent but omitted tool_calls, add get_investor_portfolio."""
    from news_rag.config import get_settings

    if not get_settings().portfolio_enabled:
        plan.portfolio_scope = "none"
        plan.tool_calls = [c for c in plan.tool_calls if c.tool != _INVESTOR_TOOL]
        return plan

    if _scope(plan) == "catalog":
        plan.tool_calls = [c for c in plan.tool_calls if c.tool != _INVESTOR_TOOL]
        return plan

    if not _plan_wants_investor_book(plan):
        return plan

    if _scope(plan) in ("none", ""):
        plan.portfolio_scope = "investor"

    if _has_investor_tool(plan):
        return plan

    plan.tool_calls = [
        ToolCall(
            tool=_INVESTOR_TOOL,
            arguments=_investor_tool_args(plan),
            wave=1,
            why="Planner investor data_need or portfolio_scope without tool_calls",
        ),
        *[c for c in plan.tool_calls if c.tool != _INVESTOR_TOOL],
    ]
    plan.requires_compose = True
    return plan


def enforce_portfolio_scope(plan: ExecutionPlan) -> ExecutionPlan:
    plan = ensure_investor_portfolio_tool(plan)

    if not _plan_wants_investor_book(plan):
        plan.tool_calls = [c for c in plan.tool_calls if c.tool != _INVESTOR_TOOL]

    cleaned: list[ToolCall] = []
    for call in plan.tool_calls:
        if call.tool != _INVESTOR_TOOL:
            cleaned.append(call)
            continue
        modules = list((call.arguments or {}).get("modules") or [])
        if modules:
            cleaned.append(call)
    plan.tool_calls = cleaned
    return plan
