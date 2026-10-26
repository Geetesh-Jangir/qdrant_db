"""Orchestrate insight pipeline: bounded two-wave graph."""

from __future__ import annotations

from typing import Any, AsyncIterator

from news_rag.guardrails import ADVICE_NOTE
from news_rag.insight.graph import run_graph_pipeline, stream_graph_pipeline

if True:
    from news_rag.query_log import QueryLogger


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
    try:
        return run_graph_pipeline(
            q,
            date_from=date_from,
            date_to=date_to,
            min_impact=min_impact,
            source=source,
            direction=direction,
            query_log=query_log,
            prior_context=prior_brief_context,
        )
    except Exception as exc:
        if query_log is not None:
            query_log.log_error("graph_pipeline", str(exc))
        return {
            "insight": f"I was unable to complete the lookup for this query ({str(exc)[:120]}). Please try again with a specific fund name or topic.\n\n*For context only — not investment advice.*",
            "outcome": "error",
            "refused": False,
            "sections": [{"id": "A1", "style": "short_answer", "text": "Error processing query.", "headline": "Notice"}],
            "pipeline_errors": [{"stage": "graph", "tool": "", "message": str(exc)[:200]}],
            "advice_note": ADVICE_NOTE,
        }


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
    q = (question or "").strip()
    async for packet in stream_graph_pipeline(
        q,
        date_from=date_from,
        date_to=date_to,
        min_impact=min_impact,
        source=source,
        direction=direction,
        query_log=query_log,
        prior_context=prior_brief_context,
    ):
        yield packet
