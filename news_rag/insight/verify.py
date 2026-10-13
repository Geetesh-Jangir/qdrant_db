"""Phase 5a: verify the answer against the brief and findings (telemetry; gaps are logged and returned)."""

from __future__ import annotations

from dataclasses import dataclass, field

from news_rag.insight.brief import QuestionBrief, asks_sector_lists
from news_rag.insight.findings import Findings
from news_rag.insight.gather import EvidenceSet
from news_rag.insight.grounding import cores_in_text, strip_ungrounded_numbers

_DIRECTION_WORDS = ("positive", "negative", "mixed", "unclear", "diverged", "tailwind", "headwind", "aligned", "diluted")


@dataclass
class VerifyResult:
    passed: bool = True
    gaps: list[str] = field(default_factory=list)
    retry_facets: list[str] = field(default_factory=list)
    ungrounded_removed: bool = False


def verify_answer(
    brief: QuestionBrief,
    findings: Findings,
    evidence: EvidenceSet,
    *,
    insight_text: str,
    question: str = "",
) -> VerifyResult:
    gaps: list[str] = []
    blob = (insight_text or "").lower()

    # Evidence that was asked for but could not be gathered.
    for entry in evidence.ledger:
        if entry.status == "unavailable" and not entry.implied:
            gaps.append(f"evidence:{entry.facet}:unavailable:{entry.reason or 'unknown'}")

    sector = findings.sector
    if brief.primary_sector() and sector is not None:
        if not sector.claims:
            gaps.append("news:no_claims")
        else:
            grounded = [
                c.get("text", "")[:50]
                for c in sector.claims[:6]
                if c.get("text") and c.get("text")[:30] in insight_text
            ]
            if sector.claims and not grounded:
                gaps.append("news:answer_not_grounded_in_claims")
        if sector.index_return_pct is None and not any(
            e.facet == "benchmark" and e.status == "unavailable" for e in evidence.ledger
        ):
            gaps.append("benchmark:missing")

    if asks_sector_lists(question, brief) and not brief.primary_sector() and not brief.wants_funds():
        if sector is not None and not sector.sectors_negative and not sector.sectors_positive:
            gaps.append("sectors:no_hurt_help_lists")
        elif sector is not None and sector.sectors_negative:
            if not any(str(x.get("name") or "") in insight_text for x in sector.sectors_negative[:4]):
                gaps.append("sectors:answer_missing_hurt_names")

    from news_rag.insight.brief import asks_market_briefing

    market_wide = asks_market_briefing(question) and not brief.funds and not findings.funds
    if brief.wants_funds() and not market_wide:
        if not findings.funds:
            gaps.append("funds:none_found")
        for f in findings.funds[:5]:
            if f.alignment == "unknown":
                gaps.append(f"fund:{f.isin or f.fund_name[:20]}:no_alignment")
            if f.return_window_pct is None:
                gaps.append(f"fund:{f.isin or f.fund_name[:20]}:no_return")
        if findings.funds and not any(w in blob for w in _DIRECTION_WORDS):
            gaps.append("success:direction_not_stated")

    for criterion in brief.success_criteria:
        key = criterion.lower()
        if "other sector" in key or "other top sector" in key:
            if findings.funds and not any(f.other_top_sectors for f in findings.funds):
                gaps.append("success:other_sectors_missing")
        if "6 month" in key or "6-month" in key:
            if findings.funds and not any(f.monthly_returns for f in findings.funds):
                gaps.append("success:monthly_pattern_missing")

    allowed = cores_in_text(findings.evidence_text)
    cleaned = strip_ungrounded_numbers(insight_text, allowed)
    ungrounded = cleaned != insight_text
    if ungrounded:
        gaps.append("grounding:ungrounded_numbers_in_answer")

    return VerifyResult(
        passed=not gaps,
        gaps=list(dict.fromkeys(gaps)),
        retry_facets=[],
        ungrounded_removed=ungrounded,
    )
