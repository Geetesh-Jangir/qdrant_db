"""Bounded Two-Wave Orchestration Graph for Ask-a-Question.

        route ──► resolve ──► wave1 ──► bridge ──► wave2 ──► evidence_gate ──► compose ──► END
          │          │                    │                     ▲                 ▲
          └─► reply ◄┘                    └──────(skip)─────────┘                 │
                                                                 (DATA_ONLY fast) ┘

- Route: Slot router (deterministic, no LLM) or Planner LLM (six consolidated capabilities).
- Resolve: Canonical entity matching against fund and sector indexes without inventing IDs.
- Wave 1: Parallel capability execution bounded by deadline.
- Bridge: Strictly deterministic inspection of Wave 1 metrics; triggers Wave 2 if warranted.
- Wave 2: At most 1 (max 2) targeted news/screen capability calls.
- Evidence Gate: Joins metrics and news per canonical entity with token budgeting.
- Compose: LLM composer with EVIDENCE, memory, and numeric grounding (deterministic templates
           only for narrow cases like pillar-mark lead or missing API key).
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from news_rag.article_pool import sources_from_articles
from news_rag.config import get_settings
from news_rag.guardrails import ADVICE_NOTE
from news_rag.insight.bridge import evaluate_wave2
from news_rag.insight.capabilities import execute_wave
from news_rag.insight.contracts import (
    AnswerMode,
    EvidencePack,
    ExecutionPlan,
    QueryClass,
    RequestTelemetry,
    ScopeKind,
)
from news_rag.insight.evidence_pack import (
    build_evidence_pack,
    render_data_only_template,
)
from news_rag.insight.fund_display import (
    is_article_only_news,
    news_insight_articles,
    normalize_user_facing_text,
    stitch_display_tables_into_answer,
    strip_context_disclaimer,
    strip_news_roundup,
)
from news_rag.insight.grounding import cores_in_text, derived_cores, strip_media_attribution, strip_ungrounded_numbers
from news_rag.insight.plan import make_plan
from news_rag.insight.slot_router import slot_route
from news_rag.llm_client import (
    call_insight_llm,
    composer_model,
    llm_api_key_configured,
)
# from news_rag.output_judge import judge_answer  # Jev judge paused for ask
from news_rag.prompts import shared_system_prefix
from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

DEFAULT_OUT_OF_SCOPE = (
    "I can help with Indian mutual funds, stocks, sectors and the market. "
    "Ask me about a fund's NAV or returns, what a fund holds, how a sector is doing, "
    "or what is moving the market."
)


class GraphUnavailable(Exception):
    """Planner or routing failed completely."""


@dataclass
class GraphState:
    question: str
    date_from: str | None = None
    date_to: str | None = None
    min_impact: int | None = None
    source: str | None = None
    direction: str | None = None
    query_log: QueryLogger | None = None
    prior_context: dict[str, Any] | None = None
    telemetry: RequestTelemetry | None = None
    conversation_id: str = ""
    memory: dict[str, Any] | None = None
    memory_passed_view: dict[str, Any] | None = None
    memory_sent_composer: bool = False

    start_time: float = field(default_factory=time.time)
    deadline_ms: float = 20000.0

    plan: ExecutionPlan | None = None
    resolved_funds: list[str] = field(default_factory=list)
    unresolved_funds: list[str] = field(default_factory=list)
    sector_keys: list[str] = field(default_factory=list)

    wave1_results: list[dict[str, Any]] = field(default_factory=list)
    wave2_results: list[dict[str, Any]] = field(default_factory=list)
    evidence_pack: EvidencePack | None = None

    answer: str = ""
    reply_kind: str = "answer"  # answer | out_of_scope | clarify | not_found
    pipeline_errors: list[dict[str, str]] = field(default_factory=list)
    route_reason: str = ""
    trace: list[dict[str, Any]] = field(default_factory=list)
    judge_result: dict[str, Any] = field(default_factory=dict)

    def remaining_deadline_ms(self) -> float:
        elapsed = (time.time() - self.start_time) * 1000.0
        return max(0.0, self.deadline_ms - elapsed)


NodeFn = Callable[[GraphState], "str | None"]


@dataclass
class Node:
    name: str
    run: NodeFn
    on_error: str | None = "evidence_gate"
    uses_llm: bool = False


# ---------------------------------------------------------------------------
# Node Implementations
# ---------------------------------------------------------------------------

def _conversation_id(state: GraphState) -> str:
    raw = state.prior_context if isinstance(state.prior_context, dict) else {}
    return str(raw.get("conversation_id") or "").strip()


def _attach_conversation(state: GraphState, ctx: dict[str, Any]) -> dict[str, Any]:
    if not state.conversation_id:
        return ctx
    turn = 0
    if isinstance(state.memory, dict):
        turn = int(state.memory.get("turn_count") or 0)
    ctx["conversation_id"] = state.conversation_id
    ctx["conversation_turn"] = turn + 1
    return ctx


def _load_planner_memory(state: GraphState) -> dict[str, Any] | None:
    from news_rag.insight.memory.prompt import prompt_view
    from news_rag.insight.memory.store import get_memory

    state.conversation_id = _conversation_id(state)
    state.memory = get_memory(state.conversation_id) if state.conversation_id else None
    view = prompt_view(state.memory)
    state.memory_passed_view = view
    if state.query_log is not None:
        state.query_log.write("MEMORY_PASSED " + json.dumps(view, ensure_ascii=False))
    if not view:
        return None
    return {"conversation_id": state.conversation_id, "memory": view}


def node_route(state: GraphState) -> str | None:
    """The planner LLM is the router. The slot router is only the fallback if it fails."""
    from news_rag.fund_risk import blocked_reply

    blocked = blocked_reply(state.question or "")
    if blocked:
        state.answer = _clean_answer(blocked)
        state.reply_kind = "direct"
        state.route_reason = "blocked question"
        if state.query_log is not None:
            state.query_log.write("ROUTE blocked private_or_methodology")
        return "reply"

    from news_rag.insight.greeting import greeting_reply, identity_reply

    identified = identity_reply(state.question or "")
    if identified:
        state.answer = _clean_answer(identified)
        state.reply_kind = "direct"
        state.route_reason = "identity"
        if state.query_log is not None:
            state.query_log.write("ROUTE identity direct_reply")
        return "reply"

    greeted = greeting_reply(state.question or "")
    if greeted:
        state.answer = _clean_answer(greeted)
        state.reply_kind = "direct"
        state.route_reason = "greeting"
        if state.query_log is not None:
            state.query_log.write("ROUTE greeting direct_reply")
        return "reply"

    settings = get_settings()
    plan = make_plan(
        state.question,
        prior_context=_load_planner_memory(state),
        query_log=state.query_log,
        telemetry=state.telemetry,
    )
    if plan is None:
        threshold = float(getattr(settings, "slot_router_confidence", 0.8))
        slot_plan = slot_route(state.question, confidence_threshold=threshold)
        if slot_plan is not None:
            state.plan = slot_plan
            state.route_reason = "planner unavailable; using slot_router fallback"
            if state.query_log is not None:
                state.query_log.write("ROUTER choice=slot_router fallback=planner_failed")
        else:
            raise GraphUnavailable("Planner returned no plan")
    else:
        state.plan = plan
        state.route_reason = (
            f"planner LLM ({len(plan.tool_calls)} tools, planner_intent={plan.intent})"
        )
        if state.query_log is not None:
            state.query_log.write(
                f"ROUTER choice=planner tools={len(plan.tool_calls)} "
                f"planner_intent={plan.intent} answer_mode={plan.answer_mode.value}"
            )

    plan = state.plan
    if plan is None:
        raise GraphUnavailable("No execution plan after routing")
    from news_rag.insight.memory.update import apply_planner_refs

    apply_planner_refs(state.memory, plan)
    from news_rag.insight.plan_enforce import apply_planner_post_hooks

    plan = apply_planner_post_hooks(state.question, plan, state.memory)
    from news_rag.insight.plan_catalog_bind import enforce_planner_catalog_plan

    plan = enforce_planner_catalog_plan(plan, state.memory)
    from news_rag.insight.planner_policy import align_planned_news_execution

    plan = align_planned_news_execution(plan)
    from news_rag.insight.plan_validate import validate_plan_tools

    plan = validate_plan_tools(state.question, plan, state.memory)
    from news_rag.insight.fund_concentration import ensure_fund_concentration_plan
    from news_rag.insight.multi_fact import ensure_planner_fund_fact_modules

    plan = ensure_planner_fund_fact_modules(state.question or "", plan)
    plan = ensure_fund_concentration_plan(state.question or "", plan)
    state.plan = plan
    if state.query_log is not None:
        tools = [f"{c.tool}({c.arguments})" for c in plan.tool_calls]
        state.query_log.write(f"PLAN_AFTER_HOOKS tools={tools} funds={plan.funds}")

    # Set deadline budget based on query class
    if plan.query_class == QueryClass.SIMPLE:
        state.deadline_ms = float(getattr(settings, "request_deadline_simple_ms", 20000))
    elif plan.query_class == QueryClass.COMPLEX:
        state.deadline_ms = float(getattr(settings, "request_deadline_complex_ms", 60000))
    else:
        state.deadline_ms = float(getattr(settings, "request_deadline_standard_ms", 40000))

    if state.telemetry is not None:
        state.telemetry.routed_by = plan.routed_by
        state.telemetry.answer_mode = plan.answer_mode.value

    # Handle immediate replies
    if plan.scope_kind == ScopeKind.OUT_OF_SCOPE:
        state.reply_kind = "out_of_scope"
        state.answer = plan.direct_reply or DEFAULT_OUT_OF_SCOPE
        state.route_reason = "out of scope"
        return "reply"

    if plan.scope_kind == ScopeKind.NEEDS_CLARIFICATION:
        state.reply_kind = "clarify"
        state.answer = plan.direct_reply or (
            "Could you tell me a little more about what you would like to know?"
        )
        state.route_reason = "clarification needed"
        return "reply"

    if (plan.direct_reply or "").strip() and not plan.tool_calls:
        from news_rag.insight.computed_answers import asks_computed_illustration

        if asks_computed_illustration(state.question or ""):
            plan.direct_reply = ""
            plan.max_words = max(int(plan.max_words or 0), 420)
            plan.requires_compose = True
            plan.presentation_notes = (
                (plan.presentation_notes or "")
                + " Compute the SIP or goal illustration from the question. Do not stop at a description."
            ).strip()
            if state.query_log is not None:
                state.query_log.write("ROUTE computed_illustration skip_direct_reply=composer")
        else:
            state.reply_kind = "direct"
            state.answer = _clean_answer(plan.direct_reply)
            state.route_reason = "direct_reply (no tools)"
            if state.query_log is not None:
                state.query_log.write("ROUTE direct_reply skip=composer")
            return "reply"

    return "resolve"


def _resolve_funds(
    plan: ExecutionPlan,
    memory: dict[str, Any] | None = None,
    *,
    question: str = "",
) -> tuple[list[str], list[str]]:
    from news_rag.fund_search import detail_has_live_facts, get_fund_index
    from news_rag.insight.memory.fund_context import primary_fund_isin, primary_fund_name

    idx = get_fund_index()
    resolved: list[str] = []
    unresolved: list[str] = []

    compare_planned = (
        any(call.tool == "compare_funds" for call in (plan.tool_calls or []))
        and len(plan.funds or []) >= 2
    )
    names_to_resolve = list(plan.funds or [])[:2] if compare_planned else list(plan.funds or [])

    if not names_to_resolve and any(c.tool == "get_fund_data" for c in (plan.tool_calls or [])):
        from news_rag.insight.investor_subject import resolve_deictic_fund_name

        ctx_fund = resolve_deictic_fund_name(question, memory)
        if ctx_fund:
            plan.funds = [ctx_fund]
            names_to_resolve = [ctx_fund]

    mem_isin = primary_fund_isin(memory)
    mem_name = primary_fund_name(memory)
    single_fund = len(names_to_resolve) <= 1

    for name in names_to_resolve:
        detail = None
        mem_isin = ""
        owned_canonical = ""
        if memory:
            from news_rag.insight.memory.fund_context import isin_for_owned_holding, owned_holding_rows

            mem_isin = isin_for_owned_holding(memory, name)
            if mem_isin:
                for row in owned_holding_rows(memory):
                    if str(row.get("isin") or "").upper() == mem_isin.upper():
                        owned_canonical = str(row.get("name") or "").strip()
                        break
        if mem_isin:
            detail, _ambiguous, _close = idx.lookup_extracted_fund(isin=mem_isin, name="")
            if detail and not detail_has_live_facts(detail):
                live = idx.get_fund_detail(mem_isin)
                if live:
                    detail = live
        if single_fund and mem_isin and mem_name and (
            mem_name.lower() in name.lower() or name.lower() in mem_name.lower()
        ):
            detail, _ambiguous, _close = idx.lookup_extracted_fund(isin=mem_isin, name="")
            if detail and not detail_has_live_facts(detail):
                live = idx.get_fund_detail(mem_isin)
                if live:
                    detail = live
        if not detail:
            detail, _ambiguous, _close = idx.lookup_extracted_fund(name=name)
        if not detail and owned_canonical and owned_canonical != name:
            detail, _ambiguous, _close = idx.lookup_extracted_fund(name=owned_canonical)
        if not detail and re.search(r"\bINF[A-Z0-9]{9}\b", name or "", re.I):
            isin_m = re.search(r"\b(INF[A-Z0-9]{9})\b", name, re.I)
            if isin_m:
                detail, _ambiguous, _close = idx.lookup_extracted_fund(isin=isin_m.group(1))
        if detail:
            canonical = str(detail.get("fund_name") or detail.get("fund_short_name") or name).strip()
            if owned_canonical:
                canonical = owned_canonical
            elif mem_isin and str(name or "").strip():
                canonical = str(name).strip()
            resolved.append(canonical)
        elif owned_canonical:
            resolved.append(owned_canonical)
        elif mem_isin:
            resolved.append(str(name).strip())
        else:
            unresolved.append(name)

    if plan.random_fund_count > 0:
        want = plan.random_fund_count
        candidates = idx.sample_fund_names(want * 3, name_contains=plan.random_fund_name_contains)
        for name in candidates:
            if name not in resolved:
                resolved.append(name)
            if len(resolved) >= want:
                break

    if (
        any(call.tool == "compare_funds" for call in (plan.tool_calls or []))
        and not compare_planned
        and len(resolved) < 2
    ):
        from news_rag.fund_rating_categories import match_scheme_category
        from news_rag.insight.memory.fund_context import comparison_fund_names, memory_funds_for_category

        category = str(plan.scheme_category or "").strip()
        if not category:
            match = match_scheme_category(question or "")
            category = str(match.category or "").strip() if match else ""
        backfill = memory_funds_for_category(memory, category) if category else comparison_fund_names(memory)
        if len(backfill) < 2:
            backfill = comparison_fund_names(memory, category=category)
        for name in backfill:
            if name not in resolved:
                detail, _a, _c = idx.lookup_extracted_fund(name=name)
                if detail:
                    resolved.append(
                        str(detail.get("fund_short_name") or detail.get("fund_name") or name)
                    )
                elif name not in unresolved:
                    unresolved.append(name)
        resolved = list(dict.fromkeys(resolved))

    if str(getattr(plan, "holding_scope", "") or "").lower() == "all_holdings":
        from news_rag.insight.memory.fund_context import owned_holding_names

        owned = owned_holding_names(memory)
        if owned:
            plan.funds = owned
            return owned, []
        if any(c.tool == "get_investor_portfolio" for c in (plan.tool_calls or [])):
            plan.funds = []
            return [], []
        if plan.funds:
            return list(dict.fromkeys(plan.funds)), []
        return [], []

    return list(dict.fromkeys(resolved)), unresolved


def node_resolve(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None
    if state.query_log is not None:
        state.query_log.log_execution_plan(plan)
        state.query_log.log_memory_used(state.memory)
        state.query_log.log_slot_plan(state.question or "", plan)

    funds, unresolved = _resolve_funds(plan, state.memory, question=state.question or "")
    state.resolved_funds = funds
    state.unresolved_funds = unresolved
    if state.query_log is not None:
        state.query_log.write(f"RESOLVED funds={funds} unresolved={unresolved}")

    sector_keys: list[str] = []
    if plan.sectors:
        from news_rag.sector_fund_ranking import get_sector_fund_ranking_index
        sector_keys = get_sector_fund_ranking_index().resolve_sector_keys(plan.sectors)
    state.sector_keys = sector_keys

    # Missing fund check — do not block investor-book answers when the planner hallucinated a catalog name.
    wanted_funds = bool(plan.funds) or plan.random_fund_count > 0
    has_screen = any(call.tool == "screen_funds_by_exposure" for call in plan.tool_calls)
    has_investor_book = any(c.tool == "get_investor_portfolio" for c in (plan.tool_calls or []))
    from news_rag.insight.portfolio_scope import _data_need_is_investor

    investor_can_answer = has_investor_book and (
        _data_need_is_investor(plan)
        or str(plan.portfolio_scope or "").lower().strip() in ("investor", "")
    )
    if investor_can_answer and wanted_funds and not funds:
        plan.funds = []
        wanted_funds = False

    if wanted_funds and not funds and not plan.sectors and not plan.stocks and not plan.drivers and not has_screen:
        state.reply_kind = "not_found"
        names = ", ".join(plan.funds) or "that fund"
        state.answer = (
            f"I couldn't find a mutual fund matching {names}. "
            "Please share the full scheme name (for example the AMC and plan) and I'll look it up."
        )
        state.route_reason = "fund not found"
        return "reply"

    if not plan.tool_calls:
        state.route_reason = "no tools needed"
        return "compose"

    state.route_reason = f"funds={len(funds)} sectors={len(sector_keys)}"
    return "wave1"


def _maybe_compare_funds_after_multi_screen(state: GraphState) -> None:
    """After one screen per category, run compare_funds so EVIDENCE has aligned return columns."""
    from news_rag.insight.category_plan import asks_cross_category_compare
    from news_rag.insight.contracts import ToolCall
    from news_rag.insight.plan_intent import plan_wants_compare_categories

    q = (state.question or "").strip()
    plan = state.plan
    screen_ok = sum(
        1
        for row in state.wave1_results
        if row.get("tool") == "screen_funds_by_exposure" and row.get("ok")
    )
    wants_compare = bool(plan and plan_wants_compare_categories(plan)) or asks_cross_category_compare(q)
    compare_intent = bool(plan and str(plan.intent or "").strip().lower() == "compare")
    if not wants_compare and not (compare_intent and screen_ok >= 1):
        return
    if any(r.get("tool") == "compare_funds" and r.get("ok") for r in state.wave1_results):
        return
    names: list[str] = []
    for row in state.wave1_results:
        if row.get("tool") != "screen_funds_by_exposure" or not row.get("ok"):
            continue
        data = row.get("data") if isinstance(row.get("data"), dict) else {}
        for fund_row in data.get("rankings") or data.get("funds") or []:
            if not isinstance(fund_row, dict):
                continue
            name = str(fund_row.get("fund_name") or "").strip()
            if name and name not in names:
                names.append(name)
    if len(names) < 2:
        return
    plan = state.plan
    ctx = _attach_conversation(state, {
        "question": q,
        "window_days": plan.window_days if plan else 30,
        "fund_names": names,
        "return_window": "1M",
    })
    state.resolved_funds = names
    if plan is not None:
        plan.funds = names
        plan.requires_compose = True
    from news_rag.insight.capabilities.executor import execute_wave

    compare_rows = execute_wave(
        [ToolCall(tool="compare_funds", arguments={"compare_on": "all"}, wave=1)],
        ctx,
        fund_names=names,
        telemetry=state.telemetry,
    )
    state.wave1_results.extend(compare_rows)
    if state.query_log is not None and compare_rows:
        state.query_log.write(
            f"TOOLS wave=1 compare_followup count={len(compare_rows)} "
            f"ok={sum(1 for r in compare_rows if r.get('ok'))}"
        )


def _maybe_enrich_picked_fund_from_screen(state: GraphState) -> None:
    """After screen (pick a fund + overview), fetch snapshot/portfolio for the top match."""
    from news_rag.tools import asks_sector_overview

    q = (state.question or "").strip()
    if asks_sector_overview(q):
        return
    if not re.search(
        r"\b(?:about|overall|tell me about|how is|overview|profile)\b",
        q,
        re.I,
    ):
        return
    rankings: list[dict[str, Any]] = []
    for r in state.wave1_results:
        if r.get("tool") == "screen_funds_by_exposure" and r.get("ok"):
            data = r.get("data") if isinstance(r.get("data"), dict) else {}
            rankings = list(data.get("rankings") or data.get("funds") or [])
            break
    if not rankings:
        return
    fund = str(rankings[0].get("fund_name") or "").strip()
    if not fund:
        return
    plan = state.plan
    if plan is not None and plan.answer_mode == AnswerMode.DATA_ONLY:
        plan.answer_mode = AnswerMode.INSIGHT_FUSION
    from news_rag.insight.capabilities.executor import execute_capability
    from news_rag.insight.contracts import ToolCall

    ctx = _attach_conversation(state, {
        "question": q,
        "window_days": plan.window_days if plan else 30,
        "fund_names": [fund],
    })
    for tc in (
        ToolCall(
            tool="get_fund_data",
            arguments={"modules": ["snapshot", "attribution"], "top_n": 3},
            wave=1,
        ),
        ToolCall(
            tool="get_portfolio_data",
            arguments={"sections": ["holdings", "sectors"], "top_n": 5},
            wave=1,
        ),
    ):
        state.wave1_results.extend(
            execute_capability(
                tc,
                fund_names=[fund],
                ctx=ctx,
                telemetry=state.telemetry,
            )
        )
    state.resolved_funds = [fund]


def node_wave1(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None

    calls = plan.wave1_calls
    if not calls:
        state.route_reason = "no Wave 1 calls"
        return "bridge" if plan.answer_mode != AnswerMode.DATA_ONLY else "evidence_gate"

    screen_first = [c for c in calls if c.tool == "screen_funds_by_exposure"]
    after_screen = [c for c in calls if c.tool != "screen_funds_by_exposure"]
    sequence_screen = bool(screen_first) and any(
        c.tool in ("compare_funds", "get_fund_data", "get_portfolio_data") for c in after_screen
    )

    from news_rag.config import get_settings as _wave_settings

    _pe = _wave_settings().portfolio_enabled
    from news_rag.insight.memory.fund_context import merge_fund_isins_map

    context = _attach_conversation(state, {
        "question": state.question,
        "portfolio_enabled": _pe,
        "fund_names": state.resolved_funds,
        "sector_name": state.sector_keys[0] if state.sector_keys else (plan.sectors[0] if plan.sectors else ""),
        "sector_keys": state.sector_keys,
        "stock_name": plan.stocks[0] if plan.stocks else "",
        "drivers": [d["id"] for d in plan.drivers],
        "driver_direction": next((d.get("direction") or "" for d in plan.drivers if d.get("direction")), ""),
        "window_days": plan.window_days,
        "direction": "any",
        "top_n": 5,
    })
    context["fund_isins"] = merge_fund_isins_map(state.memory)

    deadline_ms = max(8000.0, min(state.remaining_deadline_ms() - 5000.0, 25000.0))
    t0 = time.time()
    if sequence_screen:
        screen_results = execute_wave(
            screen_first,
            context,
            fund_names=state.resolved_funds,
            telemetry=state.telemetry,
            deadline_ms=deadline_ms,
            query_log=state.query_log,
        )
        picked: list[str] = []
        for row in screen_results:
            if row.get("tool") != "screen_funds_by_exposure" or not row.get("ok"):
                continue
            data = row.get("data") if isinstance(row.get("data"), dict) else {}
            for fund_row in data.get("rankings") or data.get("funds") or []:
                name = str((fund_row or {}).get("fund_name") or "").strip()
                if name and name not in picked:
                    picked.append(name)
        if picked:
            context["fund_names"] = picked
            state.resolved_funds = picked
        rest = execute_wave(
            after_screen,
            context,
            fund_names=picked or state.resolved_funds,
            telemetry=state.telemetry,
            deadline_ms=deadline_ms,
            query_log=state.query_log,
        )
        results = screen_results + rest
    else:
        from news_rag.insight.investor_subject import holdings_rows_from_investor_tool_results
        from news_rag.insight.plan_catalog_bind import plan_needs_investor_before_catalog

        if plan_needs_investor_before_catalog(plan, state.memory):
            investor_calls = [c for c in calls if c.tool == "get_investor_portfolio"]
            catalog_calls = [c for c in calls if c.tool != "get_investor_portfolio"]
            inv_results = execute_wave(
                investor_calls,
                context,
                fund_names=state.resolved_funds,
                telemetry=state.telemetry,
                deadline_ms=deadline_ms,
                query_log=state.query_log,
            )
            holding_names = [
                str(row.get("scheme_name") or row.get("name") or "").strip()
                for row in holdings_rows_from_investor_tool_results(inv_results)
                if isinstance(row, dict)
            ]
            holding_names = list(dict.fromkeys(n for n in holding_names if n))
            holdings_rows = holdings_rows_from_investor_tool_results(inv_results)
            context["fund_isins"] = merge_fund_isins_map(state.memory, holdings_rows)
            if holding_names:
                plan.funds = holding_names
                state.resolved_funds = holding_names
                context["fund_names"] = holding_names
            rest_results = execute_wave(
                catalog_calls,
                context,
                fund_names=holding_names or state.resolved_funds,
                telemetry=state.telemetry,
                deadline_ms=deadline_ms,
                query_log=state.query_log,
            )
            results = inv_results + rest_results
        else:
            results = execute_wave(
                calls,
                context,
                fund_names=state.resolved_funds,
                telemetry=state.telemetry,
                deadline_ms=deadline_ms,
                query_log=state.query_log,
            )
    elapsed_ms = (time.time() - t0) * 1000.0

    state.wave1_results = results
    _maybe_compare_funds_after_multi_screen(state)
    from news_rag.insight.compare_evidence import maybe_run_compare_funds_for_parties

    maybe_run_compare_funds_for_parties(state)
    _maybe_enrich_picked_fund_from_screen(state)

    # Record telemetry
    if state.telemetry is not None:
        for r in results:
            state.telemetry.add_tool(
                tool=r.get("tool", ""),
                wave=1,
                ok=bool(r.get("ok")),
                duration_ms=float(r.get("elapsed_ms") or 0.0),
                error=str(r.get("error") or ""),
                fund=str(r.get("fund") or ""),
            )

    ok_count = sum(1 for r in state.wave1_results if r.get("ok"))
    state.route_reason = f"wave1: {ok_count}/{len(state.wave1_results)} ok ({elapsed_ms:.1f}ms)"

    if plan.answer_mode == AnswerMode.DATA_ONLY:
        return "evidence_gate"

    return "bridge"


def _ensure_portfolio_for_fund_news(state: GraphState) -> None:
    """A fund answer that uses news needs holdings and sectors, even when the question never says news."""
    from news_rag.tools import asks_fund_related_news

    plan = state.plan
    news_planned = bool(plan and any(call.tool == "search_financial_news" for call in plan.tool_calls))
    if not news_planned and not asks_fund_related_news(state.question or ""):
        return
    if not state.resolved_funds:
        return
    from news_rag.insight.capabilities.executor import _return_slice_covers, execute_capability
    from news_rag.insight.contracts import ToolCall

    fund = state.resolved_funds[0]
    ctx = _attach_conversation(state, {
        "question": state.question,
        "window_days": plan.window_days if plan else 30,
        "fund_names": [fund],
    })
    has_portfolio = any(
        r.get("tool") == "get_portfolio_data" and r.get("ok")
        and _return_slice_covers("get_portfolio_data", {"sections": ["holdings", "sectors"]}, r.get("data") or {})
        for r in state.wave1_results
    )
    has_metrics = any(r.get("tool") == "get_fund_data" and r.get("ok") for r in state.wave1_results)
    extra: list[ToolCall] = []
    if not has_metrics:
        extra.append(
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "top_n": 3, "windows": ["1M"]},
                wave=1,
            )
        )
    if not has_portfolio:
        extra.append(
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": ["holdings", "sectors"], "top_n": 5},
                wave=1,
            )
        )
    for tc in extra:
        state.wave1_results.extend(
            execute_capability(tc, fund_names=[fund], ctx=ctx, telemetry=state.telemetry)
        )


def node_bridge(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None

    _ensure_portfolio_for_fund_news(state)

    from news_rag.insight.investor_drawback import (
        build_drawdown_wave2_calls,
        plan_wants_portfolio_drawback,
    )

    remaining_ms = state.remaining_deadline_ms()
    if plan_wants_portfolio_drawback(plan, state.question or "") and remaining_ms >= 2500:
        drawdown_calls = build_drawdown_wave2_calls(state.wave1_results)
        if drawdown_calls:
            fund_names = [
                str(c.arguments.get("fund") or "").strip()
                for c in drawdown_calls
                if str(c.arguments.get("fund") or "").strip()
            ]
            if fund_names:
                state.resolved_funds = fund_names
            for call in drawdown_calls:
                if call not in state.plan.tool_calls:
                    state.plan.tool_calls.append(call)
            state.route_reason = f"bridge: drawdown for {len(drawdown_calls)} holding(s)"
            return "wave2"

    remaining_ms = state.remaining_deadline_ms()
    wave2_calls = evaluate_wave2(
        plan,
        state.wave1_results,
        deadline_remaining_ms=remaining_ms,
        question=state.question or "",
    )

    if wave2_calls and remaining_ms >= 2000.0:
        state.route_reason = f"bridge triggered {len(wave2_calls)} Wave 2 call(s)"
        state.plan.tool_calls.extend([c for c in wave2_calls if c not in state.plan.tool_calls])
        return "wave2"

    state.route_reason = "bridge: skipping Wave 2"
    return "evidence_gate"


def node_wave2(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None

    calls = plan.wave2_calls
    if not calls:
        state.route_reason = "no Wave 2 calls"
        return "evidence_gate"

    from news_rag.config import get_settings as _w2_settings

    context = _attach_conversation(state, {
        "question": state.question,
        "portfolio_enabled": _w2_settings().portfolio_enabled,
        "fund_names": state.resolved_funds,
        "sector_name": state.sector_keys[0] if state.sector_keys else "",
        "sector_keys": state.sector_keys,
        "window_days": min(plan.window_days, 30),
        "direction": "any",
        "top_n": 3,
        "wave1_results": state.wave1_results,
        "query_log": state.query_log,
    })

    deadline_ms = max(8000.0, min(state.remaining_deadline_ms() - 4000.0, 25000.0))
    t0 = time.time()
    results = execute_wave(
        calls,
        context,
        fund_names=state.resolved_funds,
        telemetry=state.telemetry,
        deadline_ms=deadline_ms,
        query_log=state.query_log,
    )
    elapsed_ms = (time.time() - t0) * 1000.0

    state.wave2_results = results

    if state.telemetry is not None:
        for r in results:
            state.telemetry.add_tool(
                tool=r.get("tool", ""),
                wave=2,
                ok=bool(r.get("ok")),
                duration_ms=float(r.get("elapsed_ms") or 0.0),
                error=str(r.get("error") or ""),
            )

    ok_count = sum(1 for r in results if r.get("ok"))
    state.route_reason = f"wave2: {ok_count}/{len(results)} ok ({elapsed_ms:.1f}ms)"
    return "evidence_gate"


def node_evidence_gate(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None

    if state.query_log is not None:
        state.query_log.log_tool_results(1, state.wave1_results)
        if state.wave2_results:
            state.query_log.log_tool_results(2, state.wave2_results)
        state.query_log.log_tool_facts(state.question or "", [*state.wave1_results, *state.wave2_results], state.plan)
        state.query_log.log_error_summary([*state.wave1_results, *state.wave2_results], state.question or "", state.plan)

    from news_rag.insight.capabilities.executor import refetch_partial_fund_tools

    refetch_partial_fund_tools(
        plan,
        state.wave1_results,
        _attach_conversation(state, {
            "question": state.question or "",
            "fund_names": state.resolved_funds,
        }),
    )

    from news_rag.insight.investor_subject import (
        apply_investor_category_fund_to_plan,
        refetch_category_holdings_if_missing,
    )

    ctx = _attach_conversation(state, {
        "question": state.question or "",
        "fund_names": state.resolved_funds,
    })
    state.wave1_results = refetch_category_holdings_if_missing(
        state.question or "",
        plan,
        state.wave1_results,
        ctx,
    )

    apply_investor_category_fund_to_plan(
        plan,
        state.question or "",
        state.memory,
        state.wave1_results,
    )
    if plan.funds:
        state.resolved_funds = list(plan.funds)

    pack = build_evidence_pack(
        plan,
        state.wave1_results,
        state.wave2_results,
        token_budget=10000,
        question=state.question or "",
    )
    from news_rag.insight.portfolio_news_impact import (
        build_portfolio_news_impact_dossier,
        question_is_portfolio_news_impact,
    )

    if question_is_portfolio_news_impact(state.question or "", plan):
        dossier = build_portfolio_news_impact_dossier(
            question=state.question or "",
            plan=plan,
            data_pack=pack.data_pack,
            news_grouped=pack.news_grouped,
            query_log=state.query_log,
        )
        if dossier:
            pack.data_pack["portfolio_news_impact"] = dossier
            pack.data_pack.pop("screen", None)
    state.evidence_pack = pack
    state.route_reason = (
        f"pack: {len(pack.rows)} entity rows, news={bool(pack.news_grouped)}, "
        f"missing={len(pack.missing)}"
    )
    return "compose"


def _drop_scheme_is_the_whole_book(text: str) -> str:
    """Drop the line that treats 'you only hold N funds' as concentration."""
    kept: list[str] = []
    for line in (text or "").splitlines():
        low = line.lower()
        if "whole portfolio" in low:
            continue
        if "top 5" in low and ("100%" in low or "only" in low or "because you hold" in low):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


COMPOSE_SYSTEM = """ROLE: COMPOSER (user-facing markdown only)
You receive QUESTION, WHAT THE USER WANTS (goal, answer_mode, style, max_words), and EVIDENCE (metrics + optional news).

