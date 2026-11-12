"""Deterministic enforcement of planner portfolio_scope vs tool calls (no question regex)."""

from __future__ import annotations

from typing import Any

from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall

_INVESTOR_TOOL = "get_investor_portfolio"

_HOLDINGS_TABLE_NEEDS = frozenset({
    "investor_holding",
    "investor_pnl",
    "investor_xirr",
    "investor_hybrid",
})

_MODULES_BY_DATA_NEED: dict[str, list[str]] = {
    "investor_summary": ["summary"],
    "investor_holding": ["holdings"],
    "investor_sip": ["sip"],
    "investor_stp": ["stp"],
    "investor_pnl": ["summary", "holdings"],
    # Holdings rows already carry xirr_pct and absolute_return_pct; summary has portfolio XIRR.
    "investor_xirr": ["summary", "holdings"],
    "investor_hybrid": ["summary", "holdings"],
    "investor_risk": ["profile_risk", "allocation", "holdings", "concentration"],
}


def investor_uses_holdings_table(plan: ExecutionPlan) -> bool:
    return str(plan.data_need or "").lower().strip() in _HOLDINGS_TABLE_NEEDS


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


def _planner_text(plan: ExecutionPlan) -> str:
    return " ".join(
        str(part or "")
        for part in (plan.planner_reading, plan.goal)
    ).lower()


def _wants_concentration(plan: ExecutionPlan) -> bool:
    """The planner already named concentration or diversification. Not a user-question matcher."""
    text = _planner_text(plan)
    return "concentration" in text or "diversif" in text


def plan_wants_concentration(plan: ExecutionPlan, question: str = "") -> bool:
    from news_rag.insight.investor_drawback import plan_wants_pure_concentration

    return plan_wants_pure_concentration(plan, question)


def _modules_for_investor_plan(plan: ExecutionPlan, question: str = "") -> list[str]:
    from news_rag.insight.investor_drawback import plan_wants_portfolio_drawback
    from news_rag.insight.portfolio_intents import modules_for

    bundled = modules_for(getattr(plan, "portfolio_intent", ""))
    if bundled:
        modules = list(bundled)
        if plan_wants_portfolio_drawback(plan, question) or plan_wants_concentration(plan, question):
            for extra in ("holdings", "allocation", "concentration"):
                if extra not in modules:
                    modules.append(extra)
        return [name for name in modules if name != "meta"]

    need = str(plan.data_need or "").lower().strip()
    intent = str(plan.intent or "").lower().strip()
    if plan_wants_portfolio_drawback(plan, question):
        return ["summary", "holdings", "allocation", "concentration"]
    if plan_wants_concentration(plan, question) or _wants_concentration(plan):
        modules = ["summary", "allocation", "concentration"]
        text = _planner_text(plan)
        if any(token in text for token in ("drawback", "weakness", "underperform", "return", "loss")):
            modules.append("holdings")
        return modules
    if intent == "overview" and _data_need_is_investor(plan):
        return ["summary", "allocation", "holdings", "xirr", "concentration"]
    modules = list(_MODULES_BY_DATA_NEED.get(need) or [])
    if str(plan.intent or "").lower() == "explain_cause" and _data_need_is_investor(plan):
        for extra in ("summary", "holdings", "allocation"):
            if extra not in modules:
                modules.append(extra)
    text = _planner_text(plan)
    if _data_need_is_investor(plan) and any(
        token in text for token in ("drawback", "weakness", "allocation", "diversif", "concentration", "volatil")
    ):
        for extra in ("summary", "holdings", "allocation"):
            if extra not in modules:
                modules.append(extra)
    if not modules and _data_need_is_investor(plan):
        modules = ["summary"]
    if "stock" in _planner_text(plan) and "concentration" not in modules:
        modules.append("concentration")
    return modules


def _investor_tool_args(plan: ExecutionPlan, question: str = "") -> dict:
    modules = _modules_for_investor_plan(plan, question)
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


