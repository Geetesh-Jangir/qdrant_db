"""Orchestrate insight pipeline v2."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator

from news_rag.article_pool import sources_from_articles
from news_rag.config import get_settings
from news_rag.guardrails import check_guardrails
from news_rag.insight.blocks.compute import compute_findings
from news_rag.insight.brief import QuestionBrief, build_question_brief
from news_rag.insight.findings import Findings
from news_rag.insight.fund_why import enrich_named_fund_why
from news_rag.insight.gather import EvidenceItem, EvidenceSet, GatherContext, gather_evidence
from news_rag.insight.analyst import run_insight_analyst
from news_rag.insight.interpret import _composer_user_content, _facts, compose_from_findings
from news_rag.insight.news_reader import read_news
from news_rag.insight.verify import verify_answer
from news_rag.llm_client import (
    composer_model,
    llm_api_key_configured,
    stream_text_llm,
)
from news_rag.output_judge import JudgeResult
# from news_rag.output_judge import judge_answer  # disabled temporarily
from news_rag.prompts import build_composer_prompt
from news_rag.query_analyzer import ADVICE_NOTE
from news_rag.query_log import attach_query_log_meta

if True:
    from news_rag.query_log import QueryLogger


def _highlight_terms(findings: Findings) -> list[str]:
    terms: list[str] = []
    if findings.sector and findings.sector.sector_label:
        terms.append(findings.sector.sector_label)
    for f in findings.funds[:6]:
        terms.append(f.fund_name.split(" - ")[0].strip())
    return terms[:10]


def _build_insight_text(headline: str, narrative: str, bullets: list[str], closing: str) -> str:
    parts = [p for p in (headline, narrative) if (p or "").strip()]
    if bullets:
        parts.append("\n".join(f"• {b}" for b in bullets))
    if (closing or "").strip():
        parts.append(closing.strip())
    return "\n\n".join(parts).strip()


def run_until_compose(
    question: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
    prior_brief_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    q = (question or "").strip()
    pipeline_errors: list[dict[str, str]] = []
    settings = get_settings()

    guard = check_guardrails(q)
    if guard.outcome == "refuse_out_of_domain":
        msg = guard.message
        return {
            "insight": msg,
            "insight_summary": msg,
            "insight_bullets": [],
            "sources": [],
            "intent": "general",
            "insight_source": "insight_v2",
            "outcome": "refused",
            "refused": True,
            "sections": [],
            "sub_queries": [],
            "pipeline_errors": pipeline_errors,
            "output_score": None,
            "output_scores": {},
            "research": {"pipeline": "v2", "declined": True},
        }

    if query_log is not None:
        query_log.log_pipeline(
            "insight_v2",
            "start",
            interpret_llm=bool(getattr(settings, "insight_use_llm_interpret", True)),
            news_reader_llm=bool(getattr(settings, "insight_use_llm_news_reader", True)),
            fan_out_cap=int(getattr(settings, "insight_fan_out_cap", 8)),
        )

    if not llm_api_key_configured(settings):
        pipeline_errors.append({"stage": "config", "tool": "", "message": "LLM API key not configured."})

    t0 = time.perf_counter()
    if query_log is not None:
        query_log.log_pipeline("brief", "start")
    brief = build_question_brief(q, prior_context=prior_brief_context, query_log=query_log)
    if query_log is not None:
        query_log.log_pipeline(
            "brief",
            "done",
            seconds=round(time.perf_counter() - t0, 3),
            source=brief.raw.get("source", "llm"),
        )

    gctx = GatherContext(
        question=q,
        brief=brief,
        date_from=date_from,
        date_to=date_to,
        min_impact=min_impact,
        source=source,
        direction=direction,
        fan_out_cap=int(getattr(settings, "insight_fan_out_cap", 8)),
        query_log=query_log,
    )
    t0 = time.perf_counter()
    if query_log is not None:
        query_log.log_pipeline("gather", "start", evidence_needs=brief.evidence_needs)
    evidence = gather_evidence(gctx)
    evidence = enrich_named_fund_why(q, brief, evidence, query_log=query_log)
    if query_log is not None:
        query_log.log_pipeline("gather", "done", seconds=round(time.perf_counter() - t0, 3))

    t0 = time.perf_counter()
    if query_log is not None:
        query_log.log_pipeline("news_reader", "start", articles=len(evidence.articles))
    try:
        news_read = read_news(q, brief, evidence.articles, query_log=query_log)
    except Exception as exc:  # noqa: BLE001 - the reader must never sink the answer
        news_read = None
        pipeline_errors.append({"stage": "news_reader", "tool": "", "message": str(exc)[:200]})
    if query_log is not None:
        query_log.log_pipeline(
            "news_reader",
            "done",
            seconds=round(time.perf_counter() - t0, 3),
            mode=news_read.mode if news_read else "error",
            claims=len(news_read.claims) if news_read else 0,
        )

    t0 = time.perf_counter()
    if query_log is not None:
        query_log.log_pipeline("compute", "start")
    findings = compute_findings(brief, evidence, news_read)

    # Verify-driven repair pass: retry gather for named fund if compute yielded empty funds
    if brief.funds and not findings.funds:
        if query_log is not None:
            query_log.write(f"REPAIR: missing findings.funds for {brief.funds}, retrying gather")
        from news_rag.fund_search import get_fund_index
        idx = get_fund_index()
        for fund_name in brief.funds:
            detail, _, _ = idx.lookup_extracted_fund(name=fund_name)
            if not detail:
                hits = idx.search(fund_name, limit=2)
                if hits:
                    detail = hits[0]
            if detail and detail.get("isin"):
                isin = str(detail["isin"])
                from news_rag.tools.fund_composition import run as run_comp
                from news_rag.tools.fund_return_series import run as run_ret
                comp_res = run_comp({"isin": isin, "window_days": brief.window_days})
                if comp_res.get("ok"):
                    evidence.items.append(
                        EvidenceItem("fund_composition", "fund_composition", isin, comp_res.get("data", {}))
                    )
                ret_res = run_ret({"isin": isin, "window_days": brief.window_days})
                if ret_res.get("ok"):
                    evidence.items.append(
                        EvidenceItem("return_series", "fund_return_series", isin, ret_res.get("data", {}))
                    )
        evidence = enrich_named_fund_why(q, brief, evidence, query_log=query_log)
        findings = compute_findings(brief, evidence, news_read)

    if query_log is not None:
        sec = findings.sector
        query_log.log_compute(
            funds=len(findings.funds),
            articles=len(evidence.articles),
            news_direction=sec.news_direction if sec else "",
            news_claims=len(sec.claims) if sec else 0,
            fund_alignment={f.isin or f.fund_name[:20]: f.alignment for f in findings.funds},
            fund_tilt={f.isin or f.fund_name[:20]: f.news_tilt for f in findings.funds},
            index_return_pct=sec.index_return_pct if sec else None,
            seconds=round(time.perf_counter() - t0, 3),
        )
        query_log.log_pipeline("compute", "done", seconds=round(time.perf_counter() - t0, 3))

    analysis_brief = run_insight_analyst(
        q, brief, findings, evidence, query_log=query_log
    )
    if query_log is not None and analysis_brief:
        query_log.write("ANALYST ok takeaways=" + str(len(analysis_brief.get("net_takeaways") or [])))

    return {
        "question": q,
        "brief": brief,
        "evidence": evidence,
        "news_read": news_read,
        "findings": findings,
        "analysis_brief": analysis_brief,
        "pipeline_errors": pipeline_errors,
        "refused": False,
    }


def compose(
    question: str,
    brief: QuestionBrief,
    evidence: EvidenceSet,
    findings: Findings,
    news_read: Any = None,
    pipeline_errors: list[dict[str, str]] | None = None,
    query_log: QueryLogger | None = None,
    analysis_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    if query_log is not None:
        query_log.log_pipeline("interpret", "start")
    if pipeline_errors is None:
        pipeline_errors = []
    composed = compose_from_findings(
        question,
        brief,
        findings,
        evidence,
        query_log=query_log,
        pipeline_errors=pipeline_errors,
        analysis_brief=analysis_brief,
    )
    if query_log is not None:
        mode = (composed.answer_trace or {}).get("mode", "structured")
        query_log.log_interpret(mode=mode, bullets=len(composed.bullets), chars=len(composed.display or ""))
        query_log.log_pipeline("interpret", "done", seconds=round(time.perf_counter() - t0, 3))

    verify = verify_answer(brief, findings, evidence, insight_text=composed.display, question=question)
    if query_log is not None:
        query_log.log_verify(passed=verify.passed, gaps=verify.gaps, retry_facets=verify.retry_facets)
    insight = composed.display or _build_insight_text(
        composed.headline, composed.narrative, composed.bullets, composed.closing_summary
    )
    # Judge LLM disabled temporarily (telemetry only; does not block the user answer).
    # if query_log is not None:
    #     query_log.log_pipeline("judge", "start", purpose="Score answer quality (telemetry only)")
    # jr = judge_answer(question, insight, findings.evidence_text[:8000], query_log=query_log)
    # if query_log is not None:
    #     query_log.log_pipeline(
    #         "judge",
    #         "done",
    #         passed=jr.passed,
    #         usable=jr.usable,
    #         scores=jr.scores,
    #     )
    if query_log is not None:
        query_log.log_pipeline("judge", "skip", reason="judge_llm_disabled")
    jr = JudgeResult(passed=True, scores={}, attempt=0, raw={"disabled": True}, usable=False)
    scores = jr.scores or {}
    output_score = None
    if scores:
        vals = [scores.get(k, 0) for k in ("answers_query", "grounded", "no_advice") if k in scores]
        if vals:
            output_score = round(sum(vals) / len(vals), 3)

    articles = evidence.articles
    research = {
        "pipeline": "v2",
        "goal": brief.goal,
        "evidence_needs": brief.evidence_needs,
        "ledger": [{"facet": e.facet, "status": e.status, "reason": e.reason} for e in evidence.ledger],
        "findings": findings.to_dict(),
        "news_read": news_read.to_dict() if news_read else None,
        "verify_gaps": verify.gaps,
        "tool_runs": evidence.tool_runs,
    }

    outcome = "ok" if (insight or "").strip() else "no_data"
    return {
        "insight": insight,
        "insight_summary": composed.headline or insight[:280],
        "insight_headline": composed.headline,
        "insight_narrative": composed.narrative,
        "insight_closing_summary": composed.closing_summary,
        "insight_bullets": composed.bullets,
        "highlight_terms": _highlight_terms(findings),
        "sources": sources_from_articles(articles),
        "retrieval_window": {"window_days": brief.window_days, "window_label": brief.window_label},
        "intent": "insight_v2",
        "insight_source": "insight_v2",
        "outcome": outcome,
        "refused": False,
        "sections": [
            {
                "id": "A1",
                "style": "unified_answer",
                "text": insight,
                "headline": composed.headline,
                "narrative": composed.narrative,
                "closing_summary": composed.closing_summary,
                "bullets": composed.bullets,
            }
        ],
        "sub_queries": [{"text": a.text, "kind": a.kind} for a in brief.sub_asks],
        "pipeline_errors": pipeline_errors,
        "output_score": output_score,
        "output_scores": scores,
        "advice_note": ADVICE_NOTE,
        "research": research,
        "answer_trace": composed.answer_trace,
    }


def run_insight_pipeline(
    question: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
    prior_brief_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = run_until_compose(
        question,
        date_from=date_from,
        date_to=date_to,
        min_impact=min_impact,
        source=source,
        direction=direction,
        query_log=query_log,
        prior_brief_context=prior_brief_context,
    )
    if state.get("refused"):
        return state

    return compose(
        question=state["question"],
        brief=state["brief"],
        evidence=state["evidence"],
        findings=state["findings"],
        news_read=state.get("news_read"),
        pipeline_errors=state.get("pipeline_errors"),
        query_log=query_log,
        analysis_brief=state.get("analysis_brief"),
    )


async def stream_insight_pipeline(
    question: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
    prior_brief_context: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    try:
        yield f"event: status\ndata: {json.dumps({'stage': 'planning', 'message': 'Analyzing question...'})}\n\n"
        await asyncio.sleep(0)

        state = run_until_compose(
            question,
            date_from=date_from,
            date_to=date_to,
            min_impact=min_impact,
            source=source,
            direction=direction,
            query_log=query_log,
            prior_brief_context=prior_brief_context,
        )
        if state.get("refused"):
            if query_log is not None:
                meta = query_log.finish_from_ask_result(state, question=question)
                attach_query_log_meta(state, meta)
            yield f"event: done\ndata: {json.dumps(state)}\n\n"
            return

        brief = state["brief"]
        evidence = state["evidence"]
        findings = state["findings"]
        news_read = state.get("news_read")
        pipeline_errors = state.get("pipeline_errors", [])
        analysis_brief = state.get("analysis_brief")

        yield f"event: status\ndata: {json.dumps({'stage': 'gathering', 'message': 'Retrieving holdings, returns, and news...'})}\n\n"
        await asyncio.sleep(0)

        yield f"event: status\ndata: {json.dumps({'stage': 'news_reading', 'message': 'Synthesizing market developments...'})}\n\n"
        await asyncio.sleep(0)

        yield f"event: status\ndata: {json.dumps({'stage': 'composing', 'message': 'Drafting verified insight...'})}\n\n"
        await asyncio.sleep(0)

        settings = get_settings()
        if llm_api_key_configured(settings) and not (brief.funds and not findings.funds):
            packet = _facts(question, brief, findings, evidence)
            prompt = build_composer_prompt()
            user_content = _composer_user_content(packet, analysis_brief)
            try:
                for chunk in stream_text_llm(
                    system_prompt=prompt,
                    user_content=user_content,
                    model_override=composer_model(settings),
                    max_tokens=2500,
                    temperature=0.2,
                    query_log=query_log,
                ):
                    if chunk:
                        yield f"event: delta\ndata: {json.dumps({'text': chunk})}\n\n"
                        await asyncio.sleep(0)
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                if query_log is not None:
                    query_log.write(f"STREAM_COMPOSE error={msg}")
                pipeline_errors.append(
                    {"stage": "stream_compose", "tool": "", "message": msg[:500]}
                )

        full_res = compose(
            question=question,
            brief=brief,
            evidence=evidence,
            findings=findings,
            news_read=news_read,
            pipeline_errors=pipeline_errors,
            query_log=query_log,
            analysis_brief=analysis_brief,
        )
        if query_log is not None:
            meta = query_log.finish_from_ask_result(full_res, question=question)
            attach_query_log_meta(full_res, meta)
        yield f"event: done\ndata: {json.dumps(full_res)}\n\n"
    except Exception as exc:  # noqa: BLE001
        if query_log is not None:
            query_log.log_error("stream", str(exc))
            query_log.finish(outcome="error", article_count=0)
        yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"
