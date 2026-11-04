"""Repair and enrich planner plans without replacing planner authority."""

from __future__ import annotations

from typing import Any

from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.memory.fund_context import primary_fund_name
from news_rag.insight.planner_policy import planner_owns


def _merge_fund_names(plan: ExecutionPlan, names: list[str]) -> None:
    merged = list(plan.funds or [])
    for name in names:
        n = str(name or "").strip()
        if n and n not in merged:
            merged.append(n)
    if merged:
        plan.funds = merged


def _compare_category_slug(question: str, plan: ExecutionPlan) -> str:
    from news_rag.fund_rating_categories import match_scheme_category

    cat = str(plan.scheme_category or "").strip()
    if cat:
        return cat
    match = match_scheme_category(question or "")
    return str(match.category or "").strip() if match else ""


def seed_named_compare_funds_from_question(question: str, plan: ExecutionPlan) -> None:
    """When the user names two schemes, bind them before category compare hooks run."""
    from news_rag.insight.plan_intent import named_compare_funds_in_question, plan_wants_fund_compare

    if not plan_wants_fund_compare(plan):
        return
    if len(plan.funds or []) >= 2:
        return
    detected = named_compare_funds_in_question(question)
    if len(detected) >= 2:
        plan.funds = detected[:2]


def ensure_compare_fund_pair(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> None:
    """compare_funds needs two names — pull the pair from comparison memory when missing."""
    from news_rag.insight.plan_intent import named_compare_funds_in_question, plan_wants_fund_compare
    from news_rag.insight.memory.fund_context import comparison_fund_names

    if not plan_wants_fund_compare(plan):
        return
    if len(plan.funds or []) >= 2:
        return
    detected = named_compare_funds_in_question(question)
    if len(detected) >= 2:
        plan.funds = detected[:2]
        return
    category = _compare_category_slug(question, plan)
    pair = comparison_fund_names(memory, category=category)
    if pair:
        _merge_fund_names(plan, pair)


def finalize_fund_compare_plan(question: str, plan: ExecutionPlan) -> None:
    """Keep compare_funds as the only wave-1 tool; do not let data_need hooks replace it."""
    from news_rag.insight.plan_intent import plan_wants_fund_compare

    if not plan_wants_fund_compare(plan):
        return
    if len(plan.funds or []) >= 2:
        plan.data_need = "none"
        plan.intent = "compare"
        plan.requires_compose = True
        kept = [c for c in plan.tool_calls if c.tool == "compare_funds"]
        if not kept:
            kept = [ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)]
        plan.tool_calls = kept
        return
    if any(
        call.tool == "screen_funds_by_exposure" and (call.arguments or {}).get("compare_pair")
        for call in plan.tool_calls or []
    ):
        plan.data_need = "none"
        plan.intent = "compare"
        plan.requires_compose = True
        plan.tool_calls = [
            call
            for call in plan.tool_calls
            if call.tool == "screen_funds_by_exposure" and (call.arguments or {}).get("compare_pair")
        ]
        plan.funds = []
        return
    plan.data_need = "none"
    plan.intent = "compare"
    plan.requires_compose = True
    kept = [c for c in plan.tool_calls if c.tool == "compare_funds"]
    if not kept:
        kept = [ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)]
    plan.tool_calls = kept
    note = (
        "The user asked to compare two funds already in the conversation. "
        "Use compare_funds output only. When the question names a category (e.g. aggressive hybrid), "
        "both funds must be from that category — not a conservative hybrid from an older compare."
    )
    existing = (plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()


def apply_deictic_equity_compare_funds(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> None:
    """'Compare these equity funds' → latest pure-equity pair in chat, not hybrid or alternate picks."""
    from news_rag.insight.plan_intent import plan_wants_fund_compare
    from news_rag.insight.memory.fund_context import (
        asks_these_equity_funds,
        recent_equity_fund_pair_in_chat,
    )

    if not plan_wants_fund_compare(plan):
        return
    if not asks_these_equity_funds(question):
        return
    if _compare_category_slug(question, plan):
        return
    pair = recent_equity_fund_pair_in_chat(memory)
    if len(pair) >= 2:
        plan.funds = pair[:2]


def apply_category_scoped_compare_funds(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> None:
    """When the user names a category (e.g. both aggressive hybrids), bind funds from memory only."""
    from news_rag.insight.plan_intent import plan_wants_fund_compare
    from news_rag.insight.memory.fund_context import memory_funds_for_category

    if not plan_wants_fund_compare(plan):
        return
    category = _compare_category_slug(question, plan)
    if not category:
        return
    scoped = memory_funds_for_category(memory, category)
    if len(scoped) < 2:
        return
    plan.funds = scoped if len(scoped) == 2 else scoped[:2]
    plan.scheme_category = category


def resolve_planner_subject_refs(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> None:
    """Bind entities.funds from memory when the planner said the subject is in context."""
    from news_rag.insight.memory.fund_context import (
        comparison_fund_names,
        memory_funds_for_category,
    )
    from news_rag.insight.plan_intent import plan_wants_fund_compare

    ref = str(plan.subject_ref or "none").strip().lower()
    category = _compare_category_slug(question, plan)
    if ref == "memory_primary" and memory:
        if not plan_wants_fund_compare(plan):
            from news_rag.insight.investor_subject import resolve_user_named_fund_in_memory

            explicit = resolve_user_named_fund_in_memory(question, memory)
            if explicit:
                plan.funds = [explicit]
                plan.subject_ref = "user_named"
                return
        if plan_wants_fund_compare(plan):
            scoped = memory_funds_for_category(memory, category) if category else []
            if len(scoped) >= 2:
                plan.funds = scoped[:2]
            elif not plan.funds:
                pair = comparison_fund_names(memory, category=category)
                if len(pair) >= 2:
                    plan.funds = pair[:2]
        elif not plan.funds:
            from news_rag.insight.investor_subject import (
                question_refers_deictic_fund,
                resolve_deictic_fund_name,
            )

            if question_refers_deictic_fund(question):
                name = resolve_deictic_fund_name(question, memory)
            else:
                name = primary_fund_name(memory)
            if name:
                plan.funds = [name]
        else:
            from news_rag.insight.memory.fund_context import memory_known_fund_names

            known = {n.lower() for n in memory_known_fund_names(memory)}
            cur = str((plan.funds or [""])[0] or "").strip()
            if known and cur and cur.lower() not in known:
                name = primary_fund_name(memory)
                if name:
                    plan.funds = [name]
    elif ref == "user_named" and memory and plan.funds:
        from news_rag.insight.investor_subject import (
            reconcile_planner_invented_fund_name,
            user_explicitly_named_scheme,
        )
        from news_rag.insight.memory.fund_context import memory_known_fund_names

        cur = str((plan.funds or [""])[0] or "").strip()
        known = {n.lower() for n in memory_known_fund_names(memory)}
        if cur and known and cur.lower() not in known and not user_explicitly_named_scheme(question, cur):
            reconcile_planner_invented_fund_name(plan, memory, question)
    elif ref == "memory_stack" and memory:
        from news_rag.insight.memory.fund_context import (
            asks_these_equity_funds,
            recent_equity_fund_pair_in_chat,
        )

        if plan_wants_fund_compare(plan) and asks_these_equity_funds(question) and not category:
            equity_pair = recent_equity_fund_pair_in_chat(memory)
            if len(equity_pair) >= 2:
                plan.funds = equity_pair[:2]
                return
        pair = comparison_fund_names(memory, category=category)
        if pair:
            _merge_fund_names(plan, pair)
        else:
            stack = memory.get("entity_stack") if isinstance(memory.get("entity_stack"), list) else []
            names = [
                str(row.get("name") or "").strip()
                for row in stack
                if isinstance(row, dict) and row.get("name")
            ]
            if names:
                _merge_fund_names(plan, names[:3])
    elif ref == "list_cursor" and memory:
        cursor = memory.get("list_cursor")
        if isinstance(cursor, dict):
            names = [
                str(row.get("name") or "").strip()
                for row in (cursor.get("rows") or [])
                if isinstance(row, dict) and row.get("name")
            ]
            if names and not plan.funds:
                plan.funds = names


def _has_modules(plan: ExecutionPlan, *modules: str) -> bool:
    need = {m.lower() for m in modules}
    for call in plan.tool_calls:
        if call.tool != "get_fund_data":
            continue
        got = {str(m).lower() for m in (call.arguments or {}).get("modules") or []}
        if need <= got:
            return True
    return False


def _has_portfolio_sections(plan: ExecutionPlan, *sections: str) -> bool:
    need = {s.lower() for s in sections}
    for call in plan.tool_calls:
        if call.tool != "get_portfolio_data":
            continue
        got = {str(s).lower() for s in (call.arguments or {}).get("sections") or []}
        if need <= got:
            return True
    return False


def _prepend_tool(plan: ExecutionPlan, call: ToolCall) -> None:
    plan.tool_calls = [call, *[c for c in plan.tool_calls if c.tool != call.tool]]


def repair_data_need_tools(plan: ExecutionPlan) -> ExecutionPlan:
    """Add missing modules the planner's data_need implies; never delete planner tools."""
    from news_rag.insight.plan_intent import (
        plan_wants_alternate_in_category,
        plan_wants_compare_categories,
        plan_wants_fund_compare,
    )

    if plan_wants_compare_categories(plan) or plan_wants_alternate_in_category(plan):
        return plan
    if plan_wants_fund_compare(plan):
        return plan

    need = str(plan.data_need or "none").strip().lower()
    if need == "fund_holdings_breakdown":
        for call in plan.tool_calls or []:
            if call.tool != "get_fund_data":
                continue
            args = dict(call.arguments or {})
            modules = [str(m) for m in (args.get("modules") or [])]
            changed = False
            if "composition" not in modules:
                modules.append("composition")
                changed = True
            if changed:
                call.arguments = {**args, "modules": modules}
        if not _has_modules(plan, "risk"):
            _prepend_tool(
                plan,
                ToolCall(tool="get_fund_data", arguments={"modules": ["risk", "snapshot"]}, wave=1),
            )
        if not _has_portfolio_sections(plan, "holdings", "sectors"):
            for call in plan.tool_calls:
                if call.tool == "get_portfolio_data":
                    args = dict(call.arguments or {})
                    sections = [str(s).lower() for s in (args.get("sections") or [])]
                    if "holdings" not in sections:
                        sections.append("holdings")
                    if "sectors" not in sections:
                        sections.append("sectors")
                    args["sections"] = sections
                    args["top_n"] = max(int(args.get("top_n") or 5), 5)
                    call.arguments = args
                    break
            else:
                plan.tool_calls.append(
                    ToolCall(
                        tool="get_portfolio_data",
                        arguments={"sections": ["holdings", "sectors"], "top_n": 5},
                        wave=1,
                    )
                )
    elif need == "category_composition":
        if not _has_modules(plan, "risk"):
            _prepend_tool(
                plan,
                ToolCall(
                    tool="get_fund_data",
                    arguments={"modules": ["risk", "rating", "snapshot"]},
                    wave=1,
                ),
            )
        if not _has_portfolio_sections(plan, "holdings", "sectors"):
            plan.tool_calls.append(
                ToolCall(
                    tool="get_portfolio_data",
                    arguments={"sections": ["holdings", "sectors"], "top_n": 5},
                    wave=1,
                )
            )
    elif need == "category_performance":
        if not any(c.tool == "get_fund_data" for c in plan.tool_calls):
            plan.tool_calls = [
                ToolCall(
                    tool="get_fund_data",
                    arguments={"modules": ["snapshot", "vs_benchmark"], "windows": ["1Y", "3Y", "5Y"]},
                    wave=1,
                ),
            ]
    elif need == "rating_for_screened_list":
        if not _has_modules(plan, "rating"):
            _prepend_tool(
                plan,
                ToolCall(tool="get_fund_data", arguments={"modules": ["rating"]}, wave=1),
            )
        plan.asked_facts = list(dict.fromkeys([*(plan.asked_facts or []), "rating"]))
    return plan


def apply_planner_post_hooks(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> ExecutionPlan:
    """Planner-first: resolve subjects, targeted repairs, legacy hooks only for slot fallback."""
    from news_rag.insight.category_plan import (
        ensure_alternate_category_fund_plan,
        ensure_category_composition_plan,
        ensure_category_performance_plan,
        ensure_cross_category_compare_plan,
        ensure_fund_holdings_followup_plan,
        ensure_rating_list_funds,
        ensure_random_same_category_pair_compare_plan,
        ensure_unnamed_category_pair_compare_plan,
        ensure_better_rated_category_fund_plan,
    )
    from news_rag.insight.plan_intent import (
        plan_wants_alternate_in_category,
        plan_wants_compare_categories,
        plan_wants_fund_compare,
        reconcile_planner_intent,
    )

    reconcile_planner_intent(plan, question)
    from news_rag.insight.general_concept import apply_pure_concept_plan

    plan = apply_pure_concept_plan(plan, question)
    from news_rag.fund_risk import reroute_single_fund_risk_plan

    reroute_single_fund_risk_plan(question, plan, memory)
    from news_rag.insight.portfolio_scope import enforce_portfolio_scope

    plan = enforce_portfolio_scope(plan, memory, question)
    from news_rag.insight.investor_subject import (
        ensure_deictic_fund_period_return_plan,
        ensure_my_category_fund_investor_plan,
        enforce_deictic_and_memory_primary_fund,
        enforce_investor_holding_subject,
        ensure_catalog_tools_for_fund_news,
        reconcile_deictic_planner_fund,
        reconcile_planner_invented_fund_name,
    )

    ensure_my_category_fund_investor_plan(plan, question, memory)
    from news_rag.insight.investor_subject import ensure_all_holdings_metrics_plan, ensure_my_holding_fund_scope

    ensure_my_holding_fund_scope(plan, question, memory)
    ensure_all_holdings_metrics_plan(plan, question, memory)

    seed_named_compare_funds_from_question(question, plan)
    ensure_unnamed_category_pair_compare_plan(question, plan, memory)
    ensure_random_same_category_pair_compare_plan(question, plan, memory)
    resolve_planner_subject_refs(plan, memory, question)
    reconcile_deictic_planner_fund(plan, memory, question)
    reconcile_planner_invented_fund_name(plan, memory, question)
    enforce_investor_holding_subject(plan, memory, question)
    enforce_deictic_and_memory_primary_fund(plan, memory, question)
    from news_rag.insight.plan_catalog_bind import ensure_whole_book_catalog_scope

    ensure_whole_book_catalog_scope(plan, memory, question)
    plan = ensure_deictic_fund_period_return_plan(plan, memory, question)
    from news_rag.insight.fact_slots import merge_planner_asked_facts, tag_answer_parts

    merge_planner_asked_facts(plan)
    plan = tag_answer_parts(plan)
    from news_rag.insight.multi_fact import ensure_planner_fund_fact_modules

    ensure_planner_fund_fact_modules(question, plan)
    ensure_catalog_tools_for_fund_news(plan)
    ensure_compare_fund_pair(plan, memory, question)
    apply_category_scoped_compare_funds(question, plan, memory)
    apply_deictic_equity_compare_funds(question, plan, memory)

    from news_rag.insight.plan_intent import plan_wants_unnamed_category_pair_compare

    if plan_wants_unnamed_category_pair_compare(question, plan, memory):
        plan.requires_compose = True
        return plan

    if plan_wants_fund_compare(plan):
        finalize_fund_compare_plan(question, plan)
        return plan

    if plan_wants_compare_categories(plan):
        ensure_cross_category_compare_plan(question, plan)
        plan.intent = "compare"
        plan.requires_compose = True
        return plan

    ensure_alternate_category_fund_plan(question, plan, memory)
    ensure_better_rated_category_fund_plan(question, plan, memory)
    if plan_wants_alternate_in_category(plan):
        plan.requires_compose = True
        return plan

    repair_data_need_tools(plan)

    from news_rag.insight.fund_concentration import ensure_fund_concentration_plan

    ensure_fund_concentration_plan(question, plan)

    from news_rag.insight.plan_catalog_bind import enforce_planner_catalog_plan

    plan = enforce_planner_catalog_plan(plan, memory)

    if planner_owns(plan):
        need = str(plan.data_need or "none").lower()
        if need == "category_performance":
            ensure_category_performance_plan(question, plan, memory)
        elif need == "category_composition":
            ensure_category_composition_plan(question, plan, memory)
        elif need == "fund_holdings_breakdown":
            ensure_fund_holdings_followup_plan(question, plan, memory)
        elif need == "rating_for_screened_list":
            ensure_rating_list_funds(question, plan, memory)
        from news_rag.fund_risk import ensure_risk_tools

        ensure_risk_tools(question, plan)
        from news_rag.insight.multi_fact import ensure_planner_fund_fact_modules

        ensure_planner_fund_fact_modules(question, plan)
        ensure_fund_concentration_plan(question, plan)
        return plan

    ensure_category_performance_plan(question, plan, memory)
    ensure_cross_category_compare_plan(question, plan)
    ensure_rating_list_funds(question, plan, memory)
    from news_rag.fund_drawdown import ensure_drawdown_tools
    from news_rag.fund_rating_screen import ensure_rating_screen
    from news_rag.fund_risk import ensure_risk_tools
    from news_rag.insight.multi_fact import (
        ensure_compare_template,
        ensure_multi_fact_tools,
        ensure_screen_facts,
    )

    ensure_multi_fact_tools(question, plan)
    ensure_screen_facts(question, plan)
    ensure_compare_template(plan, question)
    ensure_drawdown_tools(question, plan)
    ensure_risk_tools(question, plan)
    ensure_rating_screen(question, plan)
    ensure_category_composition_plan(question, plan, memory)
    ensure_fund_holdings_followup_plan(question, plan, memory)
    ensure_alternate_category_fund_plan(question, plan, memory)
    return plan
