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
- Compose: Fast deterministic Markdown template for DATA_ONLY (<500ms), or LLM compose
           with numeric grounding and selective quality judge.
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
from news_rag.insight.grounding import cores_in_text, strip_media_attribution, strip_ungrounded_numbers
from news_rag.insight.plan import make_plan, plan_to_brief
from news_rag.insight.slot_router import slot_route
from news_rag.llm_client import (
    call_insight_llm,
    composer_model,
    llm_api_key_configured,
)
from news_rag.output_judge import judge_answer
from news_rag.prompts import COMPOSER_MARKDOWN_LAYOUT, FINANCIAL_SYSTEM_BASE
from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

DISCLAIMER = "*For context only — not investment advice.*"
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

def node_route(state: GraphState) -> str | None:
    """Intake & routing: Fast-path slot router or single structured planner LLM."""
    settings = get_settings()
    threshold = float(getattr(settings, "slot_router_confidence", 0.8))

    from news_rag.insight.question_intent import (
        plan_matches_intent,
        prefers_planner_over_slot,
        resolve_question_intent,
    )

    intent = resolve_question_intent(state.question)
    slot_plan = slot_route(state.question, confidence_threshold=threshold)
    use_slot = (
        slot_plan is not None
        and slot_plan.confidence >= threshold
        and plan_matches_intent(slot_plan, intent)
        and not prefers_planner_over_slot(state.question)
    )

    if use_slot and slot_plan is not None:
        state.plan = slot_plan
        state.route_reason = (
            f"slot_router fast-path (confidence={slot_plan.confidence:.2f}, intent={intent.kind})"
        )
        if state.query_log is not None:
            state.query_log.write(
                f"ROUTER choice=slot_router confidence={slot_plan.confidence:.2f} intent={intent.kind}"
            )
    else:
        if slot_plan is not None and state.query_log is not None:
            reason = "below_threshold" if slot_plan.confidence < threshold else "intent_mismatch"
            state.query_log.write(
                f"ROUTER slot_skipped reason={reason} slot_conf={slot_plan.confidence:.2f} "
                f"intent={intent.kind} slot_tools={slot_plan.tool_names}"
            )
        plan = make_plan(
            state.question,
            prior_context=state.prior_context,
            query_log=state.query_log,
            telemetry=state.telemetry,
        )
        if plan is None:
            if slot_plan is not None:
                state.plan = slot_plan
                state.route_reason = "planner unavailable; using slot_router fallback"
                if state.query_log is not None:
                    state.query_log.write("ROUTER choice=slot_router fallback=planner_failed")
            else:
                raise GraphUnavailable("Planner returned no plan")
        else:
            state.plan = plan
            if not plan_matches_intent(plan, intent) and state.query_log is not None:
                state.query_log.write(
                    f"ROUTER planner_plan intent_check=weak intent={intent.kind} tools={plan.tool_names}"
                )
            state.route_reason = f"planner LLM ({len(plan.tool_calls)} tools, intent={intent.kind})"
            if state.query_log is not None:
                state.query_log.write(f"ROUTER choice=planner tools={len(plan.tool_calls)} intent={intent.kind}")

    plan = state.plan
    if plan is None:
        raise GraphUnavailable("No execution plan after routing")

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

    return "resolve"


def _resolve_funds(plan: ExecutionPlan) -> tuple[list[str], list[str]]:
    from news_rag.fund_search import get_fund_index

    idx = get_fund_index()
    resolved: list[str] = []
    unresolved: list[str] = []

    for name in plan.funds:
        detail, _ambiguous, _close = idx.lookup_extracted_fund(name=name)
        if not detail:
            hits = idx.search(name, limit=1)
            detail = hits[0] if hits else None
        if detail:
            resolved.append(str(detail.get("fund_short_name") or detail.get("fund_name") or name))
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

    return list(dict.fromkeys(resolved)), unresolved


