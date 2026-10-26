"""Normalize portfolio lookup plans from the user question (sectors vs holdings, top N)."""

from __future__ import annotations

from news_rag.insight.contracts import AnswerMode, ExecutionPlan, QueryClass, ToolCall, Wave2Policy
from news_rag.insight.top_n import top_n_from_question
from news_rag.tools import asks_fund_portfolio_holdings, portfolio_sections_for_question


def _portfolio_call(plan: ExecutionPlan) -> ToolCall | None:
    for call in plan.tool_calls:
        if call.tool == "get_portfolio_data":
            return call
    return None


def normalize_portfolio_plan_from_question(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Force minimal DATA_ONLY portfolio fetch when the user asked for scheme holdings/sectors."""
    if (plan.routed_by or "") == "planner":
        return plan
    if not asks_fund_portfolio_holdings(question):
        return plan
    sections = portfolio_sections_for_question(question)
    kind = "sectors" if sections == ["sectors"] else "holdings" if sections == ["holdings"] else "any"
    top_n = top_n_from_question(question, default=3, item=kind)
    funds = list(plan.funds or [])
    if not funds:
        from news_rag.insight.slot_router import _extract_fund_names

        funds = _extract_fund_names(question)
    goal = (
        f"Top {top_n} sectors of {', '.join(funds)}"
        if sections == ["sectors"]
        else f"Top {top_n} holdings of {', '.join(funds)}"
        if sections == ["holdings"]
        else f"Top {top_n} portfolio slice of {', '.join(funds)}"
    )
    plan.intent = "lookup"
    plan.goal = goal
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.query_class = QueryClass.SIMPLE
    plan.funds = funds
    plan.tool_calls = [
        ToolCall(
            tool="get_portfolio_data",
            arguments={"sections": sections, "top_n": top_n},
            wave=1,
        )
    ]
    plan.wave_2_policy = Wave2Policy(trigger="none")
    plan.response_shape = "table"
    plan.max_words = 100
    plan.presentation_notes = "List only what was asked. No news, NAV, returns, or extra sections."
    return plan


def portfolio_sections_from_plan(plan: ExecutionPlan) -> list[str]:
    call = _portfolio_call(plan)
    if not call:
        return []
    raw = (call.arguments or {}).get("sections") or []
    return [str(s) for s in raw if s]