VOICE: Speak directly to the reader as **you** / **your**. Use a warm, plain tone — like a helpful colleague, not a formal report. Do not call the reader "the investor" or "investors".

CORE RULES:
0. **Subject line.** When WHAT THE USER WANTS includes `answer_subject`, the **first line** must be `## {answer_subject}` (exact scheme name from EVIDENCE). Then answer the question about **that** scheme only. Do not lead with a different fund from an old chat compare or screen.
0a. **Whole investor book.** When `investor_portfolio_overview` is true, open with `## Your portfolio` (never a single scheme name as the title). Summarize total value, invested, gain, and portfolio XIRR first. For two or more schemes in EVIDENCE, use one markdown table for scheme-level figures (scheme, category, current value, invested, gain, absolute return, XIRR, RS label) and, when allocation.categoryShare is present, a second table for category weights. Put a **blank line** before each table and keep section headings as `### Your holdings` and `### Allocation by category`. Do not list the same scheme figures again as bullets if they are in a table. The server may append underlying concentration tables; do not duplicate those blocks.
0c. **Portfolio news impact.** When EVIDENCE includes `portfolio_news_impact`, explain how the news affects **the user's book** only — not catalog screen funds. Use `## How this affects your portfolio`, then `### What the news says` and `### What stands out` from `sector_impact_analysis` / `fund_sector_exposure`. Do **not** add `### Top holdings` or `### Top sectors`; the server appends **Sectors affected by the news** and **Your funds affected** tables. Do not cite index/ETF screen picks unless they are in the user's holdings. Direct = positive `portfolio_weight_pct`; indirect = affected but ~0% in the book.
0b. **Concept + data:** When WHAT THE USER WANTS includes `concept_brief`, explain that concept first (1–3 sentences), then use EVIDENCE for the example fund/scheme. Do not skip the concept or invent fund names.
1. **Match the question.** Read the whole question. You write the answer. A lookup is a short table or a few lines. An explanation can be longer. A calculation with empty EVIDENCE is still an answer: show the figures and the assumption. Do not pad a simple question into an essay. Do not dump the whole snapshot. One named figure and nothing else asked is one sentence: the fund name and that figure only. If the question has more than one part, answer every part: the figure from EVIDENCE, then the meaning, then whether a low or high value is generally better, if they asked. A misspelled or awkward wording still means the intended ask. On a phone: one short lead sentence, then a 2-column table or at most five bullets. Paragraphs are at most two sentences. Do not use a table wider than three columns. Do not repeat a heading. Answer the asked facts first. Add at most one extra line the reader needs. A part whose source is llm (a definition or a full form) is answered from knowledge with no extra numbers.
2. **Returns in prose:** Compare a fund with its benchmark only when a benchmark return is present, and with the category average only when that average is present. If neither is present, do not write a comparison and do not say that the comparison is missing or cannot be stated. If only one side is present, compare only that side. Cite the exact gap in percentage points. Do not say "about" when the gap is computable. Do not fill a missing side with a hyphen or a guess. Do not write a returns bullet list. When several funds are compared, put the returns in the table you build. Do not say how much of the move is unexplained, or that named holdings fail to explain the fund's return. When the user asked for several of expense ratio, exit load, and AUM, state each one they asked for. Do not add the ones they did not ask for. Do not mention a direct-plan expense ratio unless that is the field in the snapshot. Do not say these figures are unavailable when they are present. When NEWS is present and the user did not ask for a returns list, do not walk 1-month, 3-month, 1-year, 3-year, and 5-year one after another. Use a return only inside a point that also uses the news.
3. **Tables and prose.** Server-built markdown tables may be appended after your text. Do **not** paste markdown tables yourself when DISPLAY is present — write the insight in prose first. When you write a markdown table, put a **blank line** between the intro sentence and the first `|` row so the table renders as one block. When TABLE_SUMMARIES is in EVIDENCE, the opening 2–4 sentences must state the fund name, **equity/cash (and debt if any) weights**, **large/mid/small cap split**, the **largest sector weights**, **named top holdings with weights**, and the **top holdings sum** when present — exact percentages from TABLE_SUMMARIES. Never leave empty **Asset mix** or **Market cap mix** labels. When the evidence has several funds or several figures (and no DISPLAY takeover), you may build one markdown table with columns from the question. Do not repeat the same numbers in a paragraph and a table you wrote.
4. **Missing measured data:** Use **-** only for a figure that should have come from EVIDENCE and is absent. Never replace a number the user stated, or a number you calculated, with a hyphen.
5. **What stands out.** When NEWS or insight_links are in EVIDENCE, that is the answer. Open with `### What stands out` **after** the `## answer_subject` heading when present. One sentence on how recent news touches **that fund's** largest weighted exposure (from insight_links for the same fund as answer_subject). Then one block per insight_links row for **that fund only**. Do not map news to a peer fund's holdings because a compare happened earlier in chat. After each news block, when snapshot or investor holding returns exist for answer_subject, add one short line on how the fund's recent return (label the horizon) relates to that theme — blend data with news, do not paste a returns table here. A holding block is a bold line `**Name · 6.46% · Telecom - Services**` copied from that row's name, weight_pct, and sector. A sector block is `**Name · 8.45% of the fund**`. A macro block is `**Macro · name**` with no invented weight. After the bold line, write the facts in that row's points: the event and the figure the article reported. Use every point for that row. The last sentence is one of those facts. Do not add a closer about how the fund may behave, whether a forecast is confirmed, or that the news matters more to the stock than to the fund. Cover holdings, sectors, and macro when those rows exist. Do not leave a weight blank. Do not write that a name is outside the top five, that a weight is missing, or that the effect cannot be measured. Do not paste a headline or a publisher. Do not add `### Recent news`, `### Fund basics`, or `### Recent performance context`. Do not add a holdings or sectors table unless the question asked for that list. If NEWS is absent, do not write this section.
6. **Numbers and knowledge:** If EVIDENCE has measured figures, those figures must match EVIDENCE. Investor portfolio amounts are already in rupees. Write ₹65,405 or ₹12,220.54 — **not** lakh, crore, or “₹12,221 lakh”. Do not rescale small book amounts into lakh. When concentration.top_holdings and concentration.sectors are present, name each top holding with its weight and each top sector with its weight. Do not write "approx" or "approximate". Do not say the top schemes hold the whole portfolio, or that the top 5 schemes are 100%, just because the book has only a few funds. Concentration is the underlying holdings and sectors, not a restatement that every scheme you own adds up to 100%. If EVIDENCE is empty, answer the question anyway. Definitions, explanations, and a standard educational read are yours to write. You may say what a term means and whether a lower or higher figure is generally better for you (for example a lower expense ratio usually leaves more of the return with you). That is not a buy or sell. Stay with mutual funds, stocks, and markets. If an input is missing, name one assumption and compute with it. A small calculation table is allowed when the user asked for a plan or a projection. Do not recommend a product.
7. **Horizon on every measured percent.** Each price or return row has `horizon` (1D, 1W, 1M, 3M, 6M, 1Y, or a day count such as 14D). WHAT THE USER WANTS also has `measured_window`. Write that code on the figure: Nifty **+0.7% (1W)**. If one figure is 1W and another is 1M, label both. Do not call a 1W or 1M change "the latest session", "today", or "right now".
8. **No invented levels.** A macro row is a percent change, not a Brent price, a rupee level, or an Indian bond yield. Do not print a level the row does not contain, and do not leave a blank where a number should be. A level or a percent that appears only in a news summary is what that article reported, not the measured move. Gold figures from metals_spot are 24K gold in INR per 10 grams. State the horizon on every gold percent in prose. When a gold return has approx true, say it uses the nearest month-end price. Do **not** add a markdown table for gold windows — the server appends one with **then** and **now** prices from `returns.from_price` / `returns.to_price`. Never quote a silver price or a silver return. A silver answer comes from the articles only, and say it is based on news.

