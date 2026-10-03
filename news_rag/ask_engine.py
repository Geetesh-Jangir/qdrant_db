"""Production ask pipeline: guardrails → plan → execute → render.

Does not read investor portfolio JSON; hypothetical "my portfolio" in questions is treated as macro context only.
"""

from __future__ import annotations

import json
from typing import Any, TYPE_CHECKING

from news_rag.config import get_settings
from news_rag.execution import execute_plan
from news_rag.final_composer import aggregate_runs, compose_unified_answer, should_unify_compose
from news_rag.macro_plans import PRESET_SOURCES
from news_rag.guardrails import check_guardrails, refusal_response
from news_rag.output_judge import NO_DATA_MSG, judge_answer
from news_rag.query_analyzer import decompose_query
from news_rag.query_plan import QueryPlan
from news_rag.synthesizer import build_subquery_section, merge_insight

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger


def _sources_from_articles(all_articles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    for a in all_articles:
        url = str(a.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        rows.append(
            {
                "title": a.get("title"),
                "url": url,
                "source": a.get("source"),
                "published_at": a.get("published_at"),
            }
        )
    return rows


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
    if query_log is not None:
        query_log.write(f"QUESTION: {q[:500]}")

    guard = check_guardrails(q)
    if guard.outcome != "pass":
        if query_log is not None:
            query_log.write(f"GUARDRAIL refuse reason={guard.reason}")
        resp = refusal_response(guard)
        if query_log is not None:
            query_log.log_insight_output(
                insight_source="guardrail",
                char_count=len(resp.get("insight") or ""),
                preview=str(resp.get("insight") or ""),
            )
        return resp

    if query_log is not None:
        query_log.write("GUARDRAIL pass")

    plan: QueryPlan = decompose_query(q, query_log=query_log)
    if not plan.sub_queries:
        return _empty_response()

    fund_ctx, runs = execute_plan(
        plan,
        q,
        date_from=date_from,
        date_to=date_to,
        min_impact=min_impact,
        source=source,
        direction=direction,
        query_log=query_log,
    )

    if fund_ctx.ambiguous:
        close = fund_ctx.close_matches or []
        msg = f"Your query matched multiple funds: {', '.join(close[:5])}. Please specify the full name or ISIN."
        return {
            "insight": msg,
            "insight_summary": msg,
            "insight_bullets": [],
            "sources": [],
            "intent": "fund_nav",
            "insight_source": "ask_engine",
            "outcome": "clarification",
            "refused": False,
            "sections": [{"id": "Q0", "style": "clarification", "text": msg, "bullets": []}],
            "sub_queries": [],
        }

    sections: list[dict[str, Any]] = []
    sub_query_meta: list[dict[str, Any]] = []
    all_articles: list[dict] = []
    settings = get_settings()
    unify = should_unify_compose(plan, settings)

    for run in runs:
        sq = run.sub_query
        news = (run.tool_results.get("news_search") or {}).get("data") or {}
        all_articles.extend(news.get("articles") or [])
        sub_query_meta.append({"id": sq.id, "text": sq.text, "style": sq.answer_style})

    insight_summary = ""
    if unify:
        if query_log is not None:
            query_log.write("ASK_ENGINE unified_compose=true")
        agg = aggregate_runs(runs, q, plan_source=plan.source)
        composed = compose_unified_answer(q, agg, plan_source=plan.source, query_log=query_log)
        sections = [
            {
                "id": "A1",
                "style": "unified_answer",
                "text": composed.display,
                "bullets": composed.bullets,
                "summary": composed.summary,
                "insight_sections": composed.insight_sections,
            }
        ]
        insight = composed.display
        bullets = composed.bullets
        insight_summary = composed.summary
        needs_judge = plan.source not in PRESET_SOURCES
    else:
        for run in runs:
            sq = run.sub_query
            section = build_subquery_section(
                sq, run.tool_results, user_question=q, query_log=query_log
            )
            sections.append(section)
            if query_log is not None:
                query_log.write(
                    f"SECTION {sq.id} style={sq.answer_style} chars={len(section.get('text') or '')}"
                )
        insight = merge_insight(sections)
        insight_summary = insight
        needs_judge = any(sq.needs_reasoning for sq in plan.sub_queries)
        bullets = []
        for sec in sections:
            bullets.extend(sec.get("bullets") or [])

    context_summary = json.dumps({"sections": sections}, ensure_ascii=False)[:8000]

    if needs_judge and insight:
        jr = judge_answer(q, insight, context_summary, query_log=query_log)
        if not jr.passed:
            jr2 = judge_answer(q, insight, context_summary + "\nretry=1", query_log=query_log)
            if not jr2.passed:
                if unify:
                    insight = NO_DATA_MSG
                    insight_summary = ""
                    bullets = []
                    sections = [{"id": "A1", "style": "unified_answer", "text": NO_DATA_MSG, "bullets": []}]
                else:
                    for sec in sections:
                        if sec.get("needs_llm"):
                            sec["text"] = NO_DATA_MSG
                    insight = merge_insight(sections)

    intent = "multi" if len(plan.sub_queries) > 1 else _primary_intent(plan)

    outcome = "ok" if any((s.get("text") or "").strip() for s in sections) else "no_data"

    result: dict[str, Any] = {
        "insight": insight,
        "insight_summary": insight_summary or insight,
        "insight_bullets": bullets,
        "sources": _sources_from_articles(all_articles),
        "intent": intent,
        "insight_source": "ask_engine",
        "outcome": outcome,
        "refused": False,
        "sections": sections,
        "sub_queries": sub_query_meta,
    }
    if query_log is not None:
        query_log.write(f"RESULT outcome={outcome}")
        query_log.log_insight_output(
            insight_source="ask_engine",
            char_count=len(insight),
            preview=insight[:500],
        )
    return result


def _empty_response() -> dict[str, Any]:
    return {
        "insight": NO_DATA_MSG,
        "insight_summary": NO_DATA_MSG,
        "insight_bullets": [],
        "sources": [],
        "intent": "general",
        "insight_source": "no_data",
        "outcome": "no_data",
        "sections": [],
        "sub_queries": [],
    }


def _primary_intent(plan: QueryPlan) -> str:
    tools = [n.tool for sq in plan.sub_queries for n in sq.data_needs]
    if "fund_nav" in tools:
        return "fund_nav"
    if "fund_holdings" in tools:
        return "fund_holdings"
    if "fund_sectors" in tools:
        return "fund_sectors"
    return "general"
