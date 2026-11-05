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
    "I am an AI bot by SUM, and I can help with Indian mutual funds, stocks, sectors and the market. "
    "Ask me about a fund's NAV or returns, what a fund holds, your portfolio, how a sector is doing, "
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
    memory_resynced: bool = False
    conversation_reset_required: bool = False

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
    from news_rag.insight.memory.hydrate import hydrate_memory_from_prior_turns, normalize_prior_turns
    from news_rag.insight.memory.prompt import chat_history_view
    from news_rag.insight.memory.store import get_memory

    prior = state.prior_context if isinstance(state.prior_context, dict) else {}
    client_turns = prior.get("turns")
    state.conversation_id = _conversation_id(state)
    server_empty = not get_memory(state.conversation_id) if state.conversation_id else True
    prior_rows = normalize_prior_turns(client_turns if isinstance(client_turns, list) else None)

    if state.conversation_id and prior_rows:
        hydrated_state, did_hydrate = hydrate_memory_from_prior_turns(
            state.conversation_id,
            client_turns if isinstance(client_turns, list) else None,
        )
        state.memory = hydrated_state or get_memory(state.conversation_id)
        if did_hydrate:
            state.memory_resynced = True
            if state.query_log is not None:
                state.query_log.write("MEMORY_HYDRATED from_client_prior_turns")
    elif state.conversation_id:
        state.memory = get_memory(state.conversation_id)
    else:
        state.memory = None

    view = chat_history_view(state.memory)
    state.memory_passed_view = view
    if state.query_log is not None:
        state.query_log.write("MEMORY_PASSED " + json.dumps(view, ensure_ascii=False))
    if server_empty and prior_rows and not view.get("turns"):
        state.conversation_reset_required = True
    if not view.get("turns"):
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
    from news_rag.insight.guardrails import guard_reply

    guarded = (
        guard_reply(state.question or "", portfolio_enabled=bool(get_settings().portfolio_enabled))
        if not greeting_reply(state.question or "")
        else None
    )
    if guarded:
        state.answer = _clean_answer(guarded[1])
        state.reply_kind = "out_of_scope" if guarded[0] != "advice" else "direct"
        state.route_reason = f"guard:{guarded[0]}"
        if state.query_log is not None:
            state.query_log.write(f"ROUTE guard kind={guarded[0]}")
        return "reply"

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
    from news_rag.insight.investor_subject import enforce_catalog_fund_list_scope

    plan = enforce_catalog_fund_list_scope(plan, state.memory, state.question or "")
    planned_tools = [f"{c.tool}:{','.join(map(str, (c.arguments or {}).get('modules') or []))}" for c in plan.tool_calls]
    from news_rag.insight.plan_enforce import apply_planner_post_hooks

    plan = apply_planner_post_hooks(state.question, plan, state.memory)
    from news_rag.insight.plan_catalog_bind import enforce_planner_catalog_plan

    plan = enforce_planner_catalog_plan(plan, state.memory, state.question or "")
    from news_rag.insight.planner_policy import align_planned_news_execution

    plan = align_planned_news_execution(plan)
    from news_rag.insight.plan_validate import validate_plan_tools

    plan = validate_plan_tools(state.question, plan, state.memory)
    from news_rag.insight.fund_name_gate import clarify_plan_if_fund_unknown

    plan = clarify_plan_if_fund_unknown(plan, state.memory, state.question or "")
    from news_rag.insight.fund_concentration import ensure_fund_concentration_plan
    from news_rag.insight.multi_fact import ensure_planner_fund_fact_modules

    plan = ensure_planner_fund_fact_modules(state.question or "", plan)
    plan = ensure_fund_concentration_plan(state.question or "", plan)
    from news_rag.insight.fields import bind_fields_to_tools
    from news_rag.insight.plan_enforce import finalize_fund_compare_plan
    from news_rag.insight.plan_intent import plan_wants_fund_compare

    plan = bind_fields_to_tools(state.question or "", plan)
    if plan_wants_fund_compare(plan):
        finalize_fund_compare_plan(state.question or "", plan)
    plan = enforce_catalog_fund_list_scope(plan, state.memory, state.question or "")
    state.plan = plan
    if state.query_log is not None:
        tools = [f"{c.tool}({c.arguments})" for c in plan.tool_calls]
        state.query_log.write(f"PLAN_AFTER_HOOKS tools={tools} funds={plan.funds}")
        final_tools = [f"{c.tool}:{','.join(map(str, (c.arguments or {}).get('modules') or []))}" for c in plan.tool_calls]
        added = [t for t in final_tools if t not in planned_tools]
        dropped = [t for t in planned_tools if t not in final_tools]
        if added or dropped:
            # Every tool the code adds or removes after the planner shows where code overrides the model.
            state.query_log.write(f"HOOKS_REWROTE_PLAN added={added} dropped={dropped}")

    # Set deadline budget based on query class
    if plan.query_class == QueryClass.SIMPLE:
        state.deadline_ms = float(getattr(settings, "request_deadline_simple_ms", 20000))
    elif plan.query_class == QueryClass.COMPLEX:
        state.deadline_ms = float(getattr(settings, "request_deadline_complex_ms", 60000))
    else:
        state.deadline_ms = float(getattr(settings, "request_deadline_standard_ms", 40000))

    if any(c.tool == "get_investor_portfolio" for c in (plan.tool_calls or [])):
        # Portfolio APIs often take 12–20s. The simple 20s budget expires mid-call.
        state.deadline_ms = max(state.deadline_ms, 45000.0)

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
        from news_rag.insight.brief import question_is_bullion_metal_price_question

        bullion_price = question_is_bullion_metal_price_question(state.question or "")
        has_market_tools = any(c.tool == "get_market_snapshot" for c in (plan.tool_calls or []))
        if bullion_price and has_market_tools:
            plan.funds = []
            wanted_funds = False
        else:
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

    deadline_ms = max(8000.0, min(state.remaining_deadline_ms() - 2000.0, 35000.0))
    if any(c.tool == "get_investor_portfolio" for c in calls):
        deadline_ms = max(deadline_ms, min(25000.0, state.remaining_deadline_ms() - 1500.0))
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

        investor_calls = [c for c in calls if c.tool == "get_investor_portfolio"]
        catalog_calls = [c for c in calls if c.tool != "get_investor_portfolio"]
        # Book tool first. Catalog fan-out on every holding shares one deadline and
        # marks get_investor_portfolio deadline_exceeded before it starts.
        if investor_calls and (catalog_calls or plan_needs_investor_before_catalog(plan, state.memory)):
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
                from news_rag.insight.investor_subject import question_asks_whole_investor_portfolio
                from news_rag.insight.plan_intent import plan_wants_fund_compare

                if plan_wants_fund_compare(plan) and plan.funds:
                    merged = list(plan.funds)
                    for name in holding_names:
                        if name not in merged:
                            merged.append(name)
                    plan.funds = merged
                elif str(plan.holding_scope or "") == "all_holdings":
                    plan.funds = holding_names
                elif question_asks_whole_investor_portfolio(state.question or "", plan):
                    plan.funds = holding_names
                state.resolved_funds = list(plan.funds)
                context["fund_names"] = list(plan.funds)
            from news_rag.insight.portfolio_news_impact import question_is_portfolio_news_impact

            if question_is_portfolio_news_impact(state.question or "", plan):
                sectors: list[str] = []
                for row in inv_results:
                    data = row.get("data") if isinstance(row.get("data"), dict) else {}
                    conc = data.get("concentration") if isinstance(data.get("concentration"), dict) else {}
                    for sector_row in (conc.get("sectors") or [])[:5]:
                        if isinstance(sector_row, dict):
                            name = str(sector_row.get("sector") or "").strip()
                            if name and name not in sectors:
                                sectors.append(name)
                if sectors:
                    for call in catalog_calls:
                        if call.tool != "search_financial_news":
                            continue
                        args = dict(call.arguments or {})
                        topics = [str(t) for t in (args.get("topics") or []) if str(t).strip()]
                        for name in sectors:
                            if name not in topics:
                                topics.append(name)
                        args["topics"] = topics[:8]
                        call.arguments = args
            spent_ms = (time.time() - t0) * 1000.0
            rest_budget = deadline_ms - spent_ms
            fanout_tools = {"get_fund_data", "get_portfolio_data", "compare_funds"}
            fanout_calls = [c for c in catalog_calls if c.tool in fanout_tools]
            other_calls = [c for c in catalog_calls if c.tool not in fanout_tools]
            fund_count = len(holding_names or state.resolved_funds or [])
            run_fanout = bool(fanout_calls) and rest_budget >= 8000 and fund_count <= 8
            rest_calls = other_calls + (fanout_calls if run_fanout else [])
            if fanout_calls and not run_fanout and state.query_log is not None:
                state.query_log.write(
                    f"WAVE1 skip_catalog reason=deadline_or_fanout "
                    f"funds={fund_count} rest_ms={rest_budget:.0f}"
                )
            if rest_calls:
                rest_results = execute_wave(
                    rest_calls,
                    context,
                    fund_names=holding_names or state.resolved_funds,
                    telemetry=state.telemetry,
                    deadline_ms=max(rest_budget, 8000.0),
                    query_log=state.query_log,
                )
            else:
                rest_results = []
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
        plan_wants_investor_drawdown_fetch,
        plan_wants_portfolio_drawback,
    )

    remaining_ms = state.remaining_deadline_ms()
    wants_drawdown = plan_wants_investor_drawdown_fetch(plan, state.question or "") or plan_wants_portfolio_drawback(
        plan, state.question or ""
    )
    if wants_drawdown and remaining_ms >= 2500:
        drawdown_calls = build_drawdown_wave2_calls(
            state.wave1_results,
            plan=plan,
            question=state.question or "",
        )
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


