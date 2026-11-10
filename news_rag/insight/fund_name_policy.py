"""Drop catalog fund names the user did not name — unless they asked for random/server picks."""

from __future__ import annotations

import re
from typing import Any

from news_rag.insight.contracts import ExecutionPlan


def plan_allows_server_fund_pick(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> bool:
    from news_rag.insight.brief import asks_random_fund_compare, random_fund_count
    from news_rag.insight.category_plan import plan_wants_random_same_category_pair_compare
    from news_rag.insight.plan_intent import (
        plan_wants_alternate_in_category,
        plan_wants_better_rated_in_category,
        plan_wants_unnamed_category_pair_compare,
    )

    if random_fund_count(question) > 0 or int(getattr(plan, "random_fund_count", 0) or 0) > 0:
        return True
    if asks_random_fund_compare(question):
        return True
    if plan_wants_random_same_category_pair_compare(question, plan, memory):
        return True
    if plan_wants_unnamed_category_pair_compare(question, plan, memory):
        return True
    from news_rag.fund_rating_screen import fund_type_name_spec

    if fund_type_name_spec(question):
        return True
    if plan_wants_alternate_in_category(plan) or plan_wants_better_rated_in_category(plan, question):
        return True
    for call in plan.tool_calls or []:
        if call.tool != "screen_funds_by_exposure":
            continue
        args = call.arguments or {}
        if args.get("pick_alternate") or args.get("pick_rating_better") or args.get("compare_pair"):
            return True
        if args.get("rating_screen") and str(plan.fund_pick or "").lower() in (
            "best_in_category",
            "alternate_in_category",
            "random_in_category",
        ):
            return True
    pick = str(plan.fund_pick or "").lower()
    if pick == "random_in_category" and re.search(r"\brandom\b", question or "", re.I):
        return True
    return False


def fund_authorized_for_question(
    fund_name: str,
    question: str,
    memory: dict[str, Any] | None,
) -> bool:
    from news_rag.insight.investor_subject import user_explicitly_named_scheme
    from news_rag.insight.memory.fund_context import compare_side_in_chat

    name = str(fund_name or "").strip()
    if not name:
        return False
    if user_explicitly_named_scheme(question, name):
        return True
    if _named_in_chat_turns(name, memory):
        return True
    return compare_side_in_chat(name, memory, question)


def _named_in_chat_turns(fund_name: str, memory: dict[str, Any] | None) -> bool:
    name = str(fund_name or "").strip().lower()
    if not name or not isinstance(memory, dict):
        return False
    parts: list[str] = []
    for row in memory.get("chat_turns") or []:
        if not isinstance(row, dict):
            continue
        parts.append(str(row.get("user") or ""))
        parts.append(str(row.get("assistant") or ""))
    return name in " ".join(parts).lower()


def enforce_user_authorized_funds_only(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> ExecutionPlan:
    """Remove planner-invented scheme names; keep only user/chat-authorized funds."""
    from news_rag.insight.brief import question_is_standalone_macro
    from news_rag.insight.investor_subject import question_refers_to_investor_holding

    if question_is_standalone_macro(question):
        return plan
    if plan_allows_server_fund_pick(question, plan, memory):
        return plan
    if str(plan.portfolio_scope or "").lower() in ("investor", "both"):
        if question_refers_to_investor_holding(question):
            return plan
    if any(c.tool == "get_investor_portfolio" for c in (plan.tool_calls or [])):
        if question_refers_to_investor_holding(question):
            return plan

    funds = [str(f).strip() for f in (plan.funds or []) if str(f).strip()]
    if not funds:
        return plan
    kept = [f for f in funds if fund_authorized_for_question(f, question, memory)]
    if kept != funds:
        plan.funds = kept
    return plan
