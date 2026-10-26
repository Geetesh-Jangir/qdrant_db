"""Planner-authoritative path: fill entities, and keep a fund overview on the news path."""

from __future__ import annotations

import re

from news_rag.insight.contracts import AnswerMode, ExecutionPlan, QueryClass, ToolCall, Wave2Policy

_FUND_OVERVIEW_RE = re.compile(
    r"\b(?:tell me about|how is|how has|overview of|what about|update on)\b",
    re.I,
)


def finalize_planner_plan(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Fill missing funds, and attach news when this is an overview of a named fund."""
    if (plan.routed_by or "") != "planner":
        return plan
    if not plan.tool_calls:
        return plan

    needs_funds = any(
        c.tool in ("get_portfolio_data", "get_fund_data", "compare_funds") for c in plan.tool_calls
    )
    if needs_funds and not plan.funds:
        from news_rag.insight.slot_router import _extract_fund_names

        funds = _extract_fund_names(question)
        if not funds:
            from news_rag.fund_search import resolve_fund_for_query

            detail, _amb, _close = resolve_fund_for_query(question)
            if detail:
                name = str(
                    detail.get("fund_name") or detail.get("fund_short_name") or ""
                ).strip()
                if name:
                    funds = [name]
        if funds:
            plan.funds = funds
    plan = _ensure_fund_overview_news(question, plan)
    from news_rag.insight.concept_asks import apply_concept_example_to_plan

    return apply_concept_example_to_plan(question, plan)


def _ensure_fund_overview_news(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """A named-fund overview is an insight, so news has to be retrieved with the metrics."""
    if not plan.funds:
        return plan
    overview = plan.intent == "overview" or bool(_FUND_OVERVIEW_RE.search(question or ""))
    if not overview:
        return plan
    if plan.intent == "lookup" and not _FUND_OVERVIEW_RE.search(question or ""):
        return plan
    has_news = any(c.tool == "search_financial_news" for c in plan.tool_calls)
    plan.answer_mode = AnswerMode.INSIGHT_FUSION
    plan.query_class = QueryClass.STANDARD
    plan.requires_compose = True
    plan.response_shape = "sections"
    if plan.max_words < 420:
        plan.max_words = 420
    plan.presentation_notes = (
        "Connect the fund's return and its largest holdings or sectors to the news articles. "
        "The numbers alone are not the answer."
    )
    plan.wave_2_policy = Wave2Policy(trigger="always", max_calls=1)
    if not has_news:
        plan.tool_calls.append(
            ToolCall(
                tool="search_financial_news",
                arguments={
                    "scope": "all",
                    "top_n": 8,
                    "window_days": min(int(plan.window_days or 30), 30),
                },
                wave=2,
            )
        )
    return plan
