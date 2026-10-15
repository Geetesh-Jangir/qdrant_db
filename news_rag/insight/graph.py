"""Plan-driven node graph for the ask pipeline.

        plan ──► resolve ──► fetch ──► measure ──► compose ──► END
          │          │                                  ▲
          └─► reply ◄┘  (out of scope, clarification, nothing to look up)

Each node does one job and returns the NAME of the next node, so the route changes with the plan:
a NAV lookup skips news and analysis, a "why did it fall" question adds holding attribution, an
out-of-scope question ends after one call. Adding a node (for example an analyst) is one function
and one entry in NODES.

Only two nodes call a model: `plan` (small fast model, decides everything) and `compose` (writes
the answer). Everything else is code.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from news_rag.article_pool import sources_from_articles
from news_rag.config import get_settings
from news_rag.insight.brief import QuestionBrief
from news_rag.insight.data_pack import build_data_pack, missing_items, select_news
from news_rag.insight.fund_why import enrich_named_fund_why
from news_rag.insight.gather import EvidenceSet, GatherContext, gather_evidence
from news_rag.insight.plan import Plan, make_plan, plan_to_brief, tools_to_facets
from news_rag.llm_client import call_insight_llm, composer_model, llm_api_key_configured
from news_rag.query_log import QueryLogger
from news_rag.query_analyzer import ADVICE_NOTE

DISCLAIMER = "*For context only — not investment advice.*"
DEFAULT_OUT_OF_SCOPE = (
    "I can help with Indian mutual funds, stocks, sectors and the market. "
    "Ask me about a fund's NAV or returns, what a fund holds, how a sector is doing, "
    "or what is moving the market."
)


class GraphUnavailable(Exception):
    """The planner could not run; the caller should use the older pipeline."""


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

    plan: Plan | None = None
    brief: QuestionBrief | None = None
    evidence: EvidenceSet = field(default_factory=EvidenceSet)
    resolved_funds: list[str] = field(default_factory=list)
    unresolved_funds: list[str] = field(default_factory=list)
    data_pack: dict[str, Any] = field(default_factory=dict)
    news: list[dict[str, Any]] = field(default_factory=list)
    news_grouped: dict[str, Any] = field(default_factory=dict)
    coverage: dict[str, Any] = field(default_factory=dict)
    layer_results: list[dict[str, Any]] = field(default_factory=list)
    targets: list[Any] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    answer: str = ""
    reply_kind: str = "answer"  # answer | out_of_scope | clarify | not_found
    pipeline_errors: list[dict[str, str]] = field(default_factory=list)
    route_reason: str = ""
    trace: list[dict[str, Any]] = field(default_factory=list)


NodeFn = Callable[[GraphState], "str | None"]


@dataclass
class Node:
    name: str
    run: NodeFn
    on_error: str | None = "compose"  # where to go if the node raises; None re-raises
    uses_llm: bool = False


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def node_plan(state: GraphState) -> str | None:
    plan = make_plan(state.question, prior_context=state.prior_context, query_log=state.query_log)
    if plan is None:
        raise GraphUnavailable("planner returned nothing")
    state.plan = plan
    if plan.scope_kind == "out_of_scope":
        state.reply_kind = "out_of_scope"
        state.answer = plan.direct_reply or DEFAULT_OUT_OF_SCOPE
        state.route_reason = "planner marked the question out of scope"
        return "reply"
    if plan.scope_kind == "needs_clarification":
        state.reply_kind = "clarify"
        state.answer = plan.clarification_question or plan.direct_reply or (
            "Could you tell me a little more about what you would like to know?"
        )
        state.route_reason = "planner needs one more detail from the user"
        return "reply"
    state.route_reason = f"{len(plan.tool_calls)} tool(s) planned"
    return "resolve"


def _resolve_funds(plan: Plan, state: GraphState) -> tuple[list[str], list[str]]:
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
        from news_rag.fund_search import lookup_extracted_fund

        # Draw extra candidates once and keep the first ones that have holdings data.
        want = plan.random_fund_count
        candidates = idx.sample_fund_names(want * 3, name_contains=plan.random_fund_name_contains)
        picked: list[str] = []
        for name in candidates:
            try:
                complete = bool((lookup_extracted_fund(name=name)[0] or {}).get("sectors"))
            except Exception:  # noqa: BLE001
                complete = False
            if complete:
                picked.append(name)
            if len(picked) >= want:
                break
        if len(picked) < want:
            picked += [n for n in candidates if n not in picked][: want - len(picked)]
        for name in picked:
            if name not in resolved:
                resolved.append(name)
    return list(dict.fromkeys(resolved)), unresolved


def node_resolve(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None
    funds, unresolved = _resolve_funds(plan, state)
    sector_keys: list[str] = []
    if plan.sectors:
        from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

        sector_keys = get_sector_fund_ranking_index().resolve_sector_keys(plan.sectors)
    state.resolved_funds = funds
    state.unresolved_funds = unresolved
    state.brief = plan_to_brief(plan, sector_keys=sector_keys, funds=funds)

    wanted_funds = bool(plan.funds) or plan.random_fund_count > 0
    if wanted_funds and not funds:
        state.reply_kind = "not_found"
        names = ", ".join(plan.funds) or "that fund"
        state.answer = (
            f"I couldn't find a fund matching {names}. "
            "Please share the full scheme name (for example the AMC and plan) and I'll look it up."
        )
        state.route_reason = "no requested fund could be matched"
        return "reply"
    if not plan.layer1 and not plan.tool_calls:
        state.route_reason = "no tools needed"
        return "compose"
    state.route_reason = (
        f"funds={len(funds)} unresolved={len(unresolved)} sectors={len(sector_keys)}"
    )
    return "layer1"


def _pack_data(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Layer-1 rows grouped by fund when a fund is set, otherwise by tool."""
    funds: dict[str, dict[str, Any]] = {}
    tools: dict[str, Any] = {}
    for row in results:
        if not row.get("ok"):
            continue
        body = {k: v for k, v in (row.get("data") or {}).items() if k not in ("isin", "url") and not str(k).startswith("_")}
        fund = str(row.get("fund") or body.get("fund_name") or "")
        if fund:
            funds.setdefault(fund, {})[row["tool"]] = body
        else:
            tools[row["tool"]] = body
    pack: dict[str, Any] = {}
    if funds:
        pack["funds"] = funds
    pack.update(tools)
    return pack