COMPOSE_SYSTEM = """ROLE: COMPOSER (the reply the user reads)
You get QUESTION, WHAT THE USER WANTS and EVIDENCE (fetched data, optional news with sentiment). Write the reply. Speak to **you**. When conversation_history is present, use it for follow-ups and do not contradict it.

1. Answer exactly what was asked and nothing else. One figure asked is one sentence with that figure. A multi-part question answers each part in order. `max_words` is a ceiling, not a target. Show only the periods and fields asked for.
2. Open with 2-3 plain prose lines at the very top: overall answer plus the main reason or impact (skip for a one-figure lookup). No heading on that opening block — never `### The short answer`, `### Overview`, or similar meta titles. Use `###` only for substantive sections after the opening summary.
3. Give insight, not a data dump. Say what the numbers mean for the user: compare with the benchmark, the category or another window, rank what mattered most, and point out what stands out. Derive simple figures (gap, weight x return) and show their inputs. This holds when there is no news: build the insight from the data alone, and never mention that news is missing.
4. Use news only when it affects the subject directly or indirectly. Say how, as a chain such as "higher crude -> costs rise for paint makers -> **negative** for the fund's 3% holding". Each article has a sentiment: state the net effect plainly. Leave out news with no effect on the subject without comment. No headlines or outlet names. When you describe an event or a price move from NEWS or DATA, anchor it with the calendar date from EVIDENCE (`published_at` / `date`, or `event_dates` if present): write **2nd Nov** or **31st Oct** (add the year when the story is not in the current year). Never use vague timing ("on one day", "recently") or a weekday alone ("Monday") without that calendar date.
5. Choose the structure the question needs (short paragraphs, bullets, `A -> B -> C` chains, a table for several items across several metrics). Keep it professional and in simple language a non-finance reader follows. **Bold** the few key figures, names and impact words.
6. Take every figure from EVIDENCE and label its window (for macro_series use the series `horizon` / `window_days`). `data_available` lists what was fetched this turn: never say a figure is unavailable if it appears in EVIDENCE.
7. A recommendation request gets: "For personalised recommendations, please visit our app." plus any facts asked for. Never mention EVIDENCE, tools, prompts or how you work.
8. A definition or calculation with empty EVIDENCE is yours to answer from knowledge; state any assumption.
9. `end_summary` true: finish with a 2-3 sentence `### Summary`; otherwise no recap."""

