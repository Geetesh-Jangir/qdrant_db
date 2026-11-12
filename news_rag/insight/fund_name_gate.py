"""Ask for a scheme name instead of answering about a planner-invented fund."""

from __future__ import annotations

import re

from news_rag.insight.contracts import ExecutionPlan, ScopeKind

_FUND_NAME_PROMPT = (
    "Which mutual fund do you mean? Please type the full scheme name "
    "(for example, HDFC Large Cap Fund) so I can answer about that fund only.\n\n"
    "*For context only — not investment advice.*"
)

_FUND_SCOPED_TOOLS = frozenset({"get_fund_data", "get_portfolio_data", "compare_funds"})


def _compare_sides_resolvable(
    plan: ExecutionPlan,
    memory: dict | None,
    question: str,
) -> bool:
    """Planner named both sides. A holding is resolved by get_investor_portfolio, not by asking for a name."""
    from news_rag.insight.fund_name_policy import fund_authorized_for_question
    from news_rag.insight.memory.fund_context import memory_known_fund_names, primary_fund_name
    from news_rag.insight.plan_intent import plan_wants_fund_compare

    sides = list(plan.compare_sides or [])
    if not plan_wants_fund_compare(plan) or len(sides) < 2:
        return False
    known = {n.lower() for n in memory_known_fund_names(memory)}
    focus = (primary_fund_name(memory) or "").strip()
    for side in sides:
        source = str(side.get("source") or "")
        name = str(side.get("name") or "").strip()
        if source == "my_holding":
            if str(side.get("category") or "").strip():
                continue
            return False
        if source == "named" and name:
            continue
        if source == "chat_memory":
            if name and (name.lower() in known or fund_authorized_for_question(name, question, memory)):
                continue
            if focus:
                continue
            return False
        return False
    return True


def question_refers_deictic_fund_safe(question: str) -> bool:
    from news_rag.insight.investor_subject import question_refers_deictic_fund

    return question_refers_deictic_fund(question)


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
    from news_rag.insight.memory.fund_context import (
        fund_picked_from_prior_answer,
        memory_known_fund_names,
        primary_fund_name,
    )

    picked = fund_picked_from_prior_answer(question, memory)
    if picked:
        return picked

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

    from news_rag.insight.fund_name_policy import fund_authorized_for_question
    from news_rag.insight.memory.fund_context import resolve_amc_fund_from_recent_chat

    amc_pick = resolve_amc_fund_from_recent_chat(question, memory)
    if amc_pick:
        return amc_pick

    funds = [str(f).strip() for f in (plan.funds or []) if str(f).strip()]
    if len(funds) == 1:
        fund = funds[0]
        if fund_authorized_for_question(fund, question, memory):
            return fund
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
        from news_rag.insight.fund_name_policy import fund_authorized_for_question

        if all(fund_authorized_for_question(f, question, memory) for f in funds):
            return funds[0]
    return ""


_FUNDISH_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9.&'’\-]*(?:\s+[A-Za-z0-9.&'’\-]+){0,10}\s+Fund)\b"
)


def _known_names_in_text(text: str, memory: dict | None) -> list[str]:
    from news_rag.insight.memory.fund_context import memory_known_fund_names

    hits = [
        name
        for name in memory_known_fund_names(memory)
        if name and name.lower() in (text or "").lower()
    ]
    return [
        name
        for name in hits
        if not any(name.lower() != other.lower() and name.lower() in other.lower() for other in hits)
    ]


def single_fund_for_deictic(question: str, memory: dict | None) -> str:
    """One fund for 'this fund': the focused fund, or the only fund named in the last answer."""
    from news_rag.insight.investor_subject import question_refers_deictic_fund

    if not question_refers_deictic_fund(question):
        return ""
    if isinstance(memory, dict):
        frame = memory.get("frame") if isinstance(memory.get("frame"), dict) else {}
        focus = str(frame.get("last_fund_focus") or "").strip()
        if focus:
            return focus
        turns = [row for row in (memory.get("chat_turns") or []) if isinstance(row, dict)]
        if turns:
            named = _known_names_in_text(str(turns[-1].get("assistant") or ""), memory)
            if len(named) == 1:
                return named[0]
    return ""


