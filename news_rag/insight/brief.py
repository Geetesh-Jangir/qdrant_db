"""Phase 1: Question brief from user text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from news_rag.insight.facets import SUB_ASK_KINDS, validate_facets
from news_rag.insight.registry import ensure_registry, registry_prompt_block
from news_rag.llm_client import call_json_llm, llm_api_key_configured, router_model
from news_rag.config import get_settings
from news_rag.query_log import clip_log_text

BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "goal": {"type": "string"},
        "sub_asks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "kind": {"type": "string"},
                },
                "required": ["id", "text", "kind"],
            },
        },
        "subjects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "raw": {"type": "string"},
                    "role": {"type": "string"},
                    "canonical": {"type": "string"},
                },
            },
        },
        "scope": {
            "type": "object",
            "properties": {
                "window_days": {"type": "integer"},
                "window_label": {"type": "string"},
            },
        },
        "implicit_needs": {"type": "array", "items": {"type": "string"}},
        "evidence_needs": {"type": "array", "items": {"type": "string"}},
        "success_criteria": {"type": "array", "items": {"type": "string"}},
        "assumptions": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["goal", "sub_asks", "evidence_needs", "success_criteria"],
}

BRIEF_SYSTEM = """You are a financial research planner for Indian mutual funds and sector news.

Output JSON with: goal, sub_asks (id, text, kind), subjects (raw, role, canonical), scope (window_days, window_label), evidence_needs, success_criteria.

Sub-ask kinds: describe, measure, compare, explain_cause, predict, list.

evidence_needs — use ONLY these facet ids (the gather stage maps them to tools):
- news_drivers + entity_state_over_time: sector news articles and tone (layered_news).
- benchmark: sector index return for the window (index_series).
- exposure_link: funds ranked by sector weight (sector_funds) — required before per-fund tools.
- fund_composition + return_series: after exposure_link, for each shortlisted fund (other sectors + NAV returns).

Planning rules:
- Sector "how is X doing" + funds impacted: evidence_needs MUST include news_drivers, entity_state_over_time, benchmark, exposure_link, fund_composition, return_series.
- Set subject role=sector with canonical pipeline label (e.g. Automobiles, Banks).
- Default window: 180 days (6 months) unless user gives another range.
- success_criteria: concrete checks (names funds, states mixed/positive/negative, cites other sectors).
- No buy/sell advice.

Read the tool registry in the user message when choosing facets."""


@dataclass
class SubAsk:
    id: str
    text: str
    kind: str = "describe"
    order: int = 0
    max_sentences: int = 3


@dataclass
class QuestionBrief:
    goal: str = ""
    sub_asks: list[SubAsk] = field(default_factory=list)
    subjects: list[dict[str, str]] = field(default_factory=list)
    window_days: int = 180
    window_label: str = "6 months"
    implicit_needs: list[str] = field(default_factory=list)
    evidence_needs: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def primary_sector(self) -> str:
        for s in self.subjects:
            if str(s.get("role") or "").lower() == "sector":
                return str(s.get("canonical") or s.get("raw") or "").strip()
        for s in self.subjects:
            r = str(s.get("raw") or "").lower()
            if "auto" in r or "sector" in r or "bank" in r:
                return str(s.get("canonical") or s.get("raw") or "").strip()
        return ""

    def wants_funds(self) -> bool:
        blob = " ".join(a.text.lower() for a in self.sub_asks) + " " + self.goal.lower()
        return any(w in blob for w in ("fund", "impacted", "affected", "exposure", "hold"))


def _infer_window_days(question: str) -> tuple[int, str]:
    q = question.lower()
    m = re.search(r"(\d+)\s*month", q)
    if m:
        n = int(m.group(1))
        return max(30, n * 30), f"{n} months"
    if "6 month" in q or "six month" in q or "last 6" in q:
        return 180, "6 months"
    if "1 year" in q or "one year" in q or "12 month" in q:
        return 365, "1 year"
    if "3 month" in q or "quarter" in q:
        return 90, "3 months"
    return 180, "6 months"


def _split_sub_asks_from_question(question: str) -> list[SubAsk]:
    """Preserve the user's question order (before LLM)."""
    parts = re.split(r"\?+|\band then\b|\band if\b", question, flags=re.I)
    out: list[SubAsk] = []
    for i, part in enumerate(parts):
        text = part.strip().rstrip("?").strip()
        if len(text) < 12:
            continue
        kind = "describe"
        lower = text.lower()
        if any(w in lower for w in ("positively", "negative", "impacted", "affected", "which fund")):
            kind = "measure"
        elif "why" in lower or "driver" in lower or "factor" in lower:
            kind = "explain_cause"
        elif "compare" in lower:
            kind = "compare"
        max_sent = 2 if kind == "measure" else 3
        out.append(SubAsk(f"u{i+1}", text, kind, order=i + 1, max_sentences=max_sent))
    return out


