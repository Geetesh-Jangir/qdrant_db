"""Optional LLM stage: facts + news -> ranked analysis brief for the composer."""

from __future__ import annotations

import json
from typing import Any

from news_rag.config import get_settings
from news_rag.insight.brief import QuestionBrief
from news_rag.insight.findings import Findings
from news_rag.insight.gather import EvidenceSet
from news_rag.insight.interpret import _facts
from news_rag.llm_client import call_json_llm, llm_api_key_configured, router_model
from news_rag.prompts import build_insight_analyst_prompt

ANALYST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "observed": {"type": "object"},
        "attribution": {"type": "array", "items": {"type": "object"}},
        "mechanisms": {"type": "array", "items": {"type": "object"}},
        "divergences": {"type": "array", "items": {"type": "string"}},
        "unsupported_or_coincident": {"type": "array", "items": {"type": "string"}},
        "gaps": {"type": "array", "items": {"type": "string"}},
        "net_takeaways": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["headline", "net_takeaways"],
}


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


def run_insight_analyst(
    question: str,
    brief: QuestionBrief,
    findings: Findings,
    evidence: EvidenceSet,
    *,
    query_log: Any = None,
) -> dict[str, Any] | None:
    settings = get_settings()
    if not analyst_should_run(brief, findings, settings):
        if query_log is not None:
            query_log.write("ANALYST skip mode=" + str(getattr(settings, "insight_analyst_mode", "auto")))
        return None
    if not llm_api_key_configured(settings):
        return None
    digest = bool(getattr(settings, "insight_use_news_digest", True))
    packet = _facts(question, brief, findings, evidence, include_article_bodies=not digest)
    user = (
        f"QUESTION:\n{question}\n\n"
        f"PLAN:\n{json.dumps({'goal': brief.goal, 'intent': brief.intent, 'sub_asks': [a.text for a in brief.sub_asks]}, ensure_ascii=False)}\n\n"
        f"FACTS PACKET:\n{json.dumps(packet, ensure_ascii=False, separators=(',', ':'))}"
    )
    try:
        res = call_json_llm(
            system_prompt=build_insight_analyst_prompt(),
            user_content=user,
            model_override=router_model(settings),
            max_tokens=4000,
            temperature=0.1,
            query_log=query_log,
            response_schema=ANALYST_SCHEMA,
            stage="insight_analyst",
        )
    except Exception as exc:  # noqa: BLE001
        if query_log is not None:
            query_log.write(f"ANALYST llm_failed error={str(exc)[:200]}")
        return None
    parsed = res.parsed if isinstance(res.parsed, dict) else {}
    return parsed if parsed else None
