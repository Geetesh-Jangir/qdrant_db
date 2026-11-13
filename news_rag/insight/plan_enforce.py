"""Repair and enrich planner plans without replacing planner authority."""

from __future__ import annotations

import re
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
    reconcile_planner_compare_fund_pair(plan, memory, question)
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
    if len(pair) < 2:
        from news_rag.insight.memory.fund_context import implicit_compare_pair_from_chat

        pair = implicit_compare_pair_from_chat(memory, question)
    if pair:
        _merge_fund_names(plan, pair)


def reconcile_planner_compare_fund_pair(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> None:
    """Drop planner-invented pairs when the user meant funds already in chat."""
    from news_rag.insight.plan_intent import named_compare_funds_in_question, plan_wants_fund_compare
    from news_rag.insight.memory.fund_context import (
        compare_side_in_chat,
        implicit_compare_pair_from_chat,
        question_asks_compare_both_in_chat,
    )

    if not plan_wants_fund_compare(plan):
        return
    if (
        len(named_compare_funds_in_question(question)) >= 2
        and not question_asks_compare_both_in_chat(question)
    ):
        return
    funds = [str(f).strip() for f in (plan.funds or []) if str(f).strip()]
    rebind = question_asks_compare_both_in_chat(question)
    if len(funds) >= 2 and not rebind:
        if all(compare_side_in_chat(f, memory, question) for f in funds[:2]):
            return
        rebind = True
    elif len(funds) >= 2 and rebind:
        if all(compare_side_in_chat(f, memory, question) for f in funds[:2]):
            return
    if not rebind and len(funds) < 2:
        return
    pair = implicit_compare_pair_from_chat(memory, question)
    if not question_asks_compare_both_in_chat(question):
        pair = [n for n in pair if _scheme_written_in_chat(n, memory)]
    if len(pair) >= 2:
        plan.funds = pair[:2]
        return
    kept = [n for n in funds if _scheme_written_in_chat(n, memory)]
    if kept != funds:
        plan.funds = kept
        plan.planner_reading = (
            "Compare only schemes named in this chat or in the user's holdings."
        )


def _scheme_written_in_chat(name: str, memory: dict[str, Any] | None) -> bool:
    """True when this scheme is in the conversation text or the holdings list. Not the catalog."""
    key = str(name or "").strip().lower()
    if not key or not isinstance(memory, dict):
        return False
    parts: list[str] = []
    for row in memory.get("chat_turns") or []:
        if isinstance(row, dict):
            parts.append(str(row.get("user") or ""))
            parts.append(str(row.get("assistant") or ""))
    if key in " ".join(parts).lower():
        return True
    for row in memory.get("holdings_in_chat") or []:
        held = str(row.get("name") if isinstance(row, dict) else row or "").strip().lower()
        if held and (held == key or key in held or held in key):
            return True
    return False


def _holding_categories(plan: ExecutionPlan) -> list[str]:
    cats: list[str] = []
    for side in plan.compare_sides or []:
        if str(side.get("source") or "") != "my_holding":
            continue
        cat = str(side.get("category") or "").strip().lower()
        if cat and cat not in cats:
            cats.append(cat)
    return cats


def bind_compare_sides(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
    question: str = "",
) -> None:
    """Fill fund names from planner compare_sides. Holdings without a cached name stay for the portfolio tool."""
    if not plan.compare_sides:
        return
    from news_rag.insight.fund_name_policy import fund_authorized_for_question
    from news_rag.insight.investor_subject import investor_holding_for_category
    from news_rag.insight.memory.fund_context import memory_known_fund_names, primary_fund_name

    known = {n.lower(): n for n in memory_known_fund_names(memory)}
    names: list[str] = []
    for side in plan.compare_sides:
        source = str(side.get("source") or "")
        name = str(side.get("name") or "").strip()
        if source == "my_holding":
            row = investor_holding_for_category(memory, str(side.get("category") or ""))
            if isinstance(row, dict):
                held = str(row.get("scheme_name") or row.get("name") or "").strip()
                if held:
                    names.append(held)
                    side["name"] = held
            continue
        if source == "chat_memory":
            resolved = known.get(name.lower()) if name else ""
            if not resolved and name and fund_authorized_for_question(name, question, memory):
                resolved = name
            if not resolved:
                resolved = primary_fund_name(memory)
            if resolved:
                names.append(resolved)
                side["name"] = resolved
            continue
        if name:
            names.append(name)
    if names:
        plan.funds = list(dict.fromkeys(names))


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
        plan.funds = []
        return
    plan.data_need = "none"
    plan.intent = "compare"
    plan.requires_compose = True
    holding_cats = _holding_categories(plan)
    portfolio_side = bool(holding_cats)
    keep_tools = {"compare_funds", "get_investor_portfolio"} if portfolio_side else {"compare_funds"}
    kept = [c for c in plan.tool_calls if c.tool in keep_tools]
    if not any(c.tool == "compare_funds" for c in kept):
        kept.append(ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1))
    have = {
        str((c.arguments or {}).get("scheme_filter") or "").strip().lower()
        for c in kept
        if c.tool == "get_investor_portfolio"
    }
    for category in holding_cats:
        if category in have:
            continue
        kept.insert(
            0,
            ToolCall(
                tool="get_investor_portfolio",
                arguments={
                    "modules": ["holdings"],
                    "scheme_filter": category,
                    "holdings_fields": "minimal",
                },
                wave=1,
                why="Named category holding in the user's book, to compare with the fund in chat",
            ),
        )
    plan.tool_calls = kept
    note = (
        "The user asked to compare two funds already in the conversation. "
        "Use compare_funds output only. Bind schemes from **recent chat turns** first — "
        "older mentions and stale stack compares weigh less (see entity TTL). "
        "When the question names a category (e.g. aggressive hybrid), "
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
            compare_side_in_chat,
            recent_equity_fund_pair_in_chat,
        )

        stacked = [str(f).strip() for f in (plan.funds or []) if str(f).strip()]
        if (
            plan_wants_fund_compare(plan)
            and len(stacked) >= 2
            and all(compare_side_in_chat(f, memory, question) for f in stacked[:2])
        ):
            return
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