9. Never mention: DATA, NEWS, EVIDENCE, DISPLAY, tool, pipeline, JSON, yfinance, proxy.
10. The markdown table in the answer is the table the user reads. Do not add a second copy of the same numbers.
11. **Shape.** A RupeeStop rating lead is placed above your answer. Do not repeat that score or those pillar marks. Bold only the label, a pillar mark, and the figure the user asked for. One block per part of the question, in that order. A table only when there are several funds or several figures.
12. **End summary.** Write `### Summary` only when WHAT THE USER WANTS has `end_summary` true. Two or three sentences: the overall read, not a repeat of every number. When `end_summary` is false, do not add a summary.
13. Answer only what the question asked. If the user asked for a figure and it is not in EVIDENCE, write one friendly sentence: "We can't get that data right now." If they did not ask for it, leave it out. A rating list names the fund, the label, and the score. When WHAT THE USER WANTS has `fund_pick` **alternate_in_category** and the screen shows **one** fund, that fund **is** the answer — name it with RS score, label, and key returns. Do **not** say a second fund is unavailable or that you need another row to compare; the user asked for one additional scheme, not a side-by-side table of two. When pillar scores are present, write each as score out of the max in EVIDENCE for that pillar; max marks differ by fund type. For a general question about pillar maximums with no fund in EVIDENCE, say each pillar's cap depends on fund type and category, and do not invent fixed numbers like 40/25/25/10 for every scheme. Do not mention a return unless the question asked for one. When one fund is the period performer and another is the rated fund, name both. Say the performer's return over that period is the better return. Say the rated fund is the better rating only when its score is higher. Do not say the rated fund won that period when its return is lower. Do not open with "I can't recommend." Do not tell the reader to buy.
14. **Managers.** Write only the managers present in EVIDENCE. Current managers are the default. Do not mention former managers unless they are in EVIDENCE.
15. **Risk.** The SEBI riskometer is how risky the fund is.
16. **Which tables to append.** WHAT THE USER WANTS lists `tables_in_answer` (candidate keys). TABLE_SUMMARIES.table_quality marks `complete`, `partial`, or `empty`. End your reply with exactly one HTML comment on its own line: `<!-- TABLES_APPEND: default -->` to append all candidates, `<!-- TABLES_APPEND: none -->` when tables would mislead, or `<!-- TABLES_APPEND: key1,key2 -->` for a subset (only keys from tables_in_answer). Omit partial or empty tables unless the user explicitly asked for that slice. A pillar mark, including the risk pillar, is a score from internal calculations. A lower risk-pillar mark does not mean the fund is less risky, and a higher mark does not mean it is more risky. Do not turn a pillar mark into a percentage of its maximum. When you add mid-cap and small-cap weights, write that sum. Do not write "approx" without the number. When drawdown episodes are present, write them once under the heading `### Maximum drawdown across periods`, one line per period. Do not list those same falls again in the opening or in a second Drawdown section. Do not say drawdown is missing, not recorded, or not available. Do not mention a return period or write "see the table below" unless that return is in EVIDENCE and the answer contains the table. When the user asks whether risk is lower or higher than before and EVIDENCE has no earlier riskometer reading, use exactly one sentence: "We can't get that data right now." Then report the current riskometer, pillar, mix, and drawdown. Do not write about snapshots, trends, or data that cannot show a change.
"""

COMPOSE_SYSTEM_PRECISE = """ROLE: COMPOSER — one specific figure
The user asked for one thing: a NAV, an AUM, one return window, a benchmark, or a short definition.