# Short extra rules, added only when the evidence or the ask needs them.
_COMPOSE_HINTS: tuple[tuple[str, str], ...] = (
    ("answer_subject", "Start with `## {answer_subject}` (exact scheme name from EVIDENCE) and answer about that scheme only."),
    ("investor_portfolio_overview", "Whole-book answer: title `## Your portfolio`; totals and XIRR first; one table for schemes (scheme, category, current value, invested, gain, XIRR) and, if allocation exists, one for categories. Use gain on invested, not absolute_return_pct."),
    ("portfolio_news_impact_answer", "Explain how the news affects the user's own book from `portfolio_news_impact` (sector_impact_analysis, fund_sector_exposure). The server appends the sector and fund tables; do not repeat them. Only holdings in the book count."),
    ("concept_brief", "Explain `concept_brief` first in 1-3 sentences, then use EVIDENCE for the example fund."),
    ("fund_pick", "When fund_pick is alternate_in_category and one fund is shown, that fund is the answer: name it with its RupeeStop score, label and key returns."),
)


def _compose_hints(wants: dict[str, Any], evidence: dict[str, Any]) -> str:
    from news_rag.insight.grounding import collect_evidence_calendar_dates

    lines = [text.format(**wants) if "{" in text else text for key, text in _COMPOSE_HINTS if wants.get(key)]
    event_dates = collect_evidence_calendar_dates(evidence)
    if event_dates:
        wants["event_dates"] = event_dates
        lines.append(
            "Use `event_dates` (from NEWS `published_at`) when stating when something happened or when a "
            "quoted price level was reported; do not invent dates outside this list or EVIDENCE."
        )
    if evidence.get("DISPLAY"):
        lines.append(
            "The server appends the fund tables after your text, so write the insight in prose. If your own "
            "table already covers them, end with `<!-- TABLES_APPEND: none -->` (or `default` to keep them all)."
        )
    if evidence.get("NEWS"):
        lines.append(
            "Open with 2-3 plain prose lines (no heading), not `### The short answer`. Then use `###` for "
            "substantive sections only. For each material event or price level, state the calendar date from "
            "that row's `published_at` / `date`, then the figure and how it affects the subject."
        )
    data_text = json.dumps(evidence.get("DATA") or "", default=str)
    if "metals_spot" in data_text or "gold" in data_text.lower()[:4000]:
        lines.append("Gold figures are 24K gold in INR per 10 grams; give the horizon on each. Never quote a silver price.")
    if "rs_rating" in data_text:
        lines.append("A RupeeStop rating lead is placed above your answer: do not repeat the score or pillar marks. A pillar mark is an internal score, not a statement of how risky the fund is.")
    return "\n".join(f"- {line}" for line in lines)