def _asks_ideal_portfolio_allocation(question: str) -> bool:
    q = question or ""
    if re.search(r"\bideal\s+portfolio\b", q, re.I):
        return True
    from news_rag.fund_rating_screen import asks_ideal_portfolio_shape

    return asks_ideal_portfolio_shape(q)


def _plan_asks_investor_book_allocation(plan: ExecutionPlan, question: str) -> bool:
    """Current book mix — not the illustrative balanced-portfolio screen."""
    from news_rag.insight.investor_subject import question_asks_current_book_allocation
    from news_rag.insight.portfolio_intents import normalize_portfolio_intent, shape_for

    intent = normalize_portfolio_intent(getattr(plan, "portfolio_intent", ""))
    if intent == "allocation" and shape_for(intent) == "fact":
        need = str(plan.data_need or "").lower()
        if need == "portfolio_allocation" and (
            plan.horizon_years is not None or _asks_ideal_portfolio_allocation(question)
        ):
            return False
        return True
    for call in plan.tool_calls or []:
        if call.tool != "get_investor_portfolio":
            continue
        mods = {str(m).lower() for m in (call.arguments or {}).get("modules") or []}
        if "allocation" in mods:
            return True
    if question_asks_current_book_allocation(question):
        return True
    scope = str(plan.portfolio_scope or "").lower().strip()
    if scope in ("investor", "both"):
        from news_rag.insight.investor_drawback import question_signals_investor_book

        q = (question or "").lower()
        if question_signals_investor_book(question) and re.search(r"\ballocation\b", q, re.I):
            if not re.search(r"\b(?:ideal|recommend|suggest)\s+(?:portfolio\s+)?allocation\b", q, re.I):
                return True
    return False


def _reroute_book_allocation_data_need(question: str, plan: ExecutionPlan) -> bool:
    """Planner sometimes says portfolio_allocation for the user's current mix."""
    from news_rag.insight.contracts import ScopeKind
    from news_rag.insight.portfolio_intents import apply_portfolio_intent

    if str(plan.data_need or "").lower() != "portfolio_allocation":
        return False
    if not _plan_asks_investor_book_allocation(plan, question):
        return False
    plan.data_need = "investor_summary"
    plan.portfolio_intent = "allocation"
    plan.portfolio_scope = "investor"
    plan.scope_kind = ScopeKind.IN_SCOPE
    plan.can_answer_directly = False
    plan.direct_reply = ""
    apply_portfolio_intent(plan)
    return True