def node_layer1(state: GraphState) -> str | None:
    from news_rag.insight.layers import _retry_failed, run_layer1

    plan, brief = state.plan, state.brief
    assert plan is not None and brief is not None
    if not plan.layer1 and plan.tool_calls:
        plan.layer1 = [
            {"tool": call["tool"], "args": {}, "required": True, "why": call.get("why", "")}
            for call in plan.tool_calls
        ]
    results = run_layer1(
        plan, state.question, state.resolved_funds, list(brief.sector_keys), query_log=state.query_log
    )
    state.layer_results = _retry_failed(
        plan, results, state.question, state.resolved_funds, list(brief.sector_keys)
    )
    state.data_pack = _pack_data(state.layer_results)
    slow = max(state.layer_results, key=lambda r: float(r.get("elapsed_ms") or 0), default=None)
    state.route_reason = (
        f"tools={len(state.layer_results)} ok={sum(1 for r in state.layer_results if r.get('ok'))} "
        f"slowest={(slow or {}).get('tool', '')}:{round(float((slow or {}).get('elapsed_ms') or 0) / 1000, 2)}s"
    )
    return "expand" if plan.layer2_news else "check"


def node_expand(state: GraphState) -> str | None:
    from news_rag.insight.layers import expand_targets

    plan = state.plan
    assert plan is not None
    state.targets = expand_targets(plan, state.layer_results)
    state.route_reason = f"targets={len(state.targets)}"
    return "layer2" if state.targets else "check"