def strip_meta_opening_heading(text: str) -> str:
    """Drop a leading ### The short answer-style title; keep the summary prose."""
    meta = frozenset(
        {
            "the short answer",
            "short answer",
            "in short",
            "in brief",
            "at a glance",
            "quick answer",
            "bottom line",
        }
    )
    lines = (text or "").splitlines()
    if not lines:
        return text or ""
    m = re.match(r"^#{1,3}\s+(.+?)\s*$", lines[0].strip())
    if not m or m.group(1).strip().lower().rstrip(".:") not in meta:
        return text
    return "\n".join(lines[1:]).lstrip().strip()


def _clean_answer(text: str) -> str:
    from news_rag.indian_format import normalize_rupee_commas_in_text

    text = normalize_user_facing_text(re.sub(r"```(?:json|markdown)?", "", text or "").strip())
    text = normalize_rupee_commas_in_text(text)
    text = strip_meta_opening_heading(text)
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
    """A close only when the question asked for an overview or a why. A compare does not recap."""
    from news_rag.insight.multi_fact import asks_one_figure

    if asks_one_figure(question) and len(plan.sub_queries or []) < 2:
        return False
    q = question or ""
    if re.search(r"\b(?:summary|overview|tell me about|overall)\b", q, re.I):
        return True
    if plan.intent == "explain_cause" and re.search(r"\bwhy\b", q, re.I):
        return True
    return False