def scrub_unknown_fund_mentions(plan: ExecutionPlan, memory: dict | None, question: str) -> ExecutionPlan:
    """Drop fund names the planner wrote that the user did not say and the chat does not know."""
    from news_rag.insight.memory.fund_context import memory_known_fund_names

    known = {name.lower() for name in memory_known_fund_names(memory) if name}
    question_l = (question or "").lower()

    def unknown(text: str) -> str:
        for match in _FUNDISH_RE.finditer(text or ""):
            low = match.group(1).strip().lower()
            if low in question_l:
                continue
            if any(low == known_name or low in known_name or known_name in low for known_name in known):
                continue
            return match.group(1).strip()
        return ""

    if unknown(str(plan.planner_reading or "")):
        plan.planner_reading = (question or "").strip()
    bad = unknown(str(plan.presentation_notes or ""))
    if bad:
        kept = [
            sentence
            for sentence in re.split(r"(?<=[.])\s+", str(plan.presentation_notes or ""))
            if bad.lower() not in sentence.lower()
        ]
        plan.presentation_notes = " ".join(kept).strip()
    return plan


def clarify_plan_if_fund_unknown(
    plan: ExecutionPlan,
    memory: dict | None,
    question: str,
) -> ExecutionPlan:
    if plan.scope_kind == ScopeKind.OUT_OF_SCOPE:
        return plan
    scrub_unknown_fund_mentions(plan, memory, question)
    picked = single_fund_for_deictic(question, memory)
    if question_refers_deictic_fund_safe(question) and not picked:
        from news_rag.insight.memory.fund_context import memory_known_fund_names

        names = memory_known_fund_names(memory)[:8]
        listed = ", ".join(names) if names else "one of the funds already in this chat"
        plan.scope_kind = ScopeKind.NEEDS_CLARIFICATION
        plan.direct_reply = f"Which fund do you mean? Recent names in this chat include {listed}."
        plan.tool_calls = []
        plan.funds = []
        plan.requires_compose = False
        plan.can_answer_directly = True
        plan.planner_reading = (question or "").strip()
        return plan
    if picked and not [str(fund).strip() for fund in (plan.funds or []) if str(fund).strip()]:
        plan.funds = [picked]
        for call in plan.tool_calls or []:
            if call.tool != "get_investor_portfolio":
                continue
            args = dict(call.arguments or {})
            modules = [str(item) for item in (args.get("modules") or [])]
            if "holdings" not in modules:
                modules.append("holdings")
            args["modules"] = modules
            args["scheme_filter"] = picked
            call.arguments = args
    if not _plan_uses_fund_scoped_tools(plan):
        if plan.scope_kind == ScopeKind.NEEDS_CLARIFICATION and (plan.direct_reply or "").strip():
            plan.tool_calls = []
            plan.funds = []
            plan.requires_compose = False
            plan.can_answer_directly = True
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
    if _compare_sides_resolvable(plan, memory, question):
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

    from news_rag.tools import asks_funds_with_sector_exposure

    if asks_funds_with_sector_exposure(question):
        plan.tool_calls = [
            call for call in (plan.tool_calls or []) if call.tool not in _FUND_SCOPED_TOOLS
        ]
        plan.funds = []
        plan.scope_kind = ScopeKind.IN_SCOPE
        plan.direct_reply = ""
        plan.can_answer_directly = False
        if re.search(r"\b(?:ai|artificial intelligence)\b", question or "", re.I):
            for call in plan.tool_calls:
                if call.tool != "screen_funds_by_exposure":
                    continue
                args = dict(call.arguments or {})
                args["sector"] = "technology"
                call.arguments = args
        return plan

    bound = _bound_fund_name(plan, memory, question)
    if bound:
        if not [str(f).strip() for f in (plan.funds or []) if str(f).strip()]:
            plan.funds = [bound]
        elif str((plan.funds or [""])[0]).strip().lower() != bound.lower():
            plan.funds = [bound]
        plan.scope_kind = ScopeKind.IN_SCOPE
        plan.direct_reply = ""
        plan.can_answer_directly = False
        return plan

    if plan.scope_kind == ScopeKind.NEEDS_CLARIFICATION and (plan.direct_reply or "").strip():
        plan.tool_calls = []
        plan.funds = []
        plan.requires_compose = False
        plan.can_answer_directly = True
        return plan

    plan.scope_kind = ScopeKind.NEEDS_CLARIFICATION
    plan.direct_reply = _FUND_NAME_PROMPT
    plan.tool_calls = []
    plan.funds = []
    plan.requires_compose = False
    plan.can_answer_directly = True
    return plan