def node_layer2(state: GraphState) -> str | None:
    from news_rag.insight.news_fanout import grouped_news, search_targets

    market_targets = sum(1 for t in state.targets if t.scope == "market")
    if state.query_log is not None and market_targets:
        state.query_log.write(
            f"MARKET_NEWS parallel_targets={market_targets} "
            f"(batched embed + Qdrant per time window)"
        )
    search_targets(state.targets)
    state.news_grouped = grouped_news(state.targets)
    filled = sum(1 for t in state.targets if t.articles)
    articles = sum(len(t.articles) for t in state.targets)
    state.route_reason = f"targets={len(state.targets)} with_news={filled} articles={articles}"
    return "check"


def node_check(state: GraphState) -> str | None:
    from news_rag.insight.layers import coverage_report, widen_thin

    plan = state.plan
    assert plan is not None
    widened = widen_thin(state.targets) if state.targets else []
    if widened:
        from news_rag.insight.news_fanout import grouped_news

        state.news_grouped = grouped_news(state.targets)
    state.coverage = coverage_report(plan, state.layer_results, state.targets, widened)
    state.route_reason = (
        f"missing_tools={len(state.coverage['missing_tools'])} "
        f"thin_news={len(state.coverage['news_without_articles'])} widened={len(widened)}"
    )
    return "compose"


COMPOSE_SYSTEM = """You write answers for everyday investors in India. You get the question, what the user wants, measured DATA, and sometimes NEWS. The answer should be useful: a person should understand what happened and why.

HOW TO WRITE
- Lead with the answer in the first sentence, using a number from DATA (the fund return, the NAV, or the price). Then explain why, then what it means for someone holding the fund.
- When NEWS is present, that explanation is the body of the answer. Do not stop after the factsheet. Use the substance of the articles in your own words: what happened, to which company or sector, and how that lines up with a number already in DATA (a weight, a return, or a contribution).
- When NEWS is grouped under market with several theme labels, give a short market read: lead with index moves from DATA, then the two or three themes that matter most, each tied to a headline theme (rates, flows, crude, earnings, banks, global risk, etc.).
- Order the explanation as macro, then sector, then holding, then the fund. Each part gets one or two sentences tied to a figure. A contribution row in DATA is the link between a stock's move and the fund.
- Shape: a short opening, then markdown sections with ## headings (How it has done, Why, What it means). Put top holdings or sectors in a small markdown table when DATA has them. A lookup with no NEWS stays a short direct answer.
- Use plain, simple words and short sentences. Explain any finance term in a few words the first time.
- Compare funds only when asked.
- Leave out anything that is not available. Mention a gap only when the user asked for that exact thing.
- Finish every sentence and every row. Use the word budget. When NEWS is present, spend it on the explanation, not on repeating the NAV.

NUMBERS
- Copy numbers from DATA or NEWS exactly as written. Do not calculate, estimate, average, add, subtract, convert or round a new figure. If fund_attribution already gives a contribution, quote that figure. If a needed figure is absent, describe the link in words and leave the new number out.
- Say which period a return covers whenever you give one.

NEVER
- Mention DATA, NEWS, MISSING, the plan, tools, systems, IDs, or how the information was collected. Never write phrases like "the data I have", "in the data", "not provided" or "the news provided". Say "I couldn't find" instead. Never ask the user for data.
- Name news outlets or give article dates.
- Give buy, sell or hold advice, price targets, or predictions stated as fact. If the user asked for advice, say you cannot recommend, then share what the data shows.
- Invent funds, companies, sectors or figures that are not in DATA or NEWS.
- Guess. COVERAGE lists tools that failed, entities with no recent news, and things we do not track (such as expense ratio). Mention each gap in one plain sentence and do not suggest other websites.

End with this exact last line: *For context only — not investment advice.*"""


