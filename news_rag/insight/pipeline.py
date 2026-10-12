"""Orchestrate insight pipeline v2."""

from __future__ import annotations

import time
from typing import Any

from news_rag.article_pool import sources_from_articles
from news_rag.config import get_settings
from news_rag.guardrails import check_guardrails
from news_rag.insight.blocks.compute import compute_findings
from news_rag.insight.brief import build_question_brief
from news_rag.insight.gather import GatherContext, gather_evidence
from news_rag.insight.interpret import compose_from_findings
from news_rag.insight.findings import Findings
from news_rag.insight.verify import verify_answer
from news_rag.llm_client import llm_api_key_configured
from news_rag.output_judge import judge_answer
from news_rag.query_analyzer import ADVICE_NOTE

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
            interpret_llm=bool(getattr(settings, "insight_use_llm_interpret", False)),
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
    if query_log is not None:
        query_log.log_pipeline("gather", "done", seconds=round(time.perf_counter() - t0, 3))

    t0 = time.perf_counter()
    if query_log is not None:
        query_log.log_pipeline("compute", "start")
    findings = compute_findings(brief, evidence)
    if query_log is not None:
        sec = findings.sector
        query_log.log_compute(
            funds=len(findings.funds),
            articles=len(evidence.articles),
            news_direction=sec.news_direction if sec else "",
            news_insights=len(sec.news_insights) if sec else 0,
            index_return_pct=sec.index_return_pct if sec else None,
            seconds=round(time.perf_counter() - t0, 3),
        )
        query_log.log_pipeline("compute", "done", seconds=round(time.perf_counter() - t0, 3))

    t0 = time.perf_counter()
    if query_log is not None:
        query_log.log_pipeline("interpret", "start")
    composed = compose_from_findings(q, brief, findings, evidence, query_log=query_log)
    if query_log is not None:
        mode = (composed.answer_trace or {}).get("mode", "structured")
        query_log.log_interpret(mode=mode, bullets=len(composed.bullets), chars=len(composed.display or ""))
        query_log.log_pipeline("interpret", "done", seconds=round(time.perf_counter() - t0, 3))

    verify = verify_answer(brief, findings, evidence, insight_text=composed.display)
    if query_log is not None:
        query_log.log_verify(passed=verify.passed, gaps=verify.gaps, retry_facets=verify.retry_facets)
    if not verify.passed and verify.retry_facets:
        if query_log is not None:
            query_log.log_pipeline("gather", "retry", facets=verify.retry_facets)
        extra_needs = list(dict.fromkeys(brief.evidence_needs + verify.retry_facets))
        brief.evidence_needs = extra_needs
        gctx.brief = brief
        evidence = gather_evidence(gctx, max_rounds=1)
        findings = compute_findings(brief, evidence)
        composed = compose_from_findings(q, brief, findings, evidence, query_log=query_log)

    insight = composed.display or _build_insight_text(
        composed.headline, composed.narrative, composed.bullets, composed.closing_summary
    )
    if query_log is not None:
        query_log.log_pipeline("judge", "start", purpose="Score answer quality (telemetry only)")
    jr = judge_answer(q, insight, findings.evidence_text[:8000], query_log=query_log)
    if query_log is not None:
        query_log.log_pipeline(
            "judge",
            "done",
            passed=jr.passed,
            usable=jr.usable,
            scores=jr.scores,
        )
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