def _heuristic_brief(question: str) -> QuestionBrief:
    ensure_registry()
    window_days, window_label = _infer_window_days(question)
    q_lower = question.lower()
    subjects: list[dict[str, str]] = []
    sector = ""
    if "automobile" in q_lower or " auto " in f" {q_lower} " or "automotive" in q_lower:
        sector = "Automobiles"
        subjects.append({"raw": "automobile", "role": "sector", "canonical": "Automobiles"})
    evidence = ["news_drivers", "entity_state_over_time", "benchmark"]
    sub_asks = _split_sub_asks_from_question(question)
    if not sub_asks:
        sub_asks = [SubAsk("s1", "Sector status and drivers", "describe", order=1)]
    success = ["States sector news themes", "Mentions benchmark or index context"]
    if any(w in q_lower for w in ("fund", "impacted", "affected", "exposure")):
        evidence.extend(["exposure_link", "fund_composition", "return_series"])
        if not any(a.kind == "measure" for a in sub_asks):
            sub_asks.append(
                SubAsk(
                    "f1",
                    "Funds with high exposure and positive or negative impact",
                    "measure",
                    order=len(sub_asks) + 1,
                    max_sentences=2,
                )
            )
        success.extend(
            [
                "Names multiple funds with exposure",
                "Lists other top sectors per fund",
                "Gives return pattern over requested window",
                "States positive/negative/mixed impact per fund",
            ]
        )
    if "nav" in q_lower and "fund" in q_lower:
        evidence.append("fund_facts_nav")
        sub_asks.append(SubAsk("n1", "Fund NAV and returns", "measure"))
    if "holding" in q_lower:
        evidence.append("fund_facts_holdings")
    if "market" in q_lower and "fund" not in q_lower:
        evidence.append("market_overview")
    evidence = validate_facets(evidence)
    return QuestionBrief(
        goal=question[:300],
        sub_asks=sub_asks,
        subjects=subjects,
        window_days=window_days,
        window_label=window_label,
        implicit_needs=["confounders via full fund composition"] if sector else [],
        evidence_needs=evidence,
        success_criteria=success,
        assumptions=["high exposure = top ranked funds by sector weight"] if sector else [],
        raw={"source": "heuristic"},
    )