def _strip_unasked_closers(text: str, *, keep_summary: bool) -> str:
    """Drop next-step and recap sections the model adds on a specific question."""
    drop = {"what you can do next", "next steps", "what to do next"}
    if not keep_summary:
        drop.add("summary")
    kept: list[str] = []
    skipping = False
    for line in (text or "").splitlines():
        heading = re.match(r"^#{2,3}\s+(.*)$", line.strip())
        if heading:
            title = heading.group(1).strip().lower().rstrip(".")
            skipping = title in drop
            if skipping:
                continue
        if skipping:
            continue
        kept.append(line)
    return "\n".join(kept).strip()


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

    from news_rag.insight.fact_answer import (
        FIELD_TEMPLATE_COMPOSER_MIN_HOLDINGS,
        field_answer_needs_composer,
        is_pure_field_answer,
        render_benchmark_comparison_table,
        render_fact_answer,
        render_investor_rs_ratings_table,
    )
    from news_rag.insight.fields import wants_comparison_table

    compose_always = bool(getattr(get_settings(), "insight_compose_always", True))
    if compose_always:
        plan.requires_compose = True

    if not compose_always and pack is not None and wants_comparison_table(state.question or "", plan):
        table_answer = render_benchmark_comparison_table(pack, plan, state.question or "")
        if table_answer:
            state.answer = _clean_answer(table_answer)
            state.route_reason = "benchmark comparison table"
            if state.query_log is not None:
                state.query_log.write("COMPOSE benchmark_comparison_table")
            return None

    if not compose_always and pack is not None:
        rs_table = render_investor_rs_ratings_table(plan, pack.data_pack, state.question or "")
        if rs_table and not field_answer_needs_composer(plan, pack.data_pack, rs_table):
            state.answer = _clean_answer(rs_table)
            state.route_reason = "investor rs ratings table"
            if state.query_log is not None:
                state.query_log.write(f"COMPOSE investor_rs_table rows={rs_table.count(chr(10))}")
            return None
        if rs_table and field_answer_needs_composer(plan, pack.data_pack, rs_table):
            plan.requires_compose = True
            if state.query_log is not None:
                state.query_log.write(
                    f"COMPOSE defer_to_llm reason=rs_list_size holdings>={FIELD_TEMPLATE_COMPOSER_MIN_HOLDINGS}"
                )

    if not compose_always and pack is not None and is_pure_field_answer(plan, state.question or "", pack.data_pack):
        fact_text = render_fact_answer(plan, pack.data_pack, state.question or "")
        if fact_text:
            state.answer = _clean_answer(fact_text)
            state.route_reason = "field template"
            if state.query_log is not None:
                state.query_log.write(
                    "COMPOSE field_template fields=" + ",".join(plan.asked_fields or [])
                )
            return None

    template_answer = None
    if (
        not compose_always
        and plan.answer_mode == AnswerMode.DATA_ONLY
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
    history_block = ""
    if state.memory:
        from news_rag.insight.memory.prompt import format_chat_history_block

        history_block = format_chat_history_block(state.memory)
        if history_block:
            wants["conversation_history"] = history_block
            state.memory_sent_composer = True
    if plan.answer_depth == "more":
        wants["explain_more"] = True
        wants["max_words"] = max(int(wants.get("max_words") or 0), 220)
    if pack and plan.asked_fields and not is_pure_field_answer(plan, state.question or "", pack.data_pack):
        pinned = render_fact_answer(plan, pack.data_pack, state.question or "")
        if pinned:
            plan.presentation_notes = (
                f"{plan.presentation_notes} Use these measured lines and do not add figures they do not contain:\n{pinned}"
            ).strip()
    if (plan.presentation_notes or "").strip():
        wants["presentation_notes"] = plan.presentation_notes.strip()
    from news_rag.insight.investor_subject import (
        question_asks_whole_investor_portfolio,
        question_refers_deictic_fund,
        resolve_answer_subject,
    )
    from news_rag.insight.investor_drawback import (
        plan_wants_investor_drawdown_fetch,
        question_asks_portfolio_level_drawdown,
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
    if question_asks_portfolio_level_drawdown(state.question or "", plan) or plan_wants_investor_drawdown_fetch(
        plan, state.question or ""
    ):
        wants["investor_portfolio_overview"] = True
        dd_notes = (
            "Portfolio drawdown ask: title `## Your portfolio`. "
            "Compare `drawdown.episodes` (max_drawdown) across fund entries in EVIDENCE; "
            "name the scheme with the deepest maximum drawdown and the period (1Y/3Y/5Y). "
            "Do not pick the first holding row as the answer subject."
        )
        wants["presentation_notes"] = " ".join(
            filter(None, [str(wants.get("presentation_notes") or "").strip(), dd_notes])
        ).strip()
    elif question_asks_whole_investor_portfolio(state.question or "", plan):
        wants["investor_portfolio_overview"] = True
        overview_notes = (
            "Whole-book overview: use `## Your portfolio` as the title. "
            "Prefer markdown tables for schemes and category allocation; blank line before each table. "
            "Per scheme use gain_loss_inr and gain on invested (gain/invested), not API absolute_return_pct "
            "(-100% when current value is zero). Show at most 8 schemes in tables unless the user asked for all funds; "
            "portfolio totals must reflect every scheme."
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

    from news_rag.insight.glossary import asks_precise_definition
    from news_rag.insight.memory.update import _facts_from_plan

    glossary_only = asks_precise_definition(state.question or "") and not (
        evidence_dict.get("rows") or evidence_dict.get("data_pack") or evidence_dict.get("DATA")
    )
    fetched = _facts_from_plan(plan)
    if fetched:
        wants["data_available"] = fetched

    # The planner's max_words is the user's length; defaults apply only when it gave none.
    if glossary_only:
        wants["max_words"] = 40
        wants["style"] = "short_answer"
        label, body, default_words = "EVIDENCE", evidence_text, 40
    elif news_articles:
        label, body, default_words = "ARTICLES", evidence_text, 180
    elif use_facts_compose and fact_brief:
        label, body, default_words = "FACTS", fact_brief, 300
    else:
        label, body, default_words = "EVIDENCE", evidence_text, 320 if (pack and pack.news_grouped) else 220
        if pack and pack.news_grouped:
            ordered = dict(evidence_dict)
            news_block = ordered.pop("NEWS", None)
            if news_block is not None:
                body = json.dumps({"NEWS": news_block, **ordered}, ensure_ascii=False)
    words = int(wants.get("max_words") or plan.max_words or 0) or default_words
    wants["max_words"] = words
    max_tokens = 120 if glossary_only else max(300, min(2500, words * 4))
    compose_system = COMPOSE_SYSTEM
    hints = _compose_hints(wants, evidence_dict)
    if hints:
        compose_system = f"{COMPOSE_SYSTEM}\n\nFOR THIS ANSWER:\n{hints}"
    user_content = (
        f"QUESTION:\n{state.question.strip()}\n\n"
        f"WHAT THE USER WANTS:\n{json.dumps(wants, ensure_ascii=False)}\n\n"
        f"{label}:\n{body}"
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
            polished_text = append_investor_portfolio_overview_tables(
                polished_text, investor, plan, state.question or ""
            )

    from news_rag.insight.portfolio_news_impact import (
        question_is_portfolio_news_impact,
        render_portfolio_news_impact_markdown,
        _strip_book_concentration_tables,
    )

    from news_rag.insight.display_table_policy import question_wants_concentration_tables

    concentration_block = _concentration_markdown((investor or {}).get("concentration"))
    append_concentration = bool(concentration_block) and question_wants_concentration_tables(
        state.question or ""
    )
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
    from news_rag.insight.display_table_policy import (
        fact_values_already_stated,
        question_wants_fact_table,
        question_wants_gold_table,
    )
    from news_rag.insight.fact_slots import render_asked_facts, slots_from_plan
    from news_rag.insight.sector_exposure_tables import (
        render_all_holdings_metric_table,
        render_all_holdings_return_table,
        render_all_holdings_sector_table,
    )

    slots = slots_from_plan(state.plan) if state.plan else []
    wave_results = [*state.wave1_results, *state.wave2_results]
    fact_table = render_asked_facts(slots, wave_results)
    wants_fact_table = question_wants_fact_table(state.question or "", state.plan)
    if wants_fact_table and state.plan and str(state.plan.holding_scope or "") == "all_holdings":
        pack_data = pack.data_pack if pack else None
        metric_table = render_all_holdings_metric_table(
            state.plan,
            wave_results,
            state.memory,
            data_pack=pack_data,
        )
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
    if (
        fact_table
        and wants_fact_table
        and fact_table not in polished_text
        and not fact_values_already_stated(polished_text, fact_table)
    ):
        polished_text = f"{polished_text}\n\n{fact_table}".strip()
    from news_rag.insight.metals_spot_tables import render_gold_returns_table, strip_gold_window_table

    gold_table = render_gold_returns_table(wave_results) if question_wants_gold_table(state.question or "") else ""
    if gold_table:
        polished_text = strip_gold_window_table(polished_text)
        if gold_table not in polished_text:
            polished_text = f"{polished_text}\n\n{gold_table}".strip()
    polished_text = strip_news_roundup(polished_text)
    polished_text = _strip_unasked_closers(
        polished_text,
        keep_summary=_wants_end_summary(plan, state.question or ""),
    )
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
    """Write internal frame after the turn and append chat transcript for the LLM."""
    from news_rag.insight.memory.evidence import drain_cache_events
    from news_rag.insight.memory.prompt import chat_history_view, memory_json_tokens
    from news_rag.insight.memory.state import append_chat_turn
    from news_rag.insight.memory.store import get_or_create, save_sources, save_state, save_turn_record
    from news_rag.insight.memory.update import commit_turn

    empty_tokens = {"planner": 0, "composer": 0}
    if not state.conversation_id:
        return empty_tokens

    query_id = state.query_log.query_id if state.query_log is not None else ""
    answer_text = (state.answer or "").strip()
    conv_state: dict[str, Any] | None = None

    if state.plan is not None:
        if state.query_log is not None:
            for event in drain_cache_events(state.conversation_id):
                beside = f" beside={event['beside']}" if event.get("beside") else ""
                state.query_log.write(f"CACHE status={event['status']} key={event['key']}{beside}")
        if sources and query_id:
            save_sources(query_id, sources, conversation_id=state.conversation_id)
        conv_state = commit_turn(
            state.conversation_id,
            state.plan,
            state.wave1_results + state.wave2_results,
            question=state.question or "",
        )
    elif answer_text:
        conv_state = get_or_create(state.conversation_id)

    if conv_state and answer_text:
        if state.plan is not None:
            chat_turn = int(conv_state.get("turn_count") or 0)
        else:
            chat_turn = len(conv_state.get("chat_turns") or []) + 1
        append_chat_turn(
            conv_state,
            user=state.question or "",
            assistant=answer_text,
            turn=chat_turn,
            query_id=query_id,
        )
        save_state(conv_state)

    passed_view = state.memory_passed_view if isinstance(state.memory_passed_view, dict) else {}
    stored_view = chat_history_view(conv_state) if conv_state else {"turns": []}
    planner_tokens = memory_json_tokens(passed_view)
    composer_tokens = planner_tokens if state.memory_sent_composer else 0
    sent_to = []
    if planner_tokens:
        sent_to.append("planner")
    if composer_tokens:
        sent_to.append("composer")
    if query_id and conv_state is not None:
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
    if state.query_log is not None and conv_state is not None:
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

    res["memory_resynced"] = bool(state.memory_resynced)
    res["conversation_reset_required"] = bool(state.conversation_reset_required)

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
