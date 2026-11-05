"""Ask for a scheme name instead of answering about a planner-invented fund."""

from __future__ import annotations

from news_rag.insight.contracts import ExecutionPlan, ScopeKind

_FUND_NAME_PROMPT = (
    "Which mutual fund do you mean? Please type the full scheme name "
    "(for example, HDFC Large Cap Fund) so I can answer about that fund only.\n\n"
    "*For context only — not investment advice.*"
)

_FUND_SCOPED_TOOLS = frozenset({"get_fund_data", "get_portfolio_data", "compare_funds"})


def _plan_uses_fund_scoped_tools(plan: ExecutionPlan) -> bool:
    for call in plan.tool_calls or []:
        if call.tool in _FUND_SCOPED_TOOLS:
            return True
    return False


def _bound_fund_name(plan: ExecutionPlan, memory: dict | None, question: str) -> str:
    from news_rag.fund_search import resolve_fund_from_question
    from news_rag.insight.investor_subject import (
        question_refers_deictic_fund,
        resolve_deictic_fund_name,
        resolve_user_named_fund_in_memory,
        user_explicitly_named_scheme,
    )
    from news_rag.insight.memory.fund_context import memory_known_fund_names, primary_fund_name

    named = resolve_user_named_fund_in_memory(question, memory)
    if named:
        return named

    detail, ambiguous, _close = resolve_fund_from_question(question)
    if detail and not ambiguous:
        name = str(
            detail.get("scheme_name") or detail.get("name") or detail.get("fund_name") or ""
        ).strip()
        if name and user_explicitly_named_scheme(question, name):
            return name

    if question_refers_deictic_fund(question):
        deictic = resolve_deictic_fund_name(question, memory)
        if deictic:
            return deictic

    funds = [str(f).strip() for f in (plan.funds or []) if str(f).strip()]
    if len(funds) == 1:
        fund = funds[0]
        if user_explicitly_named_scheme(question, fund):
            return fund
        known = {n.lower() for n in memory_known_fund_names(memory)}
        if known and fund.lower() in known:
            return fund
        if memory and primary_fund_name(memory) and primary_fund_name(memory).lower() == fund.lower():
            ref = str(plan.subject_ref or "").lower()
            if ref in ("memory_primary", "memory_stack", "list_cursor", "user_named"):
                return fund

    if len(funds) >= 2:
        if all(user_explicitly_named_scheme(question, f) for f in funds[:2]):
            return funds[0]
    return ""


def clarify_plan_if_fund_unknown(
    plan: ExecutionPlan,
    memory: dict | None,
    question: str,
) -> ExecutionPlan:
    if plan.scope_kind in (ScopeKind.OUT_OF_SCOPE, ScopeKind.NEEDS_CLARIFICATION):
        return plan
    if not _plan_uses_fund_scoped_tools(plan):
        return plan

    from news_rag.insight.general_concept import question_is_pure_general_concept
    from news_rag.insight.investor_subject import question_asks_whole_investor_portfolio
    from news_rag.insight.plan_intent import (
        plan_wants_alternate_in_category,
        plan_wants_compare_categories,
        plan_wants_fund_compare,
    )

    if question_is_pure_general_concept(question) and not _plan_uses_fund_scoped_tools(plan):
        return plan
    if plan_wants_fund_compare(plan) and len(plan.funds or []) >= 2:
        return plan
    if plan_wants_compare_categories(plan) or plan_wants_alternate_in_category(plan):
        return plan
    if question_asks_whole_investor_portfolio(question, plan):
        return plan
    from news_rag.fund_rating_screen import fund_type_name_spec
    from news_rag.insight.fund_name_policy import plan_allows_server_fund_pick

    if fund_type_name_spec(question) or plan_allows_server_fund_pick(question, plan, memory):
        return plan
    if any(
        c.tool == "screen_funds_by_exposure" and (c.arguments or {}).get("rating_screen")
        for c in (plan.tool_calls or [])
    ):
        return plan
    if str(plan.holding_scope or "") == "all_holdings":
        return plan

    if _bound_fund_name(plan, memory, question):
        return plan

    plan.scope_kind = ScopeKind.NEEDS_CLARIFICATION
    plan.direct_reply = _FUND_NAME_PROMPT
    plan.tool_calls = []
    plan.funds = []
    plan.requires_compose = False
    plan.can_answer_directly = True
    return plan
