"""Ask pipeline entry — insight v2 (brief → gather → compute → interpret → verify)."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from news_rag.config import get_settings
from news_rag.insight.pipeline import run_insight_pipeline

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger


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
        query_log.write(f"PIPELINE name=insight_v2 path=brief→gather→compute→interpret→verify→judge")
        query_log.write(f"QUESTION: {q[:500]}")
    # Legacy env flag kept for scripts that toggle v1; v1 path removed — always v2.
    _ = get_settings().ask_pipeline_v2
    return run_insight_pipeline(
        q,
        date_from=date_from,
        date_to=date_to,
        min_impact=min_impact,
        source=source,
        direction=direction,
        query_log=query_log,
    )