def build_question_brief(
    question: str,
    *,
    prior_context: dict[str, Any] | None = None,
    query_log: Any = None,
) -> QuestionBrief:
    q = (question or "").strip()
    if not q:
        return QuestionBrief(goal="", evidence_needs=validate_facets(["market_overview"]))

    settings = get_settings()
    if not llm_api_key_configured(settings):
        brief = _heuristic_brief(q)
        if query_log is not None:
            query_log.log_brief(
                source="heuristic",
                brief_summary={
                    "sector": brief.primary_sector(),
                    "window": brief.window_label,
                    "evidence_needs": brief.evidence_needs,
                    "sub_asks": [f"{a.kind}:{a.text[:60]}" for a in brief.sub_asks],
                },
            )
        return brief

    ensure_registry()
    prior_blob = ""
    if prior_context:
        prior_blob = f"\nPrior turn context: {prior_context}\n"

    user = f"Question:\n{q}\n{prior_blob}\n{registry_prompt_block()}"
    try:
        res = call_json_llm(
            system_prompt=BRIEF_SYSTEM,
            user_content=user,
            context_blocks=[],
            model_override=router_model(settings),
            max_tokens=min(settings.ask_agent_max_tokens, 900),
            temperature=0.0,
            query_log=query_log,
            response_schema=BRIEF_SCHEMA,
            stage="brief",
        )
        parsed = res.parsed if isinstance(res.parsed, dict) else {}
        if getattr(res, "truncated", False) or not parsed:
            brief = _heuristic_brief(q)
            if query_log is not None:
                query_log.write("BRIEF_FALLBACK reason=llm_truncated_or_empty")
                query_log.log_brief(
                    source="heuristic",
                    brief_summary={
                        "sector": brief.primary_sector(),
                        "evidence_needs": brief.evidence_needs,
                    },
                )
            return brief
    except Exception as exc:
        parsed = {}
        if query_log is not None:
            query_log.write(f"BRIEF_FALLBACK reason=llm_error error={exc!s}"[:200])

    if not parsed:
        brief = _heuristic_brief(q)
        if query_log is not None:
            query_log.log_brief(source="heuristic", brief_summary={"evidence_needs": brief.evidence_needs})
        return brief

    sub_asks: list[SubAsk] = []
    for item in parsed.get("sub_asks") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "describe").strip().lower()
        if kind not in SUB_ASK_KINDS:
            kind = "describe"
        sub_asks.append(
            SubAsk(
                id=str(item.get("id") or f"s{len(sub_asks)+1}"),
                text=str(item.get("text") or ""),
                kind=kind,
                order=len(sub_asks) + 1,
                max_sentences=2 if kind == "measure" else 3,
            )
        )
    scope = parsed.get("scope") if isinstance(parsed.get("scope"), dict) else {}
    window_days = int(scope.get("window_days") or 0) or _infer_window_days(q)[0]
    window_label = str(scope.get("window_label") or _infer_window_days(q)[1])
    subjects = [s for s in (parsed.get("subjects") or []) if isinstance(s, dict)]
    evidence = validate_facets([str(x) for x in (parsed.get("evidence_needs") or [])])
    if not evidence:
        brief = _heuristic_brief(q)
        if query_log is not None:
            query_log.log_brief(source="heuristic", brief_summary={"reason": "empty_evidence_needs"})
        return brief
    heur = _heuristic_brief(q)
    evidence = list(dict.fromkeys(evidence + heur.evidence_needs))
    if not sub_asks:
        sub_asks = heur.sub_asks
    if not subjects:
        subjects = heur.subjects
    brief = QuestionBrief(
        goal=str(parsed.get("goal") or q[:300]),
        sub_asks=sub_asks or _heuristic_brief(q).sub_asks,
        subjects=subjects,
        window_days=window_days,
        window_label=window_label,
        implicit_needs=[str(x) for x in (parsed.get("implicit_needs") or [])],
        evidence_needs=evidence,
        success_criteria=[str(x) for x in (parsed.get("success_criteria") or [])],
        assumptions=[str(x) for x in (parsed.get("assumptions") or [])],
        raw={**parsed, "source": "llm"},
    )
    if query_log is not None:
        query_log.log_brief(
            source="llm",
            brief_summary={
                "goal": clip_log_text(brief.goal, 120),
                "sector": brief.primary_sector(),
                "window": brief.window_label,
                "evidence_needs": evidence,
                "sub_asks": [f"{a.kind}:{a.text[:50]}" for a in brief.sub_asks[:8]],
                "merged_heuristic_facets": heur.evidence_needs,
            },
        )
    return brief