_CATALOG_BOOK_TOOLS = frozenset({"get_fund_data", "get_portfolio_data", "compare_funds"})


def strip_spurious_catalog_for_investor_book(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
    question: str = "",
) -> ExecutionPlan:
    """Drop hallucinated catalog funds/tools when the plan already fetches the user's book."""
    from news_rag.insight.plan_catalog_bind import plan_targets_catalog_on_holdings, planner_requested_catalog

    if plan_targets_catalog_on_holdings(plan):
        return plan
    if planner_requested_catalog(plan):
        plan.portfolio_scope = "both" if _plan_wants_investor_book(plan) else "catalog"
        return plan
    from news_rag.insight.investor_subject import plan_targets_single_fund_measured_return

    if plan_targets_single_fund_measured_return(plan, question):
        return plan
    if not _has_investor_tool(plan) or not _plan_wants_investor_book(plan):
        return plan
    scope = _scope(plan)
    if scope == "both":
        from news_rag.insight.memory.fund_context import primary_fund_name

        if primary_fund_name(memory):
            return plan
    if not _data_need_is_investor(plan) and scope not in ("investor", ""):
        return plan

    plan.funds = []
    plan.tool_calls = [c for c in plan.tool_calls if c.tool not in _CATALOG_BOOK_TOOLS]
    if scope in ("none", ""):
        plan.portfolio_scope = "investor"
    return plan


def ensure_investor_portfolio_tool(plan: ExecutionPlan, question: str = "") -> ExecutionPlan:
    """If the planner marked investor intent but omitted tool_calls, add get_investor_portfolio."""
    from news_rag.config import get_settings
    from news_rag.insight.investor_drawback import plan_wants_portfolio_drawback

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

    if plan_wants_portfolio_drawback(plan, question):
        plan.portfolio_scope = "investor"
        plan.intent = "explain_cause"

    needed = _modules_for_investor_plan(plan, question)
    if _has_investor_tool(plan):
        for call in plan.tool_calls:
            if call.tool != _INVESTOR_TOOL:
                continue
            args = dict(call.arguments or {})
            modules = list(args.get("modules") or [])
            for name in needed:
                if name not in modules:
                    modules.append(name)
            args["modules"] = modules
            call.arguments = args
        return plan

    plan.tool_calls = [
        ToolCall(
            tool=_INVESTOR_TOOL,
            arguments=_investor_tool_args(plan, question),
            wave=1,
            why="Planner investor data_need or portfolio_scope without tool_calls",
        ),
        *[c for c in plan.tool_calls if c.tool != _INVESTOR_TOOL],
    ]
    plan.requires_compose = True
    return plan


def enforce_portfolio_scope(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
    question: str = "",
) -> ExecutionPlan:
    from news_rag.insight.investor_drawback import plan_wants_portfolio_drawback, question_signals_investor_book
    from news_rag.insight.portfolio_intents import apply_portfolio_intent

    plan = apply_portfolio_intent(plan, question)

    if question_signals_investor_book(question):
        if str(plan.portfolio_scope or "").lower().strip() in ("none", "", "catalog"):
            plan.portfolio_scope = "investor"
        if _data_need_is_investor(plan) or plan_wants_portfolio_drawback(plan, question):
            plan = strip_spurious_catalog_for_investor_book(plan, memory, question)

    plan = ensure_investor_portfolio_tool(plan, question)
    plan = strip_spurious_catalog_for_investor_book(plan, memory, question)

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

    if investor_uses_holdings_table(plan) and _has_investor_tool(plan):
        from news_rag.insight.investor_subject import question_asks_holding_metric_and_glossary

        if plan.answer_mode == AnswerMode.DATA_ONLY and not question_asks_holding_metric_and_glossary(question):
            plan.requires_compose = False
            plan.response_shape = "table"

    from news_rag.insight.portfolio_news_impact import ensure_portfolio_news_impact_plan

    plan = ensure_portfolio_news_impact_plan(plan, question)

    return plan
