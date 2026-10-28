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
from news_rag.insight.fund_display import (
    is_article_only_news,
    news_insight_articles,
    normalize_user_facing_text,
    stitch_display_tables_into_answer,
    strip_news_roundup,
)
from news_rag.insight.grounding import cores_in_text, strip_media_attribution, strip_ungrounded_numbers
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
    pref_planner = prefers_planner_over_slot(state.question)
    slot_ok_conf = slot_plan is not None and slot_plan.confidence >= threshold
    if (
        slot_plan is not None
        and plan_matches_intent(slot_plan, intent)
        and intent.kind == "fund_portfolio"
        and slot_plan.answer_mode == AnswerMode.DATA_ONLY
        and slot_plan.confidence >= 0.9
    ):
        slot_ok_conf = True
    use_slot = (
        slot_plan is not None
        and slot_ok_conf
        and plan_matches_intent(slot_plan, intent)
        and not pref_planner
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
            if slot_plan.confidence < threshold:
                reason = "below_threshold"
            elif pref_planner:
                reason = "planner_preferred"
            elif not plan_matches_intent(slot_plan, intent):
                reason = "intent_mismatch"
            else:
                reason = "unknown"
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
            if (
                (plan.routed_by or "") != "planner"
                and not plan_matches_intent(plan, intent)
                and state.query_log is not None
            ):
                state.query_log.write(
                    f"ROUTER planner_plan intent_check=weak intent={intent.kind} tools={plan.tool_names}"
                )
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
    from news_rag.fund_drawdown import ensure_drawdown_tools
    from news_rag.fund_rating_screen import ensure_rating_screen
    from news_rag.fund_risk import ensure_risk_tools
    from news_rag.insight.multi_fact import (
        ensure_compare_template,
        ensure_multi_fact_tools,
        ensure_screen_facts,
    )

    ensure_multi_fact_tools(state.question, plan)
    ensure_screen_facts(state.question, plan)
    ensure_compare_template(plan)
    ensure_drawdown_tools(state.question, plan)
    ensure_risk_tools(state.question, plan)
    ensure_rating_screen(state.question, plan)

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


def _resolve_funds(plan: ExecutionPlan) -> tuple[list[str], list[str]]:
    from news_rag.fund_search import get_fund_index

    idx = get_fund_index()
    resolved: list[str] = []
    unresolved: list[str] = []

    for name in plan.funds:
        detail, _ambiguous, _close = idx.lookup_extracted_fund(name=name)
        if not detail and re.search(r"\bINF[A-Z0-9]{9}\b", name or "", re.I):
            isin_m = re.search(r"\b(INF[A-Z0-9]{9})\b", name, re.I)
            if isin_m:
                detail, _ambiguous, _close = idx.lookup_extracted_fund(isin=isin_m.group(1))
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
    if state.query_log is not None:
        state.query_log.log_execution_plan(plan)

    funds, unresolved = _resolve_funds(plan)
    state.resolved_funds = funds
    state.unresolved_funds = unresolved
    if state.query_log is not None:
        state.query_log.write(f"RESOLVED funds={funds} unresolved={unresolved}")

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

    screen_first = [c for c in calls if c.tool == "screen_funds_by_exposure"]
    after_screen = [c for c in calls if c.tool != "screen_funds_by_exposure"]
    sequence_screen = bool(screen_first) and any(c.tool == "compare_funds" for c in after_screen)

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

    ok_count = sum(1 for r in state.wave1_results if r.get("ok"))
    state.route_reason = f"wave1: {ok_count}/{len(state.wave1_results)} ok ({elapsed_ms:.1f}ms)"

    if plan.answer_mode == AnswerMode.DATA_ONLY:
        return "evidence_gate"

    return "bridge"


def _ensure_portfolio_for_fund_news(state: GraphState) -> None:
    from news_rag.tools import asks_fund_related_news

    if not asks_fund_related_news(state.question or ""):
        return
    if not state.resolved_funds:
        return
    from news_rag.insight.capabilities.executor import execute_capability
    from news_rag.insight.contracts import ToolCall

    fund = state.resolved_funds[0]
    plan = state.plan
    ctx = {
        "question": state.question,
        "window_days": plan.window_days if plan else 30,
        "fund_names": [fund],
    }
    has_portfolio = any(
        r.get("tool") == "get_portfolio_data" and r.get("ok") for r in state.wave1_results
    )
    has_metrics = any(
        r.get("tool") == "get_fund_data" and r.get("ok") for r in state.wave1_results
    )
    extra: list[ToolCall] = []
    if not has_metrics:
        extra.append(
            ToolCall(
                tool="get_fund_data",
                arguments={
                    "modules": ["snapshot", "return_series", "attribution"],
                    "top_n": 3,
                    "window_days": min(plan.window_days if plan else 30, 30),
                },
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
            execute_capability(
                tc,
                fund_names=[fund],
                ctx=ctx,
                telemetry=state.telemetry,
            )
        )


def node_bridge(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None

    _ensure_portfolio_for_fund_news(state)

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

    context = {
        "question": state.question,
        "fund_names": state.resolved_funds,
        "sector_name": state.sector_keys[0] if state.sector_keys else "",
        "sector_keys": state.sector_keys,
        "window_days": min(plan.window_days, 30),
        "direction": "any",
        "top_n": 3,
        "wave1_results": state.wave1_results,
        "query_log": state.query_log,
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

    if state.query_log is not None:
        state.query_log.log_tool_results(1, state.wave1_results)
        if state.wave2_results:
            state.query_log.log_tool_results(2, state.wave2_results)

    pack = build_evidence_pack(
        plan,
        state.wave1_results,
        state.wave2_results,
        token_budget=10000,
        question=state.question or "",
    )
    state.evidence_pack = pack
    state.route_reason = (
        f"pack: {len(pack.rows)} entity rows, news={bool(pack.news_grouped)}, "
        f"missing={len(pack.missing)}"
    )
    return "compose"


COMPOSE_SYSTEM = """ROLE: COMPOSER (user-facing markdown only)
You receive QUESTION, WHAT THE USER WANTS (goal, answer_mode, style, max_words), and EVIDENCE (metrics + optional news).

CORE RULES:
0. **Concept + data:** When WHAT THE USER WANTS includes `concept_brief`, explain that concept first (1–3 sentences), then use EVIDENCE for the example fund/scheme. Do not skip the concept or invent fund names.
1. **Match the question.** A lookup is a short table or a few lines. An explanation can be longer. A calculation with empty EVIDENCE is still an answer: show the figures and the assumption. Do not pad a simple question into an essay.
2. **Returns in prose:** Compare a fund with its benchmark only when a benchmark return is present, and with the category average only when that average is present. If neither is present, do not write a comparison and do not say that the comparison is missing or cannot be stated. If only one side is present, compare only that side. Cite the exact gap in percentage points. Do not say "about" when the gap is computable. Do not fill a missing side with a hyphen or a guess. Do not write a returns bullet list or a "Returns (horizon labelled)" section; the returns table is appended for you. Do not say how much of the move is unexplained, or that named holdings fail to explain the fund's return. When PERFORMANCE or the snapshot includes expense_ratio, exit_load_summary, or aum_crore, state all three that are present: the expense ratio (regular unless the field is direct), the exit-load sentence, and AUM in crore with its as-on date. Do not mention a direct-plan expense ratio unless that is the field in the snapshot. Do not say these figures are unavailable when they are present.
3. **Tables (server decides).** Read WHAT THE USER WANTS `tables_in_answer` and `tables_rationale`. Only those comparison blocks are appended after your text — do not hand-build `|` tables for fund returns or rankings. A small table is fine when EVIDENCE is empty and you are showing a calculation you did. If `tables_in_answer` is empty, skip vs-benchmark/category table talk unless the user explicitly asked for returns. Holdings: **weight %** and **holding return %** only (no per-stock pp). `holding_contribution_pp_internal` is for ranking only.
4. **Missing measured data:** Use **-** only for a figure that should have come from EVIDENCE and is absent. Never replace a number the user stated, or a number you calculated, with a hyphen.
5. **No news roundup.** Do not add `### Recent news`, `### What the news says`, or a list of article titles. A news fact belongs in the narrative only when it explains a measured move for a holding or sector already in the answer. For a sector overview, use the reported facts from the articles to explain that sector's measured move, not one caveat sentence. When DATA includes `macro_news`, that block is already the short list for this question's window. Use those articles in the answer. Do not leave them out, and do not replace them with a backdrop that is not written in them. Do not invent a cause, and do not add a section that calls funds examples.
6. **Numbers:** If EVIDENCE has measured figures, those figures must match EVIDENCE. If EVIDENCE is empty, answer the question anyway. Definitions, explanations, and calculations are yours to write, with the actual amounts. If an input is missing, name one assumption and compute with it. A small calculation table is allowed when the user asked for a plan or a projection. Do not recommend a product.
7. **Horizon on every measured percent.** Each price or return row has `horizon` (1D, 1W, 1M, 3M, 6M, 1Y, or a day count such as 14D). WHAT THE USER WANTS also has `measured_window`. Write that code on the figure: Nifty **+0.7% (1W)**. If one figure is 1W and another is 1M, label both. Do not call a 1W or 1M change "the latest session", "today", or "right now".
8. **No invented levels.** A macro row is a percent change, not a Brent price, a rupee level, or an Indian bond yield. Do not print a level the row does not contain, and do not leave a blank where a number should be. A level or a percent that appears only in a news summary is what that article reported, not the measured move.
9. Never mention: DATA, NEWS, EVIDENCE, DISPLAY, tool, pipeline, JSON, yfinance, proxy.
10. Do not repeat UI fund_rankings tables — one summary line is enough.
"""

COMPOSE_SYSTEM_PRECISE = """ROLE: COMPOSER — **precise short answer only**
The user asked a narrow definition, acronym, or factual question. EVIDENCE may be empty.

RULES:
1. Answer **only** what was asked — nothing else.
2. Prefer **one sentence** (two only if the question has two explicit parts). No ### headings, no bullet lists, no "what stands out", no worked examples, no investing tips.
3. Respect `max_words` in WHAT THE USER WANTS strictly (usually ≤50).
4. Do not mention tools, EVIDENCE, or the pipeline.
5. If you truly do not know, say so in one sentence.
"""

COMPOSE_SYSTEM_FACTS = """ROLE: COMPOSER — one note for an investor
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
    if DISCLAIMER.lower().strip("*") not in text.lower():
        text = text.rstrip() + "\n\n" + DISCLAIMER
    return text


def node_compose(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None
    pack = state.evidence_pack

    # Fast Path: Check for DATA_ONLY Template (skip when concept + compose required)
    if (
        plan.answer_mode == AnswerMode.DATA_ONLY
        and pack is not None
        and not plan.requires_compose
        and not (plan.concept_brief or "").strip()
    ):
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

    fact_brief = ""
    if pack and len(plan.asked_facts or []) >= 2:
        from news_rag.insight.evidence_pack import investor_fact_brief

        fact_brief = investor_fact_brief(pack.data_pack, plan.asked_facts)
    evidence_dict = {"FACTS": fact_brief} if fact_brief else (pack.compact() if pack else {})
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
    from news_rag.insight.planner_policy import horizon_code

    wants["measured_window"] = horizon_code(plan.window_days)
    wants["measured_window_days"] = plan.window_days
    if (plan.presentation_notes or "").strip():
        wants["presentation_notes"] = plan.presentation_notes.strip()
    if plan.sub_queries:
        wants["parts"] = [str(part.get("text") or "").strip() for part in plan.sub_queries if str(part.get("text") or "").strip()]
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

    precise = asks_precise_definition(state.question or "") and not (
        evidence_dict.get("rows") or evidence_dict.get("data_pack")
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
    elif fact_brief:
        wants["max_words"] = max(int(wants.get("max_words") or 0), 450)
        user_content = (
            f"QUESTION:\n{state.question.strip()}\n\n"
            f"WHAT THE USER WANTS:\n{json.dumps(wants, ensure_ascii=False)}\n\n"
            f"FACTS:\n{fact_brief}"
        )
        compose_system = COMPOSE_SYSTEM_FACTS
        max_tokens = 900
    elif precise:
        wants["max_words"] = min(int(wants.get("max_words") or 220), 50)
        wants["style"] = "short_answer"
        user_content = (
            f"QUESTION:\n{state.question.strip()}\n\n"
            f"WHAT THE USER WANTS:\n{json.dumps(wants, ensure_ascii=False)}\n\n"
            f"EVIDENCE:\n{evidence_text}"
        )
        compose_system = COMPOSE_SYSTEM_PRECISE
        max_tokens = 150
    else:
        compose_system = COMPOSE_SYSTEM
        word_budget = int(wants.get("max_words") or plan.max_words or 220)
        max_tokens = max(500, min(2500, word_budget * 4))

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
    if not raw_text:
        state.pipeline_errors.append({"stage": "compose", "tool": "", "message": "empty response"})
        # Fallback: render whatever structured data we have
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
    )
    if news_articles or measured:
        allowed_numbers = cores_in_text(evidence_text) | cores_in_text(state.question or "")
        grounded_text = strip_ungrounded_numbers(raw_text, allowed_numbers)
    else:
        grounded_text = raw_text
    polished_text = strip_media_attribution(grounded_text)
    if news_articles:
        from news_rag.insight.fund_display import clean_news_insight

        polished_text = clean_news_insight(polished_text)
    display_tables = {} if fact_brief else (pack.display_tables if pack else {})
    if display_tables and any(k for k in display_tables if k != "_title"):
        polished_text = stitch_display_tables_into_answer(
            polished_text,
            display_tables,
            question=state.question or "",
        )
    polished_text = strip_news_roundup(polished_text)
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