def maybe_install_balanced_portfolio_screen(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> bool:
    """Illustrative mix when the planner set portfolio_allocation. Missing years asks, it does not assume."""
    if str(plan.data_need or "").lower() != "portfolio_allocation":
        return False
    if _plan_asks_investor_book_allocation(plan, question):
        _reroute_book_allocation_data_need(question, plan)
        return False
    from news_rag.fund_rating_screen import (
        asks_balanced_long_horizon_fund_menu,
        asks_ideal_portfolio_shape,
    )

    wants_screen = bool(
        plan.horizon_years is not None
        or asks_ideal_portfolio_shape(question)
        or asks_balanced_long_horizon_fund_menu(question, memory)
        or _asks_ideal_portfolio_allocation(question)
    )
    if not wants_screen:
        if any(c.tool == "get_investor_portfolio" for c in plan.tool_calls or []):
            _reroute_book_allocation_data_need(question, plan)
        return False
    from news_rag.insight.contracts import AnswerMode, ScopeKind, ToolCall
    from news_rag.insight.portfolio_allocation import allocate

    if plan.horizon_years is None:
        if any(c.tool == "get_investor_portfolio" for c in plan.tool_calls or []):
            _reroute_book_allocation_data_need(question, plan)
            return False
        plan.tool_calls = []
        plan.funds = []
        plan.requires_compose = False
        plan.can_answer_directly = True
        plan.scope_kind = ScopeKind.NEEDS_CLARIFICATION
        plan.direct_reply = (
            "How many years can you stay invested? "
            "A mix for under a year is different from one for 10 years, so I need that number before naming funds."
        )
        return True

    result = allocate(float(plan.horizon_years), plan.asset_preference, bool(plan.include_gold))
    pairs = result.pairs()
    plan.funds = []
    plan.intent = "rank"
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.requires_compose = True
    plan.direct_reply = ""
    plan.can_answer_directly = False
    plan.asked_facts = sorted(set(plan.asked_facts or []) | {"rating"})
    note = result.composer_note()
    if note not in (plan.presentation_notes or ""):
        plan.presentation_notes = f"{plan.presentation_notes} {note}".strip()
    plan.tool_calls = [
        ToolCall(
            tool="screen_funds_by_exposure",
            arguments={
                "sector": "",
                "driver": "",
                "rating_screen": True,
                "top_n": len(pairs),
                "one_per_category": True,
                "allocation_pairs": [[fund_type, category] for fund_type, category in pairs],
                "allocation_note": note,
            },
            wave=1,
            why="One top-rated fund per allocation category.",
        )
    ]
    return True


def drop_misclassified_category_composition(question: str, plan: ExecutionPlan) -> None:
    """Ideal-portfolio / generic asks are not category_composition — do not fetch example funds."""
    if str(plan.data_need or "none").lower() != "category_composition":
        return
    from news_rag.insight.category_plan import category_composition_plan_applies

    if category_composition_plan_applies(question, plan):
        return
    plan.data_need = "none"


def repair_data_need_tools(plan: ExecutionPlan, question: str = "") -> ExecutionPlan:
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
    if need == "portfolio_allocation" and _plan_asks_investor_book_allocation(plan, question):
        _reroute_book_allocation_data_need(question, plan)
        return plan
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
        from news_rag.insight.category_plan import category_composition_plan_applies

        if not category_composition_plan_applies(question, plan):
            return plan
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
        # Only for a fund already bound; without one the call has no target and would replace a valid screen.
        if plan.funds and not any(c.tool == "get_fund_data" for c in plan.tool_calls):
            _prepend_tool(
                plan,
                ToolCall(
                    tool="get_fund_data",
                    arguments={"modules": ["snapshot", "vs_benchmark"], "windows": ["1Y", "3Y", "5Y"]},
                    wave=1,
                ),
            )
    elif need == "rating_for_screened_list":
        if plan.funds and not _has_modules(plan, "rating"):
            _prepend_tool(
                plan,
                ToolCall(tool="get_fund_data", arguments={"modules": ["rating"]}, wave=1),
            )
        plan.asked_facts = list(dict.fromkeys([*(plan.asked_facts or []), "rating"]))
    return plan


def bind_shown_list_followup(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> ExecutionPlan:
    """Point 'the top 2 / the second / any two above' at that list, then the tool for the ask."""
    import re

    from news_rag.insight.memory.fund_context import funds_from_shown_list
    from news_rag.insight.multi_fact import requested_fund_facts
    from news_rag.insight.return_windows import windows_named_in_question

    names = funds_from_shown_list(question, memory)
    if not names:
        return plan
    plan.funds = list(names)
    plan.subject_ref = "list_cursor"
    plan.fund_pick = "none"
    q = question or ""
    if re.search(r"\b(?:compare|comparison|versus|vs\.?)\b", q, re.I) and len(names) >= 2:
        plan.intent = "compare"
        plan.data_need = "none"
        plan.requires_compose = True
        plan.tool_calls = [ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)]
        return plan
    facts = requested_fund_facts(q)
    windows = windows_named_in_question(q)
    calls: list[ToolCall] = []
    if "sectors" in facts or "holdings" in facts:
        sections: list[str] = []
        if "sectors" in facts:
            sections.append("sectors")
        if "holdings" in facts:
            sections.append("holdings")
        top_n = 5
        for label in sections:
            match = re.search(rf"\btop\s+(\d+)\s+{label}", q, re.I)
            if match:
                top_n = max(1, min(20, int(match.group(1))))
        calls.append(
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": sections, "top_n": top_n},
                wave=1,
            )
        )
    if windows or (facts & {"returns", "nav", "aum", "expense"}):
        arguments: dict[str, Any] = {"modules": ["snapshot"]}
        if windows:
            arguments["windows"] = windows
        calls.append(ToolCall(tool="get_fund_data", arguments=arguments, wave=1))
    if calls:
        plan.intent = "lookup"
        plan.data_need = "none"
        plan.tool_calls = calls
        return plan
    plan.tool_calls = [call for call in (plan.tool_calls or []) if call.tool != "screen_funds_by_exposure"]
    if not any(call.tool in ("get_fund_data", "get_portfolio_data", "compare_funds") for call in plan.tool_calls):
        plan.tool_calls = [ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)]
    return plan


