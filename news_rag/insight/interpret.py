"""Phase 4: Compose answer from findings — ordered, concise, bold highlights."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from news_rag.config import get_settings
from news_rag.insight.brief import QuestionBrief, SubAsk
from news_rag.insight.findings import Findings, FundFinding
from news_rag.insight.gather import EvidenceSet
from news_rag.insight.grounding import finalize_text_fields
from news_rag.llm_client import call_json_llm, composer_model, llm_api_key_configured

INTERPRET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "narrative": {"type": "string"},
        "bullets": {"type": "array", "items": {"type": "string"}},
        "closing_summary": {"type": "string"},
    },
    "required": ["headline", "narrative", "bullets", "closing_summary"],
}

INTERPRET_SYSTEM = """Short mutual-fund answers. Sub-asks in order. Bold key terms. JSON only."""

_SECTION_TITLE = {
    "describe": "1. Sector health (from news)",
    "measure": "2. Funds most exposed — positive or negative?",
    "explain_cause": "3. What else drives these funds",
    "compare": "Comparison",
    "list": "List",
    "predict": "Outlook",
}


@dataclass
class ComposedInsight:
    headline: str = ""
    narrative: str = ""
    bullets: list[str] = field(default_factory=list)
    closing_summary: str = ""
    display: str = ""
    sub_ask_coverage: list[str] = field(default_factory=list)
    answer_trace: dict[str, Any] = field(default_factory=dict)


def _short_fund_name(name: str) -> str:
    s = re.sub(r"\s*-\s*Regular Plan.*$", "", name, flags=re.I).strip()
    s = re.sub(r"\s*-\s*Growth.*$", "", s, flags=re.I).strip()
    return s or name


def _news_backdrop(findings: Findings) -> str:
    stats = findings.sector.news_stats if findings.sector else {}
    pos = int(stats.get("positive") or 0)
    neg = int(stats.get("negative") or 0)
    if pos or neg:
        return f"**mixed** sector news ({pos} positive vs {neg} negative articles)"
    tone = findings.sector.news_direction if findings.sector else "unknown"
    if tone not in ("", "unknown"):
        return f"sector news **{tone}**"
    return "sector news"


def _fund_vs_news(f: FundFinding, findings: Findings, news_dir: str) -> str:
    ret = f.return_window_pct
    backdrop = _news_backdrop(findings)
    if ret is None:
        return f"{backdrop}; fund return **n/a**"
    if news_dir in ("mixed", "unknown", "") or _is_mixed_news(findings):
        if ret > 2:
            return f"{backdrop} → fund **helped** (**{ret:+.1f}%** return)"
        if ret < -2:
            return f"{backdrop} → fund **hurt** (**{ret:+.1f}%** return)"
        return f"{backdrop} → fund **neutral** vs headlines (**{ret:+.1f}%**)"
    if news_dir == "positive":
        if ret > 1:
            return f"{backdrop} → **aligned** (**{ret:+.1f}%**)"
        if ret < -1:
            return f"{backdrop} → **diverged** (**{ret:+.1f}%**)"
    if news_dir == "negative":
        if ret < -1:
            return f"{backdrop} → **aligned** (**{ret:+.1f}%**)"
        if ret > 1:
            return f"{backdrop} → **diverged** (**{ret:+.1f}%**)"
    return f"{backdrop} → **{ret:+.1f}%**"


def _is_mixed_news(findings: Findings) -> bool:
    stats = findings.sector.news_stats if findings.sector else {}
    pos = int(stats.get("positive") or 0)
    neg = int(stats.get("negative") or 0)
    if not pos and not neg:
        return findings.sector.news_direction == "mixed" if findings.sector else True
    return abs(pos - neg) <= max(pos, neg, 1) * 0.35


def _sector_section(brief: QuestionBrief, findings: Findings) -> str:
    s = findings.sector
    label = s.sector_label or brief.primary_sector() or "Sector"
    blocks: list[str] = []
    summary = s.executive_summary or s.news_summary
    if summary:
        blocks.append(summary)
    if s.article_count:
        blocks.append(f"From **{s.article_count}** retrieved articles in the window.")
    if s.news_insights:
        blocks.append(
            "**Evidence from articles:**\n"
            + "\n".join(f"- {x}" for x in s.news_insights[:4])
        )
    elif s.news_direction not in ("", "unknown"):
        blocks.append(f"Overall tagged news direction: **{s.news_direction}**.")
    if s.index_return_pct is not None:
        blocks.append(
            f"**{label}** proxy index (**{s.benchmark_label}**): **{s.index_return_pct:+.2f}%** over **{brief.window_label}**."
        )
    if s.news_themes and not s.news_insights:
        theme_lines = "\n".join(f"- {t}" for t in s.news_themes[:3])
        blocks.append("**Sources (titles only):**\n" + theme_lines)
    if not blocks:
        blocks.append("Not enough sector news or index data in this run to judge sector health.")
    return "\n\n".join(blocks)


def _funds_section(
    brief: QuestionBrief,
    findings: Findings,
    news_dir: str,
    max_bullets: int = 5,
) -> tuple[str, list[str]]:
    if not findings.funds:
        return "No funds with at least ~5% auto-related exposure showed up in the data.", []
    bullets: list[str] = []
    for f in findings.funds[:max_bullets]:
        name = _short_fund_name(f.fund_name)
        exp = f.exposure_pct
        ret = f.return_window_pct
        verdict = _fund_vs_news(f, findings, news_dir)
        other = f.other_top_sectors[0] if f.other_top_sectors else None
        other_txt = ""
        if other and other.get("sector"):
            pct = other.get("percentage")
            pct_txt = f"**{float(pct):.2f}%**" if pct is not None else ""
            other_txt = f" Larger sleeve: **{other.get('sector')}** {pct_txt}."
        ret_txt = f"**{ret:+.2f}%**" if ret is not None else "**N/A**"
        exp_txt = f"**{exp:.2f}%**" if exp is not None else "**N/A**"
        bullets.append(
            f"**{name}** — **Automobiles** {exp_txt}, **{brief.window_label}** {ret_txt}. {verdict}.{other_txt}"
        )
    intro = (
        f"Top **{min(len(findings.funds), max_bullets)}** funds by **Automobiles** sector weight "
        f"(≥8% in the holdings aggregate; ranked by exposure, then **{brief.window_label}** return)."
    )
    return intro, bullets


def _summary_headline(findings: Findings, brief: QuestionBrief) -> str:
    s = findings.sector
    label = s.sector_label or brief.primary_sector() or "Sector"
    idx = ""
    if s.index_return_pct is not None:
        idx = f"; index **{s.index_return_pct:+.2f}%** over {brief.window_label}"
    summary = s.executive_summary or s.news_summary
    if summary:
        first = summary.split(".")[0].strip()
        if not first.endswith("."):
            first += "."
        return f"**{label}:** {first}{idx}"
    tone = s.news_direction if s.news_direction not in ("", "unknown") else "mixed"
    return f"**{label}:** news tone **{tone}**{idx}."


def _structured_compose(
    question: str,
    brief: QuestionBrief,
    findings: Findings,
    evidence: EvidenceSet,
) -> ComposedInsight:
    news_dir = findings.sector.news_direction if findings.sector else "unknown"
    ordered = sorted(brief.sub_asks, key=lambda a: a.order or 0)
    narrative_blocks: list[str] = []
    bullets: list[str] = []
    headline = _summary_headline(findings, brief)

    for ask in ordered:
        title = _SECTION_TITLE.get(ask.kind, ask.text[:50])
        heading = f"**{title}**"
        if ask.kind == "describe":
            body = _sector_section(brief, findings)
            narrative_blocks.append(f"{heading}\n\n{body}")
        elif ask.kind in ("measure", "list"):
            intro, fund_bullets = _funds_section(brief, findings, news_dir, max_bullets=5)
            narrative_blocks.append(f"{heading}\n\n{intro}")
            bullets.extend(fund_bullets[:5])
        elif ask.kind == "explain_cause":
            lines = []
            for f in findings.funds[:4]:
                name = _short_fund_name(f.fund_name)
                att = f.attribution.get("topic_share_pct") or f.exposure_pct
                if f.other_top_sectors:
                    top = f.other_top_sectors[0]
                    lines.append(
                        f"- **{name}**: auto ~**{att}%**; **{top.get('sector')}** ({top.get('percentage')}%) is larger."
                    )
            narrative_blocks.append(
                f"{heading}\n\n" + ("\n".join(lines) if lines else "Could not separate drivers.")
            )
        else:
            narrative_blocks.append(f"{heading}\n\nSee bullets below.")

    caveats: list[str] = []
    for e in (evidence.ledger if evidence else []):
        if e.status == "unavailable" and e.facet == "benchmark":
            caveats.append("Sector index return was unavailable in this run.")
    closing = " ".join(caveats[:1]) if caveats else ""
    if closing:
        closing += " For context only — not investment advice."
    else:
        closing = "For context only — not investment advice."

    narrative = "\n\n".join(narrative_blocks)
    headline, narrative, bullets, closing = finalize_text_fields(
        headline, narrative, bullets, closing, findings.evidence_text
    )
    display = "\n\n".join(
        p for p in [headline, narrative, "\n".join(f"• {b}" for b in bullets), closing] if p
    )
    return ComposedInsight(
        headline=headline,
        narrative=narrative,
        bullets=bullets,
        closing_summary=closing,
        display=display.strip(),
        sub_ask_coverage=[a.text for a in ordered],
        answer_trace={"mode": "structured", "findings": findings.to_dict()},
    )


def compose_from_findings(
    question: str,
    brief: QuestionBrief,
    findings: Findings,
    evidence: EvidenceSet,
    *,
    query_log: Any = None,
) -> ComposedInsight:
    settings = get_settings()
    structured = _structured_compose(question, brief, findings, evidence)

    use_llm = bool(getattr(settings, "insight_use_llm_interpret", False))
    if query_log is not None:
        query_log.write(
            f"INTERPRET_MODE structured=true llm_polish={use_llm and llm_api_key_configured(settings)}"
        )
    if not use_llm or not llm_api_key_configured(settings):
        return structured

    user = f"Question: {question}\nFindings:\n{findings.to_dict()}\n"
    res = None
    try:
        res = call_json_llm(
            system_prompt=INTERPRET_SYSTEM,
            user_content=user,
            context_blocks=[],
            model_override=composer_model(settings),
            max_tokens=2000,
            temperature=0.1,
            query_log=query_log,
            response_schema=INTERPRET_SCHEMA,
            stage="interpret",
        )
        parsed = res.parsed if isinstance(res.parsed, dict) else {}
    except Exception:
        parsed = {}

    if not parsed or (res is not None and getattr(res, "truncated", False)):
        return structured
    headline = str(parsed.get("headline") or structured.headline)
    narrative = str(parsed.get("narrative") or structured.narrative)
    bullets = [str(b) for b in (parsed.get("bullets") or structured.bullets) if str(b).strip()]
    closing = str(parsed.get("closing_summary") or structured.closing_summary)
    headline, narrative, bullets, closing = finalize_text_fields(
        headline, narrative, bullets, closing, findings.evidence_text
    )
    if len(narrative) > 2800:
        return structured
    display = "\n\n".join(
        p for p in [headline, narrative, "\n".join(f"• {b}" for b in bullets), closing] if p
    )
    return ComposedInsight(
        headline=headline,
        narrative=narrative,
        bullets=bullets,
        closing_summary=closing,
        display=display.strip(),
        sub_ask_coverage=structured.sub_ask_coverage,
        answer_trace={"mode": "llm_polish", "findings": findings.to_dict()},
    )
