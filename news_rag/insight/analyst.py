"""Gate for the optional insight-analyst stage."""

from __future__ import annotations

from typing import Any

from news_rag.insight.brief import QuestionBrief
from news_rag.insight.findings import Findings


def analyst_should_run(brief: QuestionBrief, findings: Findings, settings: Any) -> bool:
    """Auto mode keeps the analyst for fund attribution and comparisons only."""
    if not getattr(settings, "insight_use_llm_analyst", True):
        return False
    mode = str(getattr(settings, "insight_analyst_mode", "auto") or "auto").strip().lower()
    if mode == "off":
        return False
    if mode == "always":
        return True
    needs = set(brief.evidence_needs or [])
    if brief.intent == "compare" or "peer_compare" in needs:
        return True
    if "fund_vs_index" in needs or "holding_drivers" in needs:
        return True
    return False