def _keep_picked_shown_fund(question: str, plan: ExecutionPlan, memory: dict[str, Any] | None) -> None:
    """A 'pick one from above' follow-up stays on that scheme and its fund lookup."""
    from news_rag.insight.fund_name_policy import plan_allows_server_fund_pick
    from news_rag.insight.memory.fund_context import fund_picked_from_prior_answer

    if plan_allows_server_fund_pick(question, plan, memory):
        return
    picked = fund_picked_from_prior_answer(question, memory)
    if not picked:
        return
    plan.funds = [picked]
    plan.subject_ref = "user_named"
    plan.tool_calls = [
        call
        for call in (plan.tool_calls or [])
        if not (
            call.tool == "screen_funds_by_exposure" and (call.arguments or {}).get("rating_screen")
        )
    ]
    if not any(call.tool == "get_fund_data" for call in plan.tool_calls):
        plan.tool_calls = [
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot", "rating"]},
                wave=1,
            ),
            *plan.tool_calls,
        ]


def apply_planner_post_hooks(
    question: str,
    plan: ExecutionPlan,
    memory: dict[str, Any] | None,
) -> ExecutionPlan:
    """Planner-first: resolve subjects, targeted repairs, legacy hooks only for slot fallback."""
    from news_rag.insight.category_plan import (
        category_composition_plan_applies,
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
    from news_rag.insight.investor_subject import reconcile_planner_invented_fund_name
    from news_rag.insight.fund_name_policy import enforce_user_authorized_funds_only

    reconcile_planner_invented_fund_name(plan, memory, question)
    from news_rag.insight.memory.fund_context import fund_picked_from_prior_answer

    picked = fund_picked_from_prior_answer(question, memory)
    if picked:
        plan.funds = [picked]
        plan.subject_ref = "user_named"
    plan = enforce_user_authorized_funds_only(plan, memory, question)
    from news_rag.insight.general_concept import apply_pure_concept_plan

    plan = apply_pure_concept_plan(plan, question)
    from news_rag.insight.category_plan import ensure_name_fund_type_plan

    plan = ensure_name_fund_type_plan(question, plan, memory)
    from news_rag.fund_risk import reroute_single_fund_risk_plan

    reroute_single_fund_risk_plan(question, plan, memory)
    from news_rag.insight.portfolio_scope import enforce_portfolio_scope

    _reroute_book_allocation_data_need(question, plan)
    plan = enforce_portfolio_scope(plan, memory, question)
    from news_rag.insight.portfolio_news_impact import ensure_portfolio_news_impact_plan

    plan = ensure_portfolio_news_impact_plan(plan, question)
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
    from news_rag.insight.investor_subject import (
        ensure_all_holdings_metrics_plan,
        ensure_manager_fund_scope,
        ensure_my_holding_fund_scope,
    )

    ensure_my_holding_fund_scope(plan, question, memory)
    ensure_all_holdings_metrics_plan(plan, question, memory)

    bind_compare_sides(plan, memory, question)
    seed_named_compare_funds_from_question(question, plan)
    reconcile_planner_compare_fund_pair(plan, memory, question)
    ensure_unnamed_category_pair_compare_plan(question, plan, memory)
    ensure_random_same_category_pair_compare_plan(question, plan, memory)
    resolve_planner_subject_refs(plan, memory, question)
    reconcile_deictic_planner_fund(plan, memory, question)
    reconcile_planner_invented_fund_name(plan, memory, question)
    enforce_investor_holding_subject(plan, memory, question)
    enforce_deictic_and_memory_primary_fund(plan, memory, question)
    ensure_manager_fund_scope(plan, question, memory)
    from news_rag.insight.planner_policy import narrow_deictic_follow_up, planner_owns

    if not planner_owns(plan):
        plan = narrow_deictic_follow_up(question, plan, memory)
    from news_rag.insight.plan_catalog_bind import ensure_whole_book_catalog_scope

    ensure_whole_book_catalog_scope(plan, memory, question)
    plan = ensure_deictic_fund_period_return_plan(plan, memory, question)
    from news_rag.insight.investor_subject import enforce_catalog_fund_list_scope

    plan = enforce_catalog_fund_list_scope(plan, memory, question)
    from news_rag.insight.fact_slots import merge_planner_asked_facts, tag_answer_parts

    merge_planner_asked_facts(plan)
    plan = tag_answer_parts(plan)
    from news_rag.insight.multi_fact import ensure_planner_fund_fact_modules

    ensure_planner_fund_fact_modules(question, plan)
    from news_rag.insight.bullion_plan import apply_bullion_metal_scope
    from news_rag.insight.macro_scope import apply_standalone_macro_scope

    plan = apply_bullion_metal_scope(question, plan)
    plan = apply_standalone_macro_scope(question, plan)
    ensure_catalog_tools_for_fund_news(plan, question)
    plan = enforce_user_authorized_funds_only(plan, memory, question)
    ensure_compare_fund_pair(plan, memory, question)
    apply_category_scoped_compare_funds(question, plan, memory)
    apply_deictic_equity_compare_funds(question, plan, memory)

    from news_rag.insight.plan_intent import plan_wants_unnamed_category_pair_compare

    from news_rag.insight.portfolio_bind import finish_portfolio_plan_bind

    if plan_wants_unnamed_category_pair_compare(question, plan, memory):
        plan.requires_compose = True
        _keep_picked_shown_fund(question, plan, memory)
        return finish_portfolio_plan_bind(question, plan, memory)

    if plan_wants_fund_compare(plan):
        finalize_fund_compare_plan(question, plan)
        _keep_picked_shown_fund(question, plan, memory)
        return finish_portfolio_plan_bind(question, plan, memory)

    if plan_wants_compare_categories(plan):
        ensure_cross_category_compare_plan(question, plan)
        plan.intent = "compare"
        plan.requires_compose = True
        _keep_picked_shown_fund(question, plan, memory)
        return finish_portfolio_plan_bind(question, plan, memory)

    ensure_alternate_category_fund_plan(question, plan, memory)
    ensure_better_rated_category_fund_plan(question, plan, memory)
    if plan_wants_alternate_in_category(plan):
        plan.requires_compose = True
        _keep_picked_shown_fund(question, plan, memory)
        return finish_portfolio_plan_bind(question, plan, memory)

    if maybe_install_balanced_portfolio_screen(question, plan, memory):
        return finish_portfolio_plan_bind(question, plan, memory)
    drop_misclassified_category_composition(question, plan)
    repair_data_need_tools(plan, question)

    from news_rag.insight.fund_concentration import ensure_fund_concentration_plan

    ensure_fund_concentration_plan(question, plan)

    from news_rag.insight.plan_catalog_bind import enforce_planner_catalog_plan

    plan = enforce_planner_catalog_plan(plan, memory, question)

    if planner_owns(plan):
        need = str(plan.data_need or "none").lower()
        if need == "category_performance":
            ensure_category_performance_plan(question, plan, memory)
        elif need == "category_composition" and category_composition_plan_applies(question, plan):
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
        from news_rag.fund_rating_screen import ensure_quality_fund_list, ensure_rating_screen

        ensure_quality_fund_list(question, plan)
        ensure_rating_screen(question, plan, memory)
        _keep_picked_shown_fund(question, plan, memory)
        return finish_portfolio_plan_bind(question, plan, memory)

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
    ensure_rating_screen(question, plan, memory)
    ensure_category_composition_plan(question, plan, memory)
    ensure_fund_holdings_followup_plan(question, plan, memory)
    ensure_alternate_category_fund_plan(question, plan, memory)
    _keep_picked_shown_fund(question, plan, memory)
    return finish_portfolio_plan_bind(question, plan, memory)
