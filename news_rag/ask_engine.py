"""LLM-only ask pipeline: plan → resolve names → parallel tools → digests → compose → score."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from news_rag.article_pool import collect_bundle_articles, sources_from_articles
from news_rag.ask_agent import run_research_agent
from news_rag.ask_composer import compose_final_answer
from news_rag.ask_plan import AskPlan
from news_rag.config import get_settings
from news_rag.json_util import safe_json_dumps
from news_rag.output_judge import judge_answer
from news_rag.market_pulse import clustered_macro_data_from_bundle
from news_rag.query_analyzer import ADVICE_NOTE

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger


def _build_insight_text(
    headline: str,
    narrative: str,
    bullets: list[str],
    closing_summary: str = "",
) -> str:
    parts = [p for p in (headline, narrative) if (p or "").strip()]
    if bullets:
        parts.append("\n".join(f"• {b}" for b in bullets))
    if (closing_summary or "").strip():
        parts.append(closing_summary.strip())
    return "\n\n".join(parts).strip()


def _all_articles(bundle) -> list[dict]:
    return collect_bundle_articles(bundle)


def _sources_from_articles(articles: list[dict]) -> list[dict]:
    return sources_from_articles(articles)


def _retrieval_window_meta(bundle) -> dict[str, Any] | None:
    pulse = clustered_macro_data_from_bundle(bundle)
    if not pulse:
        return None
    return {
        "window_days": pulse.get("window_days"),
        "window_label": pulse.get("window_label"),
        "published_from": pulse.get("published_from"),
        "published_to": pulse.get("published_to"),
    }


def _intent_from_plan(plan: AskPlan) -> str:
    tools = {t.tool for t in plan.tools}
    if "fund_nav" in tools:
        return "fund_nav"
    if "fund_top_stocks" in tools or "fund_top_sectors" in tools:
        return "fund_holdings"
    if "common_market_news" in tools or "market_pulse" in tools:
        return "market_pulse"
    if "macro_news_enhanced" in tools:
        return "macro"
    if any(t in tools for t in ("holdings_news", "sector_news", "macro_news")):
        return "general"
    return "general"


def run_ask_engine(
    question: str,
    *,
    date_from: str | None = None,
    date_to: str | None = None,
    min_impact: int | None = None,
    source: str | None = None,
    direction: str | None = None,
    query_log: QueryLogger | None = None,
) -> dict[str, Any]:
    q = (question or "").strip()
    pipeline_errors: list[dict[str, str]] = []

    if query_log is not None:
        query_log.write(f"QUESTION: {q[:500]}")

    try:
        run = run_research_agent(
            q,
            date_from=date_from,
            date_to=date_to,
            min_impact=min_impact,
            source=source,
            direction=direction,
            query_log=query_log,
        )
    except Exception as exc:
        if query_log is not None:
            query_log.write(f"AGENT_EXCEPTION {exc}")
        pipeline_errors.append({"stage": "agent", "tool": "", "message": str(exc)})
        return _error_response(q, pipeline_errors, query_log)

    plan: AskPlan = run.plan
    if run.declined or plan.decline_entirely:
        msg = run.decline_message or plan.decline_message or "This question is outside our financial data scope."
        if query_log is not None:
            query_log.write(f"AGENT decline_entirely message={msg[:200]}")
        return {
            "insight": msg,
            "insight_summary": msg,
            "insight_bullets": [],
            "sources": [],
            "intent": "general",
            "insight_source": "agent",
            "outcome": "refused",
            "refused": True,
            "sections": [],
            "sub_queries": [],
            "pipeline_errors": pipeline_errors,
            "output_score": None,
            "output_scores": {},
            "research": run.research,
        }

    if plan.declined_parts and query_log is not None:
        query_log.write(f"AGENT declined_parts={plan.declined_parts}")

    bundle = run.bundle
    for pe in bundle.pipeline_errors:
        pipeline_errors.append({"stage": pe.stage, "tool": pe.tool, "message": pe.message})

    if run.ambiguous or bundle.names.ambiguous:
        close = bundle.names.close_matches or []
        msg = (
            f"Your query matched multiple funds: {', '.join(close[:5])}. "
            "Please specify the full name or ISIN."
        )
        return {
            "insight": msg,
            "insight_summary": msg,
            "insight_bullets": [],
            "sources": [],
            "intent": "fund_nav",
            "insight_source": "ask_engine",
            "outcome": "clarification",
            "refused": False,
            "sections": [{"id": "A1", "style": "clarification", "text": msg, "bullets": []}],
            "sub_queries": [{"text": plan.answer_parts}],
            "pipeline_errors": pipeline_errors,
            "output_score": None,
            "output_scores": {},
            "fund_candidates": close[:8],
            "research": run.research,
        }

    composed = compose_final_answer(
        q,
        plan,
        bundle,
        [],
        holdings_market=None,
        query_log=query_log,
    )
    if composed.error:
        pipeline_errors.append({"stage": "composer", "tool": "", "message": composed.error})

    headline = composed.headline or composed.summary
    narrative = composed.narrative or ""
    closing = composed.closing_summary or ""
    bullets = list(composed.bullets)
    insight = composed.display or _build_insight_text(headline, narrative, bullets, closing)

    sections = [
        {
            "id": "A1",
            "style": "unified_answer",
            "text": insight,
            "headline": headline,
            "narrative": narrative,
            "closing_summary": closing,
            "bullets": bullets,
            "summary": headline,
            "highlight_terms": composed.highlight_terms,
        }
    ]

    context_summary = safe_json_dumps(
        {"plan": plan.answer_parts, "tools": list(bundle.tool_results.keys())},
        limit=8000,
    )
    jr = judge_answer(q, insight, context_summary, query_log=query_log)
    scores = jr.scores or {}
    grounded = scores.get("grounded")
    judge_usable = bool(getattr(jr, "usable", True))
    if (
        (insight or "").strip()
        and judge_usable
        and grounded is not None
        and float(grounded) < get_settings().judge_min_score
    ):
        if query_log is not None:
            query_log.write(f"JUDGE ungrounded={grounded} retry_once=true")
        note = "The draft was not grounded in the retrieved evidence. Fetch the missing facts, then stop."
        run = run_research_agent(
            q,
            date_from=date_from,
            date_to=date_to,
            min_impact=min_impact,
            source=source,
            direction=direction,
            query_log=query_log,
            prior=run,
            judge_note=note,
        )
        plan = run.plan
        bundle = run.bundle
        plan.judge_note = note
        for pe in bundle.pipeline_errors:
            pipeline_errors.append({"stage": pe.stage, "tool": pe.tool, "message": pe.message})
        composed = compose_final_answer(
            q,
            plan,
            bundle,
            [],
            holdings_market=None,
            query_log=query_log,
        )
        headline = composed.headline or composed.summary
        narrative = composed.narrative or ""
        closing = composed.closing_summary or ""
        bullets = list(composed.bullets)
        insight = composed.display or _build_insight_text(headline, narrative, bullets, closing)
        sections = [
            {
                "id": "A1",
                "style": "unified_answer",
                "text": insight,
                "headline": headline,
                "narrative": narrative,
                "closing_summary": closing,
                "bullets": bullets,
                "summary": headline,
                "highlight_terms": composed.highlight_terms,
            }
        ]
        context_summary = safe_json_dumps(
            {"plan": plan.answer_parts, "tools": list(bundle.tool_results.keys())},
            limit=8000,
        )
        jr = judge_answer(q, insight, context_summary, query_log=query_log)
        scores = jr.scores or {}
    output_score = None
    if scores:
        vals = [scores.get(k, 0) for k in ("answers_query", "grounded", "no_advice") if k in scores]
        if vals:
            output_score = round(sum(vals) / len(vals), 3)

    if query_log is not None:
        query_log.write(f"JUDGE display_only scores={scores} aggregate={output_score}")
        query_log.log_stage("output_score", scores=scores, aggregate=output_score, passed=jr.passed)

    all_articles = _all_articles(bundle)
    if query_log is not None:
        query_log.write(f"SOURCES_POOL articles={len(all_articles)} with_url={sum(1 for a in all_articles if a.get('url'))}")
    outcome = "ok" if (insight or "").strip() else "no_data"
    if not all_articles and (insight or "").strip():
        outcome = "no_data"

    result: dict[str, Any] = {
        "insight": insight,
        "insight_summary": headline or composed.summary or insight,
        "insight_headline": headline,
        "insight_narrative": narrative,
        "insight_closing_summary": closing,
        "insight_bullets": bullets,
        "highlight_terms": composed.highlight_terms,
        "sources": _sources_from_articles(all_articles),
        "retrieval_window": _retrieval_window_meta(bundle),
        "intent": _intent_from_plan(plan),
        "insight_source": "ask_engine",
        "outcome": outcome,
        "refused": False,
        "sections": sections,
        "sub_queries": [{"text": plan.answer_parts, "declined": plan.declined_parts}],
        "pipeline_errors": pipeline_errors,
        "output_score": output_score,
        "output_scores": scores,
        "advice_note": ADVICE_NOTE if plan.declined_parts else "",
        "research": run.research,
        "answer_trace": composed.answer_trace(),
    }
    if query_log is not None:
        query_log.write(f"RESULT outcome={outcome} errors={len(pipeline_errors)}")
        query_log.log_insight_output(
            insight_source="ask_engine",
            char_count=len(insight or ""),
            preview=(insight or "")[:500],
        )
    return result


def _error_response(
    question: str,
    pipeline_errors: list[dict[str, str]],
    query_log: QueryLogger | None,
) -> dict[str, Any]:
    msg = pipeline_errors[-1]["message"] if pipeline_errors else "Ask pipeline failed."
    if query_log is not None:
        query_log.write(f"RESULT outcome=error {msg}")
    return {
        "insight": msg,
        "insight_summary": msg,
        "insight_bullets": [],
        "sources": [],
        "intent": "general",
        "insight_source": "error",
        "outcome": "error",
        "refused": False,
        "sections": [],
        "sub_queries": [],
        "pipeline_errors": pipeline_errors,
        "output_score": None,
        "output_scores": {},
    }