def _public_news(grouped: dict[str, Any], *, budget: int = 24000) -> dict[str, Any]:
    """Drop urls and share the character budget across entities."""
    flat: list[tuple[str, str, dict[str, Any]]] = []
    for scope, entities in (grouped or {}).items():
        if not isinstance(entities, dict):
            continue
        for entity, rows in entities.items():
            for row in rows or []:
                if isinstance(row, dict):
                    flat.append((scope, entity, row))
    if not flat:
        return {}
    each = max(180, budget // len(flat))
    out: dict[str, dict[str, list[dict[str, str]]]] = {}
    for scope, entity, row in flat:
        text = str(row.get("text") or "")[:each]
        out.setdefault(scope, {}).setdefault(entity, []).append(
            {"headline": str(row.get("headline") or ""), "text": text}
        )
    return out


def compose_user_content(state: GraphState) -> str:
    plan = state.plan
    assert plan is not None
    wants = {
        "goal": plan.goal,
        "parts_to_answer": [s["text"] for s in plan.sub_queries],
        "time_frame": plan.window_label,
        "style": plan.style,
        "max_words": plan.max_words,
        "lead_with": plan.lead_with,
        "format_notes": plan.presentation_notes,
        "user_asked_for_advice": plan.asks_for_advice,
    }
    has_news = bool(state.news_grouped)
    if has_news:
        wants["max_words"] = max(int(plan.max_words or 0), 480)
        wants["must_explain"] = "Use the NEWS to explain the DATA numbers. Do not stop at NAV and returns."
    wants = {k: v for k, v in wants.items() if v not in ("", [], None, False)}
    parts = [
        "QUESTION:\n" + state.question.strip(),
        "WHAT THE USER WANTS:\n" + json.dumps(wants, ensure_ascii=False, separators=(",", ":")),
        "DATA:\n"
        + (
            json.dumps(state.data_pack, ensure_ascii=False, separators=(",", ":"))
            if state.data_pack
            else "none"
        ),
    ]
    news = _public_news(state.news_grouped)
    if news:
        parts.append("NEWS:\n" + json.dumps(news, ensure_ascii=False, separators=(",", ":")))
    coverage = dict(state.coverage or {})
    if state.unresolved_funds:
        coverage["funds_not_found"] = list(state.unresolved_funds)
    if any(coverage.get(k) for k in ("missing_tools", "news_without_articles", "not_supported", "funds_not_found")):
        parts.append("COVERAGE:\n" + json.dumps(coverage, ensure_ascii=False, separators=(",", ":")))
    return "\n\n".join(parts)


def _clean_answer(text: str) -> str:
    text = re.sub(r"```(?:json|markdown)?", "", text or "").strip()
    if DISCLAIMER.lower().strip("*") not in text.lower():
        text = text.rstrip() + "\n\n" + DISCLAIMER
    return text


def node_compose(state: GraphState) -> str | None:
    plan = state.plan
    assert plan is not None
    settings = get_settings()
    if not llm_api_key_configured(settings):
        raise GraphUnavailable("no llm key for compose")
    user = compose_user_content(state)
    word_budget = plan.max_words
    if state.news_grouped:
        word_budget = max(word_budget, 480)
    max_tokens = max(1200, min(4500, int(word_budget * 5)))
    res = call_insight_llm(
        system_prompt=COMPOSE_SYSTEM,
        user_content=user,
        query_log=state.query_log,
        model_override=composer_model(settings),
        max_tokens=max_tokens,
        temperature=0.2,
        stage="composer",
    )
    text = (res.raw_text or "").strip() if res else ""
    if len(text) < 20:
        state.pipeline_errors.append({"stage": "compose", "tool": "", "message": "empty answer"})
        raise RuntimeError("composer returned no text")
    state.answer = _clean_answer(text)
    state.route_reason = f"chars={len(state.answer)}"
    return None


def node_reply(state: GraphState) -> str | None:
    """Answers that need no data: out of scope, a question back to the user, nothing to look up."""
    state.route_reason = state.reply_kind
    return None


NODES: dict[str, Node] = {
    "plan": Node("plan", node_plan, on_error=None, uses_llm=True),
    "resolve": Node("resolve", node_resolve, on_error="compose"),
    "layer1": Node("layer1", node_layer1, on_error="compose"),
    "expand": Node("expand", node_expand, on_error="check"),
    "layer2": Node("layer2", node_layer2, on_error="check"),
    "check": Node("check", node_check, on_error="compose"),
    "compose": Node("compose", node_compose, on_error=None, uses_llm=True),
    "reply": Node("reply", node_reply, on_error=None),
}
ENTRY = "plan"
MAX_HOPS = 10


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


def run_graph(state: GraphState) -> GraphState:
    log = state.query_log
    name: str | None = ENTRY
    hops = 0
    while name and hops < MAX_HOPS:
        hops += 1
        node = NODES[name]
        if log is not None:
            log.log_pipeline(node.name, "start")
        t0 = time.perf_counter()
        nxt: str | None
        error = ""
        try:
            nxt = node.run(state)
        except GraphUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001 - one node must not sink the answer
            error = f"{type(exc).__name__}: {exc}"[:240]
            state.pipeline_errors.append({"stage": node.name, "tool": "", "message": error})
            if node.on_error is None:
                if log is not None:
                    log.log_pipeline(node.name, "error", seconds=round(time.perf_counter() - t0, 3), error=error)
                raise
            nxt = node.on_error
            state.route_reason = f"{node.name} failed, continuing"
        seconds = round(time.perf_counter() - t0, 3)
        state.trace.append(
            {"node": node.name, "seconds": seconds, "next": nxt, "why": state.route_reason, "error": error}
        )
        if log is not None:
            log.log_pipeline(
                node.name,
                "done",
                seconds=seconds,
                next=nxt or "end",
                why=state.route_reason,
                llm=node.uses_llm,
            )
        name = nxt
    return state


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


def build_result(state: GraphState) -> dict[str, Any]:
    plan = state.plan
    brief = state.brief
    evidence = state.evidence
    shown = [
        {"url": art.get("url"), "title": art.get("headline")}
        for target in state.targets
        for art in (target.articles or [])
        if art.get("url")
    ]
    insight = state.answer
    refused = state.reply_kind == "out_of_scope"
    headline = next((ln.strip(" #*") for ln in insight.splitlines() if ln.strip()), insight[:120])
    terms = list(dict.fromkeys((state.resolved_funds + (plan.sectors if plan else []))))[:8]
    research = {
        "pipeline": "graph",
        "goal": plan.goal if plan else "",
        "plan": plan.summary() if plan else {},
        "evidence_needs": brief.evidence_needs if brief else [],
        "ledger": [{"facet": e.facet, "status": e.status, "reason": e.reason} for e in evidence.ledger],
        "verify_gaps": [],
        "retry_facets": [],
        "tool_runs": [
            {"tool": row.get("tool"), "ok": row.get("ok"), "elapsed_ms": row.get("elapsed_ms"), "fund": row.get("fund")}
            for row in state.layer_results
        ] or evidence.tool_runs,
        "nodes": state.trace,
    }
    return {
        "insight": insight,
        "insight_summary": headline,
        "insight_headline": headline,
        "insight_narrative": insight,
        "insight_closing_summary": "",
        "insight_bullets": [],
        "highlight_terms": terms,
        "sources": sources_from_articles(shown),
        "retrieval_window": {
            "window_days": plan.window_days if plan else None,
            "window_label": plan.window_label if plan else "",
        },
        "intent": "insight_v2",
        "insight_source": "insight_graph",
        "outcome": "refused" if refused else ("ok" if insight.strip() else "no_data"),
        "refused": refused,
        "sections": [{"id": "A1", "style": "unified_answer", "text": insight, "headline": headline}],
        "sub_queries": [{"text": s["text"], "kind": "describe"} for s in (plan.sub_queries if plan else [])],
        "pipeline_errors": state.pipeline_errors,
        "output_score": None,
        "output_scores": {},
        "advice_note": ADVICE_NOTE,
        "research": research,
        "answer_trace": {"mode": "graph", "route": [t["node"] for t in state.trace]},
    }


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
) -> dict[str, Any]:
    """Run the graph. Raises GraphUnavailable when the caller should use the older pipeline."""
    state = GraphState(
        question=(question or "").strip(),
        date_from=date_from,
        date_to=date_to,
        min_impact=min_impact,
        source=source,
        direction=direction,
        query_log=query_log,
        prior_context=prior_context,
    )
    if query_log is not None:
        query_log.log_pipeline("insight_graph", "start", nodes=",".join(NODES))
    run_graph(state)
    return build_result(state)
