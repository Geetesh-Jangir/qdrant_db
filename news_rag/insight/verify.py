"""Phase 5a: Verify answer against brief and findings."""

from __future__ import annotations

from dataclasses import dataclass, field

from news_rag.insight.brief import QuestionBrief
from news_rag.insight.findings import Findings
from news_rag.insight.grounding import cores_in_text, strip_ungrounded_numbers
from news_rag.insight.gather import EvidenceSet


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
) -> VerifyResult:
    gaps: list[str] = []
    retry: list[str] = []

    for entry in evidence.ledger:
        if entry.status in ("missing", "partial"):
            gaps.append(f"evidence:{entry.facet}:{entry.status}")
            retry.append(entry.facet)

    blob = (insight_text or "").lower()
    for criterion in brief.success_criteria:
        key = criterion.lower()
        if "other sector" in key or "other top sector" in key:
            if findings.funds and not any(f.other_top_sectors for f in findings.funds):
                gaps.append("success:other_sectors_missing")
                if "fund_composition" not in retry:
                    retry.append("fund_composition")
        if "6 month" in key or "6-month" in key:
            if "month" not in blob and not any(f.monthly_returns for f in findings.funds):
                gaps.append("success:6m_pattern_missing")
                if "return_series" not in retry:
                    retry.append("return_series")
        if "positive" in key or "negative" in key:
            if (
                "positive" not in blob
                and "negative" not in blob
                and "mixed" not in blob
                and "unclear" not in blob
                and "diverged" not in blob
            ):
                if findings.funds:
                    gaps.append("success:direction_not_stated")

    for ask in brief.sub_asks:
        snippet = ask.text.lower()[:40]
        if snippet and snippet not in blob and ask.kind == "describe":
            if "sector" in snippet or "automobile" in snippet or "auto" in snippet:
                if "news" not in blob and "index" not in blob:
                    gaps.append(f"sub_ask:{ask.id}:sector_not_addressed")

    allowed = cores_in_text(findings.evidence_text)
    cleaned = strip_ungrounded_numbers(insight_text, allowed)
    ungrounded = cleaned != insight_text

    passed = len(gaps) == 0 and not ungrounded
    return VerifyResult(passed=passed, gaps=gaps, retry_facets=list(dict.fromkeys(retry)), ungrounded_removed=ungrounded)
