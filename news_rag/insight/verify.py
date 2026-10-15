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

    allowed = cores_in_text(_grounding_blob(findings, evidence))
    cleaned = strip_ungrounded_numbers(insight_text, allowed)
    ungrounded = cleaned != insight_text
    if ungrounded:
        gaps.append("grounding:ungrounded_numbers_in_answer")

    gaps.extend(_attribution_judge(insight_text, evidence))

    retry: list[str] = []
    for entry in evidence.ledger:
        if entry.status == "unavailable" and not entry.implied and entry.facet not in retry:
            retry.append(entry.facet)
    if any(gap == "funds:none_found" for gap in gaps) and "exposure_link" not in retry:
        retry.append("exposure_link")

    return VerifyResult(
        passed=not gaps,
        gaps=list(dict.fromkeys(gaps)),
        retry_facets=retry,
        ungrounded_removed=ungrounded,
    )


def _grounding_blob(findings: Findings, evidence: EvidenceSet) -> str:
    """Numbers the answer may use: measured evidence, claims, and the article bodies they came from."""
    parts = [findings.evidence_text or ""]
    sector = findings.sector
    if sector is not None:
        parts.append(sector.tone_reason or "")
        parts.append(sector.news_summary or "")
        for claim in sector.claims or []:
            parts.append(str(claim.get("text") or ""))
    for art in (evidence.articles or [])[:8]:
        parts.append(str(art.get("title") or ""))
        parts.append(str(art.get("scraped_text") or art.get("snippet") or "")[:4000])
    return "\n".join(parts)


def _attribution_judge(insight_text: str, evidence: EvidenceSet) -> list[str]:
    """Contributions must add up, and the write-up must follow the largest holding detractors."""
    from news_rag.insight.holding_attribution import arithmetic_ok

    gaps: list[str] = []
    blob = (insight_text or "").lower()
    for item in evidence.by_facet("fund_attribution"):
        data = item.data if isinstance(item.data, dict) else {}
        for fund in data.get("funds") or []:
            if not isinstance(fund, dict):
                continue
            attr = fund.get("attribution") if isinstance(fund.get("attribution"), dict) else {}
            if not attr or not attr.get("all_priced"):
                continue
            if not arithmetic_ok(attr):
                gaps.append("attribution:contributions_do_not_sum")
            detractors = attr.get("detractors") or []
            if not detractors:
                continue
            top = str(detractors[0].get("name") or "")
            if top and top.lower() not in blob:
                gaps.append("attribution:top_detractor_missing")
            if "main drag" in blob and top and top.lower() not in blob:
                gaps.append("attribution:conclusion_contradicts_holdings")
    return gaps