def node_resolve(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None

    funds, unresolved = _resolve_funds(plan)
    state.resolved_funds = funds
    state.unresolved_funds = unresolved

    sector_keys: list[str] = []
    if plan.sectors:
        from news_rag.sector_fund_ranking import get_sector_fund_ranking_index
        sector_keys = get_sector_fund_ranking_index().resolve_sector_keys(plan.sectors)
    state.sector_keys = sector_keys

    # Missing fund check
    wanted_funds = bool(plan.funds) or plan.random_fund_count > 0
    if wanted_funds and not funds and not plan.sectors and not plan.stocks and not plan.drivers:
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


def _maybe_enrich_picked_fund_from_screen(state: GraphState) -> None:
    """After screen (pick a fund + overview), fetch snapshot/portfolio for the top match."""
    q = (state.question or "").strip()
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

    ctx = {
        "question": q,
        "window_days": plan.window_days if plan else 30,
        "fund_names": [fund],
    }
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

    context = {
        "question": state.question,
        "fund_names": state.resolved_funds,
        "sector_name": state.sector_keys[0] if state.sector_keys else (plan.sectors[0] if plan.sectors else ""),
        "sector_keys": state.sector_keys,
        "stock_name": plan.stocks[0] if plan.stocks else "",
        "drivers": [d["id"] for d in plan.drivers],
        "driver_direction": next((d.get("direction") or "" for d in plan.drivers if d.get("direction")), ""),
        "window_days": plan.window_days,
        "direction": "any",
        "top_n": 5,
    }

    deadline_ms = max(8000.0, min(state.remaining_deadline_ms() - 5000.0, 25000.0))
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

    state.wave1_results = results
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

    ok_count = sum(1 for r in results if r.get("ok"))
    state.route_reason = f"wave1: {ok_count}/{len(results)} ok ({elapsed_ms:.1f}ms)"

    if plan.answer_mode == AnswerMode.DATA_ONLY:
        return "evidence_gate"

    return "bridge"


def node_bridge(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None

    remaining_ms = state.remaining_deadline_ms()
    wave2_calls = evaluate_wave2(
        plan,
        state.wave1_results,
        deadline_remaining_ms=remaining_ms,
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

    context = {
        "question": state.question,
        "fund_names": state.resolved_funds,
        "sector_name": state.sector_keys[0] if state.sector_keys else "",
        "sector_keys": state.sector_keys,
        "window_days": min(plan.window_days, 30),
        "direction": "any",
        "top_n": 3,
    }

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

    pack = build_evidence_pack(
        plan,
        state.wave1_results,
        state.wave2_results,
        token_budget=10000,
    )
    state.evidence_pack = pack
    state.route_reason = (
        f"pack: {len(pack.rows)} entity rows, news={bool(pack.news_grouped)}, "
        f"missing={len(pack.missing)}"
    )
    return "compose"


COMPOSE_SYSTEM = f"""{FINANCIAL_SYSTEM_BASE}

ROLE: COMPOSER (user-facing markdown only)
You receive QUESTION, WHAT THE USER WANTS (goal, answer_mode, style, max_words), and EVIDENCE (metrics + optional news).

CORE RULES:
1. Lead with the direct answer in the first sentence; bold key figures from EVIDENCE only.
2. INSIGHT_FUSION: connect measured moves -> drivers -> mechanism -> what it means for what they asked (fund, sector, macro).
3. Honor WHAT THE USER WANTS.style when set: short_answer (1-2 paragraphs), bullets (list-heavy), table (metric/compare tables), sections (mixed sections + bullets/tables as needed).
4. Ground every number in EVIDENCE. Simple arithmetic on those numbers is allowed; label approximations.
5. Never mention internal terms: DATA, NEWS, EVIDENCE, tool, pipeline, JSON, articles retrieved.
6. If EVIDENCE is empty or a list is missing, say clearly that no rows were returned — never claim a scan failed unless EVIDENCE says so.
7. For rankings or holdings in EVIDENCE, prefer a markdown table; keep columns readable (name, weight %, return if present).
8. Do not repeat the same table if the UI already shows fund_rankings — summarize in one short paragraph instead.

{COMPOSER_MARKDOWN_LAYOUT}
"""


def _clean_answer(text: str) -> str:
    text = re.sub(r"```(?:json|markdown)?", "", text or "").strip()
    if DISCLAIMER.lower().strip("*") not in text.lower():
        text = text.rstrip() + "\n\n" + DISCLAIMER
    return text


def compose_user_content(state: GraphState) -> str:
    """Format prompt payload for composer."""
    plan = state.plan
    wants = {
        "goal": plan.goal if plan else "",
        "answer_mode": plan.answer_mode.value if plan else "DATA_ONLY",
        "style": plan.response_shape if plan else "sections",
        "max_words": plan.max_words if plan else 220,
        "lead_with": plan.lead_with if plan else "",
        "asks_for_advice": plan.asks_for_advice if plan else False,
    }
    pack = state.evidence_pack
    evidence_dict = pack.compact() if pack else {}
    return (
        f"QUESTION:\n{state.question.strip()}\n\n"
        f"WHAT THE USER WANTS:\n{json.dumps(wants, ensure_ascii=False)}\n\n"
        f"EVIDENCE:\n{json.dumps(evidence_dict, ensure_ascii=False)}"
    )


def node_compose(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None
    pack = state.evidence_pack

    # Fast Path: Check for DATA_ONLY Template
    if plan.answer_mode == AnswerMode.DATA_ONLY and pack is not None:
        template_answer = render_data_only_template(pack, plan)
        if template_answer:
            state.answer = _clean_answer(template_answer)
            state.route_reason = "DATA_ONLY direct template (<10ms)"
            return None

    # LLM Composition
    settings = get_settings()
    if not llm_api_key_configured(settings):
        # Fallback to deterministic partial if no key configured
        if pack:
            state.answer = _clean_answer("Here is the requested information:\n\n" + json.dumps(pack.data_pack, indent=2))
            return None
        raise GraphUnavailable("No LLM key configured for composer")

    evidence_dict = pack.compact() if pack else {}
    evidence_text = json.dumps(evidence_dict, ensure_ascii=False)

    wants = {
        "goal": plan.goal,
        "answer_mode": plan.answer_mode.value,
        "style": plan.response_shape,
        "max_words": plan.max_words,
        "lead_with": plan.lead_with,
        "asks_for_advice": plan.asks_for_advice,
    }

    user_content = (
        f"QUESTION:\n{state.question.strip()}\n\n"
        f"WHAT THE USER WANTS:\n{json.dumps(wants, ensure_ascii=False)}\n\n"
        f"EVIDENCE:\n{evidence_text}"
    )

    max_tokens = max(500, min(2500, plan.max_words * 4))
    t0 = time.time()
    res = call_insight_llm(
        system_prompt=COMPOSE_SYSTEM,
        user_content=user_content,
        query_log=state.query_log,
        model_override=composer_model(settings),
        max_tokens=max_tokens,
        temperature=0.2,
        stage="composer",
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
    if not raw_text:
        state.pipeline_errors.append({"stage": "compose", "tool": "", "message": "empty response"})
        # Fallback: render whatever structured data we have
        if pack and pack.data_pack:
            state.answer = _clean_answer(json.dumps(pack.data_pack))
            return None
        raise RuntimeError("Composer LLM produced empty text")

    # Numeric Grounding check
    allowed_numbers = cores_in_text(evidence_text)
    grounded_text = strip_ungrounded_numbers(raw_text, allowed_numbers)
    polished_text = strip_media_attribution(grounded_text)
    state.answer = _clean_answer(polished_text)

    # Selective Judge for INSIGHT_FUSION
    if plan.answer_mode == AnswerMode.INSIGHT_FUSION and getattr(settings, "insight_verify_retry", True):
        try:
            judge_res = judge_answer(
                state.question,
                state.answer,
                evidence_text[:4000],
                query_log=state.query_log,
                telemetry=state.telemetry,
            )
            state.judge_result = {"passed": judge_res.passed, "scores": judge_res.scores}
            if state.telemetry:
                state.telemetry.quality_state = "passed" if judge_res.passed else "failed"
        except Exception as exc:
            logger.warning("Judge execution error: %s", exc)

    state.route_reason = f"composed ({elapsed_ms:.1f}ms, chars={len(state.answer)})"
    return None


def node_reply(state: GraphState) -> str | None:
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

        # Stream answer deltas
        answer = state.answer or "No information found."
        words = answer.split(" ")
        chunk_size = 6
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i + chunk_size])
            if i + chunk_size < len(words):
                chunk += " "
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