RULES:
1. One sentence. Name the fund and the figure they asked for. Nothing else.
2. A 1-month return is only the 1-month figure. Do not add 1-year, 3-year, or 5-year returns.
3. Use the number in EVIDENCE. If it is missing, say so in that same sentence.
4. No heading, no bullets, no other facts, no investing comment.
5. Do not mention tools, EVIDENCE, or the pipeline.
"""

COMPOSE_SYSTEM_FACTS = """ROLE: COMPOSER — one note for you
FACTS has every figure the user asked for.

RULES:
1. Cover every topic in FACTS. Leave a blank line between topics so the note is easy to read.
2. Write plain sentences. For sectors, use one bullet per sector and keep its weight.
3. Use only figures written in FACTS. Do not invent a total, a cause, or a forecast.
4. Do not use a table. Do not repeat a figure you already stated. Do not add expense ratio, AUM, or exit load unless FACTS includes them.
5. Do not give a buy or sell view. Do not mention FACTS, tools, or the pipeline.
"""

COMPOSE_SYSTEM_NEWS = """ROLE: COMPOSER — insight from the articles
The user asked what the news means. ARTICLES are the only source.

RULES:
1. Write a short opening and two or three bullets. Say what happened and what it means for the subject. Merge articles about the same event into one point.
2. Use only facts written in ARTICLES. Do not invent a price, a cause, or a level.
3. Do not name a publisher, a website, or a reporter. Do not paste headlines. Every sentence is complete. Never end with an ellipsis.
4. Leave out an article that is not about the subject of the question.
5. Never mention ARTICLES, tools, or the pipeline.
"""


def _clean_answer(text: str) -> str:
    text = normalize_user_facing_text(re.sub(r"```(?:json|markdown)?", "", text or "").strip())
    return strip_context_disclaimer(text)


def _answer_stream_chunks(answer: str) -> list[str]:
    text = answer or ""
    if re.search(r"(?m)^\s*\|", text) or "**" in text:
        lines = text.splitlines(keepends=True)
        return lines if lines else [text]
    words = text.split(" ")
    chunk_size = 6
    chunks: list[str] = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i : i + chunk_size])
        if i + chunk_size < len(words):
            chunk += " "
        chunks.append(chunk)
    return chunks or [text]


def _wants_end_summary(plan: ExecutionPlan, question: str) -> bool:
    """An analysis gets a short close. A single fact does not."""
    from news_rag.insight.multi_fact import asks_one_figure

    if asks_one_figure(question) and len(plan.sub_queries or []) < 2:
        return False
    if len(plan.sub_queries or []) > 1:
        return plan.intent in ("overview", "explain_cause", "compare")
    if plan.intent in ("overview", "explain_cause", "compare"):
        return True
    return bool(re.search(r"\bwhy\b|\brisk analysis\b|\bhow risky\b", question or "", re.I))


def _plan_fetches_manager_roster(plan: ExecutionPlan | None) -> bool:
    if plan is None:
        return False
    for call in plan.tool_calls or []:
        if call.tool != "get_fund_data":
            continue
        mods = {str(m).lower() for m in (call.arguments or {}).get("modules") or []}
        if "managers" in mods:
            return True
    return False


def _rating_lead_for_pack(pack: EvidencePack | None, question: str) -> str:
    from news_rag.fund_risk import rating_lead
    from news_rag.insight.manager_view import asks_manager_roster

    if pack is None:
        return ""
    if asks_manager_roster(question):
        return ""
    fund_keys = [k for k in (pack.data_pack or {}) if str(k).startswith("fund:")]
    if len(fund_keys) > 1:
        return ""
    screen = (pack.data_pack or {}).get("screen")
    if isinstance(screen, dict):
        rows = screen.get("rankings") or screen.get("funds") or []
        if isinstance(rows, list) and len(rows) > 1:
            return ""
    for value in (pack.data_pack or {}).values():
        if isinstance(value, dict) and isinstance(value.get("rs_rating"), dict):
            return rating_lead(value["rs_rating"], question)
    return ""


def node_compose(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None
    pack = state.evidence_pack

    from news_rag.fund_risk import asks_pillar_mark, asks_sebi_riskometer, rating_lead

    if plan.answer_mode == AnswerMode.DATA_ONLY and pack and asks_pillar_mark(state.question or ""):
        from news_rag.fund_risk import pillar_focus, render_pillar_marks_table

        fund = next(
            (value for key, value in pack.data_pack.items() if str(key).startswith("fund:") and isinstance(value, dict)),
            None,
        )
        if isinstance(fund, dict) and isinstance(fund.get("rs_rating"), dict):
            body = rating_lead(fund["rs_rating"], state.question or "")
            if body:
                if not pillar_focus(state.question or ""):
                    table = render_pillar_marks_table(fund["rs_rating"])
                    if table:
                        body = f"{body}\n\n{table}"
                name = str(fund.get("fund_name") or (plan.funds[0] if plan.funds else "")).strip()
                state.answer = _clean_answer(f"### {name}\n\n{body}" if name else body)
                state.route_reason = "pillar rating template"
                return None

    if (
        plan.answer_mode == AnswerMode.DATA_ONLY
        and pack
        and asks_sebi_riskometer(state.question or "")
    ):
        fund = next(
            (value for key, value in pack.data_pack.items() if str(key).startswith("fund:") and isinstance(value, dict)),
            None,
        )
        if isinstance(fund, dict):
            from news_rag.insight.evidence_pack import _risk_body

            body = _risk_body(fund)
            if body:
                name = str(fund.get("fund_name") or (plan.funds[0] if plan.funds else "")).strip()
                text = f"### {name}\n\n{body}" if name else body
                state.answer = _clean_answer(text)
                state.route_reason = "SEBI riskometer template"
                return None

    if pack is not None:
        from news_rag.insight.investor_drawback import (
            plan_wants_portfolio_drawback,
            render_portfolio_drawback_answer,
        )

        if plan_wants_portfolio_drawback(plan, state.question or ""):
            drawback_answer = render_portfolio_drawback_answer(pack, plan, state.question or "")
            if drawback_answer:
                state.answer = _clean_answer(drawback_answer)
                state.route_reason = "portfolio drawback template"
                return None

        from news_rag.insight.evidence_pack import render_fund_concentration_answer

        fund_concentration = render_fund_concentration_answer(
            pack, plan, state.question or ""
        )
        if fund_concentration:
            state.answer = _clean_answer(fund_concentration)
            state.route_reason = "fund concentration template"
            return None

        from news_rag.insight.evidence_pack import render_investor_concentration_answer

        concentration_answer = render_investor_concentration_answer(
            pack, plan, state.question or ""
        )
        if concentration_answer:
            state.answer = _clean_answer(concentration_answer)
            state.route_reason = "portfolio concentration template"
            return None

    template_answer = None
    if (
        plan.answer_mode == AnswerMode.DATA_ONLY
        and pack is not None
        and not (plan.concept_brief or "").strip()
    ):
        saved_compose = plan.requires_compose
        plan.requires_compose = False
        try:
            template_answer = render_data_only_template(pack, plan)
        finally:
            plan.requires_compose = saved_compose

    # DATA_ONLY is a fetch choice, not a finished dump. The composer writes the answer.
    settings = get_settings()
    if not llm_api_key_configured(settings):
        if template_answer:
            state.answer = _clean_answer(template_answer)
            state.route_reason = "DATA_ONLY template (no composer key)"
            return None
        if pack:
            state.answer = _clean_answer("Here is the requested information:\n\n" + json.dumps(pack.data_pack, indent=2))
            return None
        raise GraphUnavailable("No LLM key configured for composer")

    fact_brief = ""
    use_facts_compose = False
    if pack and len(plan.asked_facts or []) >= 2:
        from news_rag.insight.evidence_pack import investor_fact_brief

        fact_brief = investor_fact_brief(pack.data_pack, plan.asked_facts)
        # INSIGHT_FUSION overviews need full EVIDENCE (holdings, news, snapshot), not FACTS-only mode.
        use_facts_compose = bool(fact_brief) and plan.answer_mode == AnswerMode.DATA_ONLY
    evidence_dict = (
        {"FACTS": fact_brief}
        if use_facts_compose
        else (pack.compact() if pack else {})
    )
    news_articles = (
        news_insight_articles(state.question or "", pack.news_grouped)
        if pack and is_article_only_news(plan, pack)
        else []
    )
    if news_articles:
        evidence_dict = {"ARTICLES": news_articles}
    evidence_text = json.dumps(evidence_dict, ensure_ascii=False)

    policy_meta = pack.display_table_policy if pack else {}
    wants = {
        "goal": plan.goal,
        "answer_mode": plan.answer_mode.value,
        "style": plan.response_shape,
        "max_words": plan.max_words,
        "lead_with": plan.lead_with,
        "asks_for_advice": plan.asks_for_advice,
        **(policy_meta or {}),
    }
    if str(getattr(plan, "fund_pick", "") or "").strip().lower() not in ("", "none"):
        wants["fund_pick"] = str(plan.fund_pick).strip().lower()
    if str(getattr(plan, "planner_reading", "") or "").strip():
        wants["reading"] = plan.planner_reading.strip()
    return_windows: list[str] = []
    for call in plan.tool_calls:
        modules = list((call.arguments or {}).get("modules") or [])
        if call.tool == "get_fund_data" and any(name in modules for name in ("snapshot", "vs_benchmark", "return_series")):
            return_windows.extend(str(item) for item in ((call.arguments or {}).get("windows") or []))
    if return_windows:
        wants["measured_window"] = ", ".join(dict.fromkeys(return_windows))
        wants["measured_window_days"] = plan.window_days
    wants["end_summary"] = _wants_end_summary(plan, state.question or "")
    if state.memory:
        from news_rag.insight.memory.prompt import prompt_view

        view = prompt_view(state.memory)
        if view:
            wants["conversation"] = view
            state.memory_sent_composer = True
    if plan.answer_depth == "more":
        wants["explain_more"] = True
        wants["max_words"] = max(int(wants.get("max_words") or 0), 220)
    if (plan.presentation_notes or "").strip():
        wants["presentation_notes"] = plan.presentation_notes.strip()
    from news_rag.insight.investor_subject import (
        question_asks_whole_investor_portfolio,
        question_refers_deictic_fund,
        resolve_answer_subject,
    )

    inv_holdings: list[dict[str, Any]] = []
    if pack:
        inv = (pack.data_pack or {}).get("investor_portfolio") if pack else {}
        if isinstance(inv, dict):
            inv_holdings = [r for r in (inv.get("holdings") or []) if isinstance(r, dict)]
    subject = resolve_answer_subject(
        state.question or "",
        plan,
        state.memory,
        investor_holdings=inv_holdings,
        wave1_results=state.wave1_results,
    )
    if question_asks_whole_investor_portfolio(state.question or "", plan):
        wants["investor_portfolio_overview"] = True
        overview_notes = (
            "Whole-book overview: use `## Your portfolio` as the title. "
            "Prefer markdown tables for schemes and category allocation; blank line before each table."
        )
        wants["presentation_notes"] = " ".join(
            filter(None, [str(wants.get("presentation_notes") or "").strip(), overview_notes])
        ).strip()
    elif subject:
        wants["answer_subject"] = subject
    if pack and isinstance(pack.data_pack.get("portfolio_news_impact"), dict):
        wants["portfolio_news_impact_answer"] = True
        wants["max_words"] = max(int(wants.get("max_words") or 0), 480)
        impact_notes = (
            "Use EVIDENCE.portfolio_news_impact for sector and fund exposure tables. "
            "Sector-impact reasons come from sector_impact_analysis; do not invent weights."
        )
        wants["presentation_notes"] = " ".join(
            filter(None, [str(wants.get("presentation_notes") or "").strip(), impact_notes])
        ).strip()
        wants.pop("investor_portfolio_overview", None)
    if question_refers_deictic_fund(state.question or "") and subject:
        reading = str(getattr(plan, "planner_reading", "") or "").strip()
        if reading and subject.lower() not in reading.lower():
            wants["reading"] = f"Follow-up about {subject} (pronoun in the question refers to this scheme)."
            wants["presentation_notes"] = " ".join(
                filter(
                    None,
                    [
                        str(wants.get("presentation_notes") or "").strip(),
                        "Do not use a different fund name from an old planner guess — answer_subject is authoritative.",
                    ],
                )
            ).strip()
    if plan.sub_queries:
        wants["parts"] = [
            {
                "text": str(part.get("text") or "").strip(),
                **({"source": part.get("source")} if part.get("source") else {}),
            }
            for part in plan.sub_queries
            if str(part.get("text") or "").strip()
        ]
    if (plan.concept_brief or "").strip():
        wants["concept_brief"] = plan.concept_brief.strip()
    from news_rag.insight.computed_answers import asks_computed_illustration

    if asks_computed_illustration(state.question or ""):
        wants["compute_illustration"] = True
        wants["max_words"] = max(int(wants.get("max_words") or 0), 420)

    user_content = (
        f"QUESTION:\n{state.question.strip()}\n\n"
        f"WHAT THE USER WANTS:\n{json.dumps(wants, ensure_ascii=False)}\n\n"
        f"EVIDENCE:\n{evidence_text}"
    )

    from news_rag.insight.glossary import asks_precise_definition

    glossary_only = asks_precise_definition(state.question or "") and not (
        evidence_dict.get("rows") or evidence_dict.get("data_pack") or evidence_dict.get("DATA")
    )
    if news_articles:
        wants["max_words"] = max(int(wants.get("max_words") or 0), 180)
        user_content = (
            f"QUESTION:\n{state.question.strip()}\n\n"
            f"WHAT THE USER WANTS:\n{json.dumps(wants, ensure_ascii=False)}\n\n"
            f"ARTICLES:\n{evidence_text}"
        )
        compose_system = COMPOSE_SYSTEM_NEWS
        max_tokens = 700
    elif glossary_only:
        wants["max_words"] = 40
        wants["style"] = "short_answer"
        user_content = (
            f"QUESTION:\n{state.question.strip()}\n\n"
            f"WHAT THE USER WANTS:\n{json.dumps(wants, ensure_ascii=False)}\n\n"
            f"EVIDENCE:\n{evidence_text}"
        )
        compose_system = COMPOSE_SYSTEM_PRECISE
        max_tokens = 120
    elif use_facts_compose and fact_brief:
        wants["max_words"] = max(int(wants.get("max_words") or 0), 450)
        user_content = (
            f"QUESTION:\n{state.question.strip()}\n\n"
            f"WHAT THE USER WANTS:\n{json.dumps(wants, ensure_ascii=False)}\n\n"
            f"FACTS:\n{fact_brief}"
        )
        compose_system = COMPOSE_SYSTEM_FACTS
        max_tokens = 900
    else:
        compose_system = COMPOSE_SYSTEM
        wants["max_words"] = max(int(wants.get("max_words") or 0), 180)
        word_budget = int(wants.get("max_words") or plan.max_words or 220)
        max_tokens = max(500, min(2500, word_budget * 4))
        if pack and pack.news_grouped:
            wants["max_words"] = max(int(wants.get("max_words") or 0), 420)
            max_tokens = max(max_tokens, min(2500, int(wants["max_words"]) * 4))
            ordered = dict(evidence_dict)
            news_block = ordered.pop("NEWS", None)
            if news_block is not None:
                ordered = {"NEWS": news_block, **ordered}
            evidence_text = json.dumps(ordered, ensure_ascii=False)
            user_content = (
                f"QUESTION:\n{state.question.strip()}\n\n"
                "TASK: NEWS is in EVIDENCE. Open with ### What stands out. "
                "Write one block per insight_links row. State the weight and the facts in that row's points, "
                "including the article text. Use those articles. "
                "The last sentence of each block is a fact from those points. "
                "Do not add a closer about how the fund may behave, whether a forecast is confirmed, "
                "or that the news matters more to the stock than to the fund. "
                "Do not open with a returns recap. Do not paste headlines.\n\n"
                f"WHAT THE USER WANTS:\n{json.dumps(wants, ensure_ascii=False)}\n\n"
                f"EVIDENCE:\n{evidence_text}"
            )

    t0 = time.time()
    res = call_insight_llm(
        system_prompt=compose_system,
        user_content=user_content,
        query_log=state.query_log,
        model_override=composer_model(settings),
        max_tokens=max_tokens,
        temperature=0.2,
        stage="composer",
        cached_system_prefix=shared_system_prefix(),
    )
    elapsed_ms = (time.time() - t0) * 1000.0

    if state.telemetry is not None and res is not None:
        state.telemetry.add_llm_usage(
            stage="compose",
            provider=res.provider,
            model=res.model,
            input_tokens=res.input_tokens,
            output_tokens=res.output_tokens,
            cached_input_tokens=getattr(res, "cached_tokens", 0),
            total_ms=round(elapsed_ms, 1),
            usage_source="api",
        )

    raw_text = (res.raw_text or "").strip() if res else ""
    if state.query_log and raw_text:
        state.query_log.write(f"COMPOSE_RAW chars={len(raw_text)} output_tokens={getattr(res, 'output_tokens', 0) or 0}")
    if not raw_text:
        state.pipeline_errors.append({"stage": "compose", "tool": "", "message": "empty response"})
        if template_answer:
            state.answer = _clean_answer(template_answer)
            state.route_reason = "composer empty; template fallback"
            return None
        if pack and pack.data_pack:
            state.answer = _clean_answer(json.dumps(pack.data_pack))
            return None
        raise RuntimeError("Composer LLM produced empty text")

    # Strip figures only when we actually measured something. A calculation or explanation
    # with empty evidence must keep the numbers the composer wrote.
    measured = bool(
        evidence_dict.get("DATA")
        or evidence_dict.get("PERFORMANCE")
        or evidence_dict.get("DISPLAY")
        or evidence_dict.get("TABLE_SUMMARIES")
    )
    if news_articles or measured:
        allowed_numbers = cores_in_text(evidence_text) | cores_in_text(state.question or "")
        allowed_numbers |= derived_cores(allowed_numbers)
        if pack and isinstance(pack.data_pack.get("investor_portfolio"), dict):
            from news_rag.insight.grounding import investor_book_cores

            allowed_numbers |= investor_book_cores(pack.data_pack["investor_portfolio"])
        if pack and isinstance(pack.data_pack, dict):
            from news_rag.insight.grounding import fund_portfolio_cores

            allowed_numbers |= fund_portfolio_cores(pack.data_pack)
        grounded_text = strip_ungrounded_numbers(raw_text, allowed_numbers)
    else:
        grounded_text = raw_text
    polished_text = strip_media_attribution(grounded_text)
    if pack and isinstance(pack.data_pack.get("investor_portfolio"), dict):
        from news_rag.insight.evidence_pack import repair_investor_insight_prose
        from news_rag.insight.fund_display import strip_grounding_holes

        polished_text = repair_investor_insight_prose(
            polished_text,
            pack.data_pack["investor_portfolio"],
        )
        polished_text = strip_grounding_holes(polished_text)
    if news_articles:
        from news_rag.insight.fund_display import clean_news_insight

        polished_text = clean_news_insight(polished_text)
    from news_rag.insight.fund_display import strip_missing_data_caveats, strip_private_leaks
    from news_rag.insight.multi_fact import asks_one_figure

    from news_rag.insight.fund_display import (
        assemble_fund_overview_answer,
        filter_display_tables_by_decision,
        parse_tables_append_directive,
    )

    polished_text, table_decision = parse_tables_append_directive(polished_text)
    polished_text = strip_private_leaks(strip_missing_data_caveats(polished_text))
    lead = _rating_lead_for_pack(pack, state.question or "")
    if _plan_fetches_manager_roster(plan):
        lead = ""
    display_tables = {} if fact_brief or asks_one_figure(state.question or "") else (pack.display_tables if pack else {})
    impact_dossier = (
        pack.data_pack.get("portfolio_news_impact")
        if pack and isinstance(pack.data_pack.get("portfolio_news_impact"), dict)
        else None
    )
    if impact_dossier:
        display_tables = {}
    if display_tables and table_decision is not None:
        display_tables = filter_display_tables_by_decision(display_tables, table_decision)
    overview_layout = (
        plan.intent == "overview"
        and len(plan.funds or []) == 1
        and plan.answer_mode == AnswerMode.INSIGHT_FUSION
        and bool(display_tables)
    )
    if overview_layout:
        polished_text = assemble_fund_overview_answer(
            polished_text,
            display_tables,
            rating_lead_text=lead,
            question=state.question or "",
        )
    else:
        if lead and "RupeeStop rating" not in polished_text and "out of" not in polished_text[:180]:
            polished_text = f"{lead}\n\n{polished_text}".strip()
        if display_tables and any(k for k in display_tables if k != "_title"):
            polished_text = stitch_display_tables_into_answer(
                polished_text,
                display_tables,
                question=state.question or "",
            )
    investor = {}
    if pack and isinstance(pack.data_pack, dict):
        investor = pack.data_pack.get("investor_portfolio") if isinstance(pack.data_pack.get("investor_portfolio"), dict) else {}
    from news_rag.insight.evidence_pack import (
        _concentration_markdown,
        append_investor_portfolio_overview_tables,
    )
    from news_rag.fund_risk import asks_fund_risk

    if question_asks_whole_investor_portfolio(state.question or "", plan) and investor:
        if not (pack and isinstance(pack.data_pack.get("portfolio_news_impact"), dict)):
            polished_text = append_investor_portfolio_overview_tables(polished_text, investor, plan)

    from news_rag.insight.portfolio_news_impact import (
        question_is_portfolio_news_impact,
        render_portfolio_news_impact_markdown,
        _strip_book_concentration_tables,
    )

    concentration_block = _concentration_markdown((investor or {}).get("concentration"))
    append_concentration = bool(concentration_block)
    if impact_dossier or question_is_portfolio_news_impact(state.question or "", plan):
        append_concentration = False
    if append_concentration and asks_fund_risk(state.question or "") and len(plan.funds or []) == 1:
        append_concentration = False
    if (
        append_concentration
        and "### Portfolio concentration" not in polished_text
        and "### Top holdings" not in polished_text
    ):
        polished_text = f"{polished_text}\n\n{concentration_block}".strip()
    if impact_dossier or question_is_portfolio_news_impact(state.question or "", plan):
        polished_text = _strip_book_concentration_tables(polished_text)
    if impact_dossier:
        impact_block = render_portfolio_news_impact_markdown(impact_dossier)
        if impact_block:
            polished_text = f"{polished_text}\n\n{impact_block}".strip()
    if concentration_block:
        polished_text = _drop_scheme_is_the_whole_book(polished_text)
    from news_rag.insight.fact_slots import render_asked_facts, slots_from_plan
    from news_rag.insight.sector_exposure_tables import (
        render_all_holdings_metric_table,
        render_all_holdings_return_table,
        render_all_holdings_sector_table,
    )

    slots = slots_from_plan(state.plan) if state.plan else []
    wave_results = [*state.wave1_results, *state.wave2_results]
    fact_table = render_asked_facts(slots, wave_results)
    if state.plan and str(state.plan.holding_scope or "") == "all_holdings":
        metric_table = render_all_holdings_metric_table(state.plan, wave_results, state.memory)
        if metric_table:
            fact_table = metric_table
        elif not fact_table:
            ret_table = render_all_holdings_return_table(state.plan, wave_results, state.memory)
            if ret_table:
                fact_table = ret_table
        else:
            ret_table = render_all_holdings_return_table(state.plan, wave_results, state.memory)
            if ret_table:
                fact_table = f"{fact_table}\n\n{ret_table}".strip()
        sector_table = render_all_holdings_sector_table(state.plan, wave_results, state.memory)
        if sector_table:
            fact_table = f"{fact_table}\n\n{sector_table}".strip() if fact_table else sector_table
    if fact_table and fact_table not in polished_text:
        polished_text = f"{polished_text}\n\n{fact_table}".strip()
    from news_rag.insight.metals_spot_tables import render_gold_returns_table, strip_gold_window_table

    gold_table = render_gold_returns_table(wave_results)
    if gold_table:
        polished_text = strip_gold_window_table(polished_text)
        if gold_table not in polished_text:
            polished_text = f"{polished_text}\n\n{gold_table}".strip()
    polished_text = strip_news_roundup(polished_text)
    if state.query_log and raw_text:
        state.query_log.write(
            f"COMPOSE_POST chars={len(polished_text)} measured={measured} "
            f"grounded_delta={len(raw_text) - len(grounded_text if measured else raw_text)}"
        )
    if (
        asks_one_figure(state.question or "")
        and len(polished_text.strip()) < 80
        and any(not r.get("ok") for r in (state.wave1_results or []) if r.get("tool") == "get_fund_data")
    ):
        polished_text = (
            polished_text.strip()
            or f"## {(plan.funds or ['This fund'])[0]}\n\nWe can't get that data right now."
        )
        if "can't get that data" not in polished_text.lower():
            polished_text = f"{polished_text.rstrip()}\n\nWe can't get that data right now.".strip()
    state.answer = _clean_answer(polished_text)

    # Jev judge is paused for ask. The score was recorded and the answer was still returned.
    # if plan.answer_mode == AnswerMode.INSIGHT_FUSION and getattr(settings, "insight_verify_retry", True):
    #     try:
    #         judge_res = judge_answer(
    #             state.question,
    #             state.answer,
    #             evidence_text[:4000],
    #             query_log=state.query_log,
    #             telemetry=state.telemetry,
    #         )
    #         state.judge_result = {"passed": judge_res.passed, "scores": judge_res.scores}
    #         if state.telemetry:
    #             state.telemetry.quality_state = "passed" if judge_res.passed else "failed"
    #     except Exception as exc:
    #         logger.warning("Judge execution error: %s", exc)

    state.route_reason = f"composed ({elapsed_ms:.1f}ms, chars={len(state.answer)})"
    return None


def node_reply(state: GraphState) -> str | None:
    if state.query_log is not None and state.plan is not None:
        state.query_log.log_execution_plan(state.plan)
    state.route_reason = state.reply_kind
    return None


# ---------------------------------------------------------------------------
# Graph Definition
# ---------------------------------------------------------------------------

NODES: dict[str, Node] = {
    "route": Node("route", node_route, on_error=None, uses_llm=True),
    "resolve": Node("resolve", node_resolve, on_error="evidence_gate"),
    "wave1": Node("wave1", node_wave1, on_error="bridge"),
    "bridge": Node("bridge", node_bridge, on_error="evidence_gate"),
    "wave2": Node("wave2", node_wave2, on_error="evidence_gate"),
    "evidence_gate": Node("evidence_gate", node_evidence_gate, on_error="compose"),
    "compose": Node("compose", node_compose, on_error=None, uses_llm=True),
    "reply": Node("reply", node_reply, on_error=None),
}
ENTRY = "route"
MAX_HOPS = 10


def run_graph(state: GraphState) -> GraphState:
    log = state.query_log
    name: str | None = ENTRY
    hops = 0

    while name and hops < MAX_HOPS:
        hops += 1
        node = NODES.get(name)
        if not node:
            break

        if log is not None:
            log.log_pipeline(node.name, "start")
        if state.telemetry is not None:
            state.telemetry.start_phase(node.name)

        t0 = time.perf_counter()
        nxt: str | None
        error = ""

        try:
            nxt = node.run(state)
        except GraphUnavailable:
            raise
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"[:240]
            state.pipeline_errors.append({"stage": node.name, "tool": "", "message": error})
            if node.on_error is None:
                if log is not None:
                    log.log_pipeline(node.name, "error", seconds=round(time.perf_counter() - t0, 3), error=error)
                raise
            nxt = node.on_error
            state.route_reason = f"{node.name} error ({error}), routing to {nxt}"

        seconds = round(time.perf_counter() - t0, 3)
        state.trace.append({
            "node": node.name,
            "seconds": seconds,
            "next": nxt,
            "why": state.route_reason,
            "error": error,
        })

        if log is not None:
            log.log_pipeline(
                node.name,
                "done",
                seconds=seconds,
                next=nxt or "end",
                why=state.route_reason,
                llm=node.uses_llm,
            )
        if state.telemetry is not None:
            state.telemetry.end_phase(node.name, duration_ms=round(seconds * 1000, 1))

        name = nxt

    return state


def _store_turn_memory(state: GraphState, sources: list[dict[str, Any]] | None) -> dict[str, int]:
    """Write the frame after the turn. A failed lookup is recorded as no subject."""
    from news_rag.insight.memory.evidence import drain_cache_events
    from news_rag.insight.memory.prompt import memory_json_tokens, prompt_view
    from news_rag.insight.memory.store import save_sources, save_turn_record
    from news_rag.insight.memory.update import commit_turn

    empty_tokens = {"planner": 0, "composer": 0}
    if not state.conversation_id or state.plan is None:
        return empty_tokens
    if state.query_log is not None:
        for event in drain_cache_events(state.conversation_id):
            beside = f" beside={event['beside']}" if event.get("beside") else ""
            state.query_log.write(f"CACHE status={event['status']} key={event['key']}{beside}")
    query_id = state.query_log.query_id if state.query_log is not None else ""
    if sources and query_id:
        save_sources(query_id, sources, conversation_id=state.conversation_id)
    saved = commit_turn(
        state.conversation_id,
        state.plan,
        state.wave1_results + state.wave2_results,
        question=state.question or "",
    )
    stored_view = prompt_view(saved)
    passed_view = state.memory_passed_view if isinstance(state.memory_passed_view, dict) else {}
    planner_tokens = memory_json_tokens(passed_view)
    composer_tokens = planner_tokens if state.memory_sent_composer else 0
    sent_to = []
    if planner_tokens:
        sent_to.append("planner")
    if composer_tokens:
        sent_to.append("composer")
    if query_id:
        save_turn_record(query_id, {
            "query_id": query_id,
            "passed": {
                "sent_to": sent_to,
                "token_estimate": {"planner": planner_tokens, "composer": composer_tokens},
                "memory": passed_view,
            },
            "stored": {
                "updated_by": "python",
                "memory": stored_view,
            },
        })
    if state.query_log is not None:
        state.query_log.write("MEMORY_STORED " + json.dumps(stored_view, ensure_ascii=False))
        state.query_log.write(
            f"MEMORY_TOKENS planner={planner_tokens} composer={composer_tokens}"
        )
    return {"planner": planner_tokens, "composer": composer_tokens}


def build_result(state: GraphState) -> dict[str, Any]:
    plan = state.plan
    pack = state.evidence_pack

    sources: list[dict[str, Any]] = []
    if pack and pack.news_grouped:
        for scope, articles in pack.news_grouped.items():
            for art in articles:
                if isinstance(art, dict):
                    sources.append(art)

    insight = state.answer
    refused = state.reply_kind in ("out_of_scope", "clarify")
    headline = next((ln.strip(" #*") for ln in insight.splitlines() if ln.strip()), insight[:120])
    terms = list(dict.fromkeys((state.resolved_funds + (plan.sectors if plan else []))))[:8]

    tool_runs = [
        {"tool": r.get("tool"), "ok": r.get("ok"), "elapsed_ms": r.get("elapsed_ms")}
        for r in (state.wave1_results + state.wave2_results)
    ]

    research = {
        "pipeline": "two_wave_graph",
        "goal": plan.goal if plan else "",
        "plan": plan.summary() if plan else {},
        "tool_runs": tool_runs,
        "nodes": state.trace,
        "judge": state.judge_result,
        "remaining_deadline_ms": state.remaining_deadline_ms(),
    }

    fund_rankings: list[dict[str, Any]] = []
    fund_return_window = ""
    fund_managers: dict[str, Any] | None = None
    if pack and isinstance(pack.data_pack.get("screen"), dict):
        scr = pack.data_pack["screen"]
        if not isinstance(pack.data_pack.get("portfolio_news_impact"), dict):
            fund_rankings = list(scr.get("rankings") or scr.get("funds") or [])[:20]
            fund_return_window = str(scr.get("return_window") or "").strip().upper()
    if pack:
        for key, block in pack.data_pack.items():
            if not key.startswith("fund:") or not isinstance(block, dict):
                continue
            mgr = block.get("managers")
            if isinstance(mgr, dict) and (mgr.get("current") or mgr.get("past")):
                fund_managers = mgr
                break

    res = {
        "insight": insight,
        "fund_rankings": fund_rankings,
        "fund_return_window": fund_return_window,
        "fund_managers": fund_managers,
        "insight_summary": headline,
        "insight_headline": headline,
        "insight_narrative": insight,
        "insight_closing_summary": "",
        "insight_bullets": [],
        "highlight_terms": terms,
        "sources": sources_from_articles(sources),
        "retrieval_window": {
            "window_days": plan.window_days if plan else 30,
            "window_label": plan.window_label if plan else "1 month",
        },
        "intent": plan.intent if plan else "lookup",
        "insight_source": "insight_graph_v3",
        "outcome": "refused" if refused else ("ok" if insight.strip() else "no_data"),
        "refused": refused,
        "sections": [{"id": "A1", "style": plan.response_shape if plan else "sections", "text": insight, "headline": headline}],
        "sub_queries": plan.sub_queries if plan else [],
        "pipeline_errors": state.pipeline_errors,
        "output_score": state.judge_result.get("scores", {}).get("grounded"),
        "output_scores": state.judge_result.get("scores", {}),
        "advice_note": ADVICE_NOTE,
        "research": research,
        "answer_trace": {"mode": "two_wave_graph", "route": [t["node"] for t in state.trace]},
    }
    query_id = state.query_log.query_id if state.query_log is not None else ""
    used_news = bool(sources)
    res["memory_tokens"] = _store_turn_memory(state, sources if used_news else None)
    res["query_id"] = query_id
    res["used_news"] = used_news
    res["sources_href"] = f"sources?query_id={query_id}" if used_news and query_id else ""
    if query_id:
        res["memory_passed_href"] = f"memory-passed?query_id={query_id}"
        res["memory_stored_href"] = f"memory-stored?query_id={query_id}"

    if state.telemetry:
        state.telemetry.finalize()
        res["telemetry"] = state.telemetry.to_sse_telemetry()
        res["llm_input_tokens"] = state.telemetry.total_input_tokens
        res["llm_output_tokens"] = state.telemetry.total_output_tokens
        res["cached_input_tokens"] = state.telemetry.cached_input_tokens
        res["llm_calls"] = len(state.telemetry.llm_usage)

    return res


def run_graph_pipeline(
    question: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
    prior_context: dict[str, Any] | None = None,
    telemetry: RequestTelemetry | None = None,
) -> dict[str, Any]:
    """Run the bounded two-wave graph pipeline."""
    state = GraphState(
        question=(question or "").strip(),
        date_from=date_from,
        date_to=date_to,
        min_impact=min_impact,
        source=source,
        direction=direction,
        query_log=query_log,
        prior_context=prior_context,
        telemetry=telemetry,
    )
    if query_log is not None:
        query_log.log_pipeline("insight_graph", "start", nodes=",".join(NODES))
    run_graph(state)
    return build_result(state)


async def stream_graph_pipeline(
    question: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
    prior_context: dict[str, Any] | None = None,
) -> Any:
    """Stream the bounded two-wave graph execution with granular SSE events."""
    import asyncio
    from news_rag.insight.telemetry import (
        event_answer_completed,
        event_answer_delta,
        event_phase_completed,
        event_phase_started,
        event_quality_check,
        event_request_failed,
        event_request_started,
        event_tool_completed,
        event_tool_started,
        new_telemetry,
    )

    telemetry = new_telemetry()
    yield event_request_started(telemetry, question)
    await asyncio.sleep(0)

    state = GraphState(
        question=(question or "").strip(),
        date_from=date_from,
        date_to=date_to,
        min_impact=min_impact,
        source=source,
        direction=direction,
        query_log=query_log,
        prior_context=prior_context,
        telemetry=telemetry,
    )

    try:
        # Step-by-step streamed graph execution
        name: str | None = ENTRY
        hops = 0

        while name and hops < MAX_HOPS:
            hops += 1
            node = NODES.get(name)
            if not node:
                break

            yield event_phase_started(telemetry, node.name)
            await asyncio.sleep(0)

            # Emit tool_started events before waves
            if node.name == "wave1" and state.plan:
                for c in state.plan.wave1_calls:
                    yield event_tool_started(telemetry, c.tool, wave=1)
                    await asyncio.sleep(0)
            elif node.name == "wave2" and state.plan:
                for c in state.plan.wave2_calls:
                    yield event_tool_started(telemetry, c.tool, wave=2)
                    await asyncio.sleep(0)

            t0 = time.perf_counter()
            nxt: str | None = None
            error = ""

            try:
                nxt = node.run(state)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"[:240]
                state.pipeline_errors.append({"stage": node.name, "tool": "", "message": error})
                if node.on_error is None:
                    yield event_request_failed(telemetry, error)
                    raise
                nxt = node.on_error
                state.route_reason = f"{node.name} failed ({error}), advancing to {nxt}"

            dur_ms = round((time.perf_counter() - t0) * 1000, 1)

            # Emit tool_completed events after waves
            if node.name == "wave1":
                for r in state.wave1_results:
                    yield event_tool_completed(
                        telemetry,
                        r.get("tool", ""),
                        wave=1,
                        ok=bool(r.get("ok")),
                        duration_ms=float(r.get("elapsed_ms") or 0.0),
                        fund=str(r.get("fund") or ""),
                    )
                    await asyncio.sleep(0)
            elif node.name == "wave2":
                for r in state.wave2_results:
                    yield event_tool_completed(
                        telemetry,
                        r.get("tool", ""),
                        wave=2,
                        ok=bool(r.get("ok")),
                        duration_ms=float(r.get("elapsed_ms") or 0.0),
                    )
                    await asyncio.sleep(0)

            yield event_phase_completed(telemetry, node.name, duration_ms=dur_ms, why=state.route_reason)
            await asyncio.sleep(0)

            name = nxt

        # Stream answer deltas (line chunks when markdown tables — word chunks break | rows)
        answer = state.answer or "No information found."
        for chunk in _answer_stream_chunks(answer):
            yield event_answer_delta(telemetry, chunk)
            await asyncio.sleep(0.01)

        # Quality check event if judge was run
        if state.judge_result:
            yield event_quality_check(
                telemetry,
                state="passed" if state.judge_result.get("passed") else "failed",
                scores=state.judge_result.get("scores", {}),
            )
            await asyncio.sleep(0)

        # Final result
        result = build_result(state)
        if query_log is not None:
            from news_rag.query_log import attach_query_log_meta
            meta = query_log.finish_from_ask_result(result, question=question)
            attach_query_log_meta(result, meta)

        yield event_answer_completed(telemetry, answer, result)

    except Exception as exc:
        yield event_request_failed(telemetry, str(exc))
