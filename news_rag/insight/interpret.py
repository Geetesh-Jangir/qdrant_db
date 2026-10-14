"""Phase 4: compose the answer.

Hybrid design:
  - CODE owns every number and label (exposure, return, tilt, alignment) and the layout.
  - The LLM only writes the words that link news to funds: headline, sector read, one line per fund,
    closing. It is given FACTS (cited claims, per-fund tilt/alignment) and must cite claims as [c1].
  - Each LLM field is validated; any field that fails falls back to a structured sentence built from
    the same facts, so the answer is always complete and news-backed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from news_rag.config import get_settings
from news_rag.insight.brief import QuestionBrief, asks_market_briefing, asks_sector_lists
from news_rag.insight.findings import Findings, FundFinding, SectorFinding
from news_rag.insight.gather import EvidenceSet
from news_rag.insight.grounding import (
    cores_in_text,
    finalize_text_fields,
    strip_media_attribution,
    strip_ungrounded_numbers,
)
from news_rag.prompts import (
    build_composer_prompt,
    build_interpret_hybrid_prompt,
    build_named_fund_composer_prompt,
)
from news_rag.insight.measured_facts import measured_facts_block
from news_rag.snippet_clean import article_text_usable, polish_insight_sentence, starts_mid_sentence
from news_rag.llm_client import (
    call_insight_llm,
    call_json_llm,
    composer_model,
    llm_api_key_configured,
)


MAX_FUND_BULLETS = 5

INTERPRET_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "sector_read": {"type": "string"},
        "fund_lines": {"type": "object"},
        "closing": {"type": "string"},
    },
    "required": ["headline", "sector_read", "fund_lines", "closing"],
}

INTERPRET_SYSTEM = build_interpret_hybrid_prompt()

# Final answers are not truncated to a fixed character budget (0 = no cap in polish_insight_sentence).
_INSIGHT_TEXT_CAP = 0


def _composer_user_content(packet: dict[str, Any], analysis_brief: dict[str, Any] | None) -> str:
    parts: list[str] = []
    list_dir = str(packet.get("list_direction") or "any")
    if list_dir == "positive":
        parts.append(
            "USER CONSTRAINT (mandatory): List ONLY sectors and funds that are positively "
            "affected / tailwinds from the driver. Do not present a negative-sector essay; "
            "you may use one short sentence on macro pain only as context."
        )
    elif list_dir == "negative":
        parts.append(
            "USER CONSTRAINT (mandatory): List ONLY sectors and funds negatively affected. "
            "Do not list tailwind / helped names."
        )
    from news_rag.insight.brief import asks_random_fund_compare, asks_share_price, random_fund_count

    if random_fund_count(str(packet.get("question") or "")) == 1:
        parts.append(
            "USER CONSTRAINT (mandatory): The user did not name a fund. The fund in this packet was "
            "picked at random from the catalog. Say so in one short phrase, then answer exactly what "
            "was asked about THAT fund (e.g. its sector weights from the composition data, top holdings, "
            "return). Lead with the fund's own sector weights. Do not give a market-wide sector essay, "
            "do not ask the user to name a fund, and do not switch funds."
        )

    if asks_share_price(str(packet.get("question") or "")) and packet.get("stock"):
        parts.append(
            "USER CONSTRAINT (mandatory): The user asked for a share price. "
            "Lead with the rupee price in facts.stock. Do not answer with a mutual fund."
        )
    if asks_market_briefing(str(packet.get("question") or "")) and not packet.get("funds"):
        parts.append(
            "USER CONSTRAINT (mandatory): This is a market briefing. Lead with what happened "
            "and why. Do not mention missing ISINs, holdings, FACTS PACKET, or article counts. "
            "Do not ask the user for fund data."
        )
    if asks_random_fund_compare(str(packet.get("question") or "")):
        parts.append(
            "USER CONSTRAINT (mandatory): The user did not name funds. The two funds in this "
            "packet were picked at random from the catalog. Compare those two side by side "
            "(returns, category, top sectors, overlap). Say they were chosen at random. "
            "Do not ask the user to name funds, and do not switch to other funds."
        )
    parts.append("FACTS PACKET:\n" + json.dumps(packet, ensure_ascii=False, indent=2))
    if analysis_brief:
        parts.append(
            "ANALYSIS BRIEF:\n" + json.dumps(analysis_brief, ensure_ascii=False, indent=2)
        )
    return "\n\n".join(parts)

# Real advice only. Descriptive market language ("foreign investors sold", "selling pressure") is fine.
_ADVICE_RE = re.compile(
    r"\b(?:you should|investors should (?:buy|sell|invest|hold|avoid|switch|accumulate)|"
    r"should (?:buy|sell|invest|hold|avoid|switch|accumulate)|"
    r"(?:we|i) recommend|recommend(?:ed|s|ing)? (?:buying|selling|investing|holding|that you)|"
    r"good time to (?:buy|sell|invest)|"
    r"(?:consider|worth) (?:buying|selling|investing|adding)|"
    r"(?:buy|accumulate|avoid) (?:on dips?|these|this fund|the fund))\b",
    re.I,
)
_MARKER_RE = re.compile(r"\s*\[c(\d+)\]")
_OUTLET_RE = re.compile(
    r"\b(Economic Times|Livemint|Mint|Reuters|CNBC|CNBC-TV18|Moneycontrol|Business Standard|NDTV|Bloomberg|Financial Express)\b",
    re.I,
)
_DATE_RE = re.compile(
    r"\b(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*|\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2})\b",
    re.I,
)


def scrub_composer_text(text: str, packet: dict[str, Any], evidence_text: str) -> str:
    """Remove only the offending sentences/numbers instead of discarding the whole answer."""
    allowed = cores_in_text(evidence_text)
    allowed.update(cores_in_text(json.dumps(packet, ensure_ascii=False)))
    kept_lines: list[str] = []
    for line in (text or "").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            kept_lines.append(line)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", line)
        ok = [
            s for s in sentences
            if not (_ADVICE_RE.search(s) or _OUTLET_RE.search(s) or _DATE_RE.search(s))
        ]
        kept_lines.append(" ".join(ok))
    scrubbed = "\n".join(kept_lines)
    return strip_ungrounded_numbers(scrubbed, allowed)


def check_composer_guardrails(text: str, packet: dict[str, Any], evidence_text: str) -> list[str]:
    violations: list[str] = []
    if _ADVICE_RE.search(text):
        violations.append("Contains investment advice.")
    if _OUTLET_RE.search(text):
        violations.append("Mentions news outlet names.")
    if _DATE_RE.search(text):
        violations.append("Mentions publication dates.")
    allowed = cores_in_text(evidence_text)
    allowed.update(cores_in_text(json.dumps(packet, ensure_ascii=False)))
    cleaned = strip_ungrounded_numbers(text, allowed)
    if cleaned != text:
        violations.append("Contains ungrounded numbers.")
    return violations



@dataclass
class ComposedInsight:
    headline: str = ""
    narrative: str = ""
    bullets: list[str] = field(default_factory=list)
    closing_summary: str = ""
    display: str = ""
    sub_ask_coverage: list[str] = field(default_factory=list)
    answer_trace: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _short_fund_name(name: str) -> str:
    s = re.sub(r"\s*-\s*Regular Plan.*$", "", name, flags=re.I).strip()
    s = re.sub(r"\s*-\s*Growth.*$", "", s, flags=re.I).strip()
    s = re.sub(r"\s*-\s*Direct.*$", "", s, flags=re.I).strip()
    return s or name


def _fund_cap(question: str) -> int:
    m = re.search(r"\b(\d+)\s+funds?\b", question or "", re.I)
    if m:
        return max(1, min(int(m.group(1)), MAX_FUND_BULLETS))
    return MAX_FUND_BULLETS


def _shown_funds(
    findings: Findings, question: str = "", brief: QuestionBrief | None = None
) -> list[FundFinding]:
    """Up to MAX_FUND_BULLETS funds. When the news splits funds into tailwind and headwind, show both sides."""
    funds = list(findings.funds)
    d = (brief.direction if brief else "any").strip().lower()
    if d == "positive":
        funds = [f for f in funds if f.news_tilt == "tailwind"] or funds
    elif d == "negative":
        funds = [f for f in funds if f.news_tilt == "headwind"] or funds
    head = [f for f in funds if f.news_tilt == "headwind"]
    tail = [f for f in funds if f.news_tilt == "tailwind"]
    if head and tail and d == "any":
        n_tail = min(len(tail), max(2, MAX_FUND_BULLETS - 3))
        n_head = min(len(head), MAX_FUND_BULLETS - n_tail)
        picked = head[:n_head] + tail[:n_tail]
        rest = [f for f in funds if f not in picked]
        picked += rest[: MAX_FUND_BULLETS - len(picked)]
        cap = _fund_cap(question)
        return sorted(picked, key=lambda f: funds.index(f))[:cap]
    return funds[: _fund_cap(question)]


def _claim_map(findings: Findings) -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in (findings.sector.claims if findings.sector else [])}


def _render_citations(text: str, claims: dict[str, dict[str, Any]]) -> tuple[str, int]:
    """Drop [c#] markers and any outlet names; sources are attached separately in the API."""
    raw = text or ""
    cited = len(_MARKER_RE.findall(raw))
    out = _MARKER_RE.sub("", raw)
    out = strip_media_attribution(out)
    return out.strip(), cited


def _dedupe_parenthetical_cites(text: str) -> str:
    """(Economic Times, 10 Oct; Economic Times, 10 Oct) -> single cite."""

    def repl(m: re.Match[str]) -> str:
        inner = m.group(1)
        if not re.search(r"\d", inner):
            return m.group(0)
        parts = [p.strip() for p in inner.split(";")]
        uniq: list[str] = []
        for p in parts:
            if p and p not in uniq:
                uniq.append(p)
        if not uniq:
            return ""
        return " (" + "; ".join(uniq) + ")"

    return re.sub(r"\(([^()]+)\)", repl, text or "")


def _valid_llm_text(text: str, *, max_chars: int = 0) -> bool:
    t = (text or "").strip()
    if not t or _ADVICE_RE.search(t):
        return False
    return max_chars <= 0 or len(t) <= max_chars


def _pct(v: float | None, signed: bool = False) -> str:
    if v is None:
        return "**n/a**"
    return f"**{v:+.1f}%**" if signed else f"**{v:.1f}%**"


# ---------------------------------------------------------------------------
# Structured (code-built) pieces — also the fallback for every LLM field
# ---------------------------------------------------------------------------


def _index_line(brief: QuestionBrief, findings: Findings) -> str:
    s = findings.sector
    if not s or s.index_return_pct is None or not brief.primary_sector():
        return ""
    label = s.sector_label or brief.primary_sector() or "Sector"
    if any(l.code == "benchmark_substitute" for l in findings.limits):
        return (
            f"No usable **{label}** index history, so for context the broad market (**Nifty 50**) "
            f"moved **{s.index_return_pct:+.1f}%** over **{brief.window_label}**."
        )
    return (
        f"The market's own verdict: **{s.benchmark_label or label}** is "
        f"**{s.index_return_pct:+.1f}%** over **{brief.window_label}**."
    )


def _structured_sector_read(findings: Findings) -> str:
    s = findings.sector
    if not s:
        return ""
    reason = (s.tone_reason or "").strip()
    if re.search(r"\d+\s+of the\s+\d+\s+articles", reason, re.I):
        reason = ""
    if reason:
        tone_word = {"positive": "positive", "negative": "negative", "mixed": "mixed"}.get(s.tone, "")
        lead = f"The news tone is **{tone_word}**. " if tone_word else ""
        return (lead + reason).strip()
    summary = (s.executive_summary or "").strip()
    if summary and not re.search(r"\d+\s+of the\s+\d+\s+articles", summary, re.I):
        return summary
    return ""


def _sector_lists_block(s: SectorFinding, *, emphasize_down: bool, side: str = "both") -> str:
    neg = [x for x in (s.sectors_negative or []) if x.get("name")]
    pos = [x for x in (s.sectors_positive or []) if x.get("name")]
    if side == "positive":
        neg = []
    elif side == "negative":
        pos = []
    if not neg and not pos:
        return ""
    chunks: list[str] = []

    def _lines(title: str, rows: list[dict]) -> list[str]:
        out = [title]
        for x in rows[:6]:
            reason = polish_insight_sentence(str(x.get("reason") or ""), max_chars=180).rstrip(".")
            name = str(x.get("name") or "").strip()
            if not name:
                continue
            out.append(f"• **{name}**" + (f" — {reason}" if reason else ""))
        return out

    if neg:
        title = "**Sectors under pressure**"
        chunks.append("\n".join(_lines(title, neg)))
    if pos:
        title = "**Sectors that benefit**" if side == "positive" else "**Sectors holding up better**"
        chunks.append("\n".join(_lines(title, pos)))
    return "\n\n".join(chunks).strip()


def _structured_headline(brief: QuestionBrief, findings: Findings) -> str:
    s = findings.sector
    label = (s.sector_label if s else "") or brief.primary_sector() or "Market"
    tone = s.tone if s and s.tone not in ("", "unknown", "unclear") else ""
    reason = (s.tone_reason or "").strip() if s else ""
    first = reason.split(". ")[0].rstrip(".") if reason else ""
    idx = ""
    if s and s.index_return_pct is not None:
        idx = f"; index **{s.index_return_pct:+.1f}%** over {brief.window_label}"
    if tone and first:
        return f"**{label}:** news is **{tone}** — {first}{idx}."
    if tone:
        return f"**{label}:** news is **{tone}**{idx}."
    return f"**{label}:** not enough news to call a direction{idx}."


def _status_tag(f: FundFinding) -> str:
    touched = f.pos_exposure_pct + f.neg_exposure_pct + f.mixed_exposure_pct
    if f.drag_sectors:
        top = f.drag_sectors[0]
        idx = top.get("index_return_pct")
        idx_txt = f" index **{float(idx):+.1f}%**" if isinstance(idx, (int, float)) else ""
        return f"**{top.get('sector')}** is **{float(top.get('weight_pct') or 0):.0f}%** of the fund{idx_txt}"
    if f.news_tilt == "unknown":
        return ""
    if touched < 1:
        return "this news **does not reach** the fund's holdings"
    if f.alignment == "diluted":
        return f"the news touches only **{touched:.0f}%** of the fund, so the effect is **diluted**"
    if f.news_tilt == "mixed":
        if f.pos_exposure_pct >= 3 and f.neg_exposure_pct >= 3:
            return (
                f"news helps **{f.pos_exposure_pct:.0f}%** of the fund and hurts "
                f"**{f.neg_exposure_pct:.0f}%**, so the net effect is **mixed**"
            )
        return f"news pulls **both ways** on the **{touched:.0f}%** of the fund it touches"
    if f.news_tilt == "neutral":
        return "news has **little direct effect** on its holdings"
    tilt = "**tailwind**" if f.news_tilt == "tailwind" else "**headwind**"
    return {
        "aligned": f"the fund's return **moved with** that {tilt}",
        "diverged": f"the fund's return **did not follow** that {tilt}",
        "flat": f"the fund's return was **almost flat** despite that {tilt}",
    }.get(f.alignment, f"news is a {tilt}")


def _structured_fund_line(f: FundFinding) -> str:
    parts: list[str] = []
    if f.mechanism:
        parts.append(f.mechanism.split(" | ")[0].strip().rstrip("."))
    if f.alignment == "diverged" and f.other_top_sectors:
        top = f.other_top_sectors[0]
        parts.append(f"larger sleeve is **{top.get('sector')}** at **{float(top.get('percentage') or 0):.1f}%**")
    elif f.other_top_sectors and not parts:
        top = f.other_top_sectors[0]
        parts.append(f"larger sleeve: **{top.get('sector')}** **{float(top.get('percentage') or 0):.1f}%**")
    return "; ".join(parts)


def _unique_fund_lines(fund_lines: dict[str, str]) -> dict[str, str]:
    """Drop a sentence that is copied onto every fund — the sector read already said it."""
    texts = [re.sub(r"\s+", " ", (v or "")).strip().lower() for v in fund_lines.values() if (v or "").strip()]
    if len(texts) < 2 or len(set(texts)) != 1:
        return fund_lines
    return {k: "" for k in fund_lines}


def _fund_bullet(
    f: FundFinding, brief: QuestionBrief, sector_label: str, why: str, bench_label: str = ""
) -> str:
    name = _short_fund_name(f.fund_name)
    exp_label = f.exposure_sector or (sector_label if sector_label != "Sector" else "")
    exp_txt = f" · **{exp_label} {f.exposure_pct:.1f}%**".replace("**  ", "**") if f.exposure_pct is not None else ""
    ret_txt = f" · **{brief.window_label} {f.return_window_pct:+.1f}%**" if f.return_window_pct is not None else ""
    if ret_txt and f.relative_to_benchmark_pct is not None and bench_label:
        rel = f.relative_to_benchmark_pct
        ret_txt += f" (**{abs(rel):.1f} pts** {'ahead of' if rel >= 0 else 'behind'} {bench_label})"
    status = _status_tag(f)
    head = f"**{name}**{exp_txt}{ret_txt}"
    body = "; ".join(x for x in (status, why.strip().rstrip(".")) if x)
    return f"{head} — {body}." if body else f"{head}."


def _funds_intro(
    findings: Findings,
    sector_label: str,
    shown: list[FundFinding],
    has_sector: bool = True,
    fund_focus: bool = False,
) -> str:
    exps = [f.exposure_pct for f in shown if f.exposure_pct is not None]
    if fund_focus:
        return "Return over the window, what the fund holds, and the news that touches those holdings."
    if not has_sector:
        return "Funds with the largest weight in the sectors named above."
    if exps:
        return (
            f"Top **{len(shown)}** funds by **{sector_label}** weight (**{min(exps):.0f}%** to **{max(exps):.0f}%**), "
            "each read against what the news says."
        )
    return f"**{len(shown)}** funds most relevant to this question, each read against what the news says."


def _caveat(evidence: EvidenceSet | None) -> str:
    notes: list[str] = []
    for e in evidence.ledger if evidence else []:
        if e.status == "unavailable" and e.facet == "benchmark":
            notes.append("The sector index return was unavailable in this run.")
        if e.status == "unavailable" and e.facet == "return_series":
            notes.append("Fund return history was unavailable for some funds.")
    return notes[0] if notes else ""


def _driver_sentence(s: SectorFinding | None) -> str:
    if not s:
        return ""
    if s.tone_reason:
        line = polish_insight_sentence(s.tone_reason, max_chars=220).rstrip(".")
        if line:
            return line
    if s.news_themes:
        return ", ".join(str(t).strip() for t in s.news_themes[:3] if str(t).strip())
    if s.claims:
        return str(s.claims[0].get("text") or "").strip().rstrip(".")
    return ""


def _sector_names_bold(rows: list[dict[str, Any]], limit: int = 3) -> str:
    return ", ".join(f"**{str(x.get('name') or '').strip()}**" for x in rows[:limit] if x.get("name"))


def _sector_why_phrase(rows: list[dict[str, Any]], limit: int = 2) -> str:
    bits: list[str] = []
    for row in rows[:limit]:
        r = polish_insight_sentence(str(row.get("reason") or ""), max_chars=100).rstrip(".")
        if r:
            bits.append(r)
    if not bits:
        return ""
    if len(bits) == 1:
        return bits[0]
    return f"{bits[0]}; {bits[1]}"


def _structured_closing(findings: Findings, brief: QuestionBrief | None = None, question: str = "") -> str:
    s = findings.sector
    drivers = _driver_sentence(s)
    tone_word = {"positive": "positive", "negative": "negative", "mixed": "mixed"}.get(
        (s.tone if s else "") or "", ""
    )

    if brief and brief.primary_sector() and s and not asks_sector_lists(question, brief):
        label = brief.primary_sector()
        parts: list[str] = []
        if tone_word and drivers:
            parts.append(f"**{label}** news is **{tone_word}**: {drivers}.")
        elif tone_word:
            parts.append(f"**{label}** news reads **{tone_word}**.")
        if s.index_return_pct is not None:
            bench = s.benchmark_label or label
            parts.append(
                f"Over **{brief.window_label if brief else 'the window'}**, **{bench}** is **{s.index_return_pct:+.1f}%**."
            )
        shown = _shown_funds(findings)[:3]
        if shown:
            bits = []
            for f in shown:
                weight = f" ({f.exposure_pct:.0f}%)" if f.exposure_pct is not None else ""
                bits.append(f"**{_short_fund_name(f.fund_name)}**{weight}")
            parts.append("Heaviest weights: " + ", ".join(bits) + ".")
        return " ".join(parts)

    if not findings.funds and s and (s.sectors_negative or s.sectors_positive):
        parts: list[str] = []
        if drivers:
            parts.append(f"**Why the market feels tense:** {drivers}.")
        hurt_rows = list(s.sectors_negative)
        help_rows = list(s.sectors_positive)
        if brief and (brief.direction or "").lower() == "positive":
            hurt_rows = []
        elif brief and (brief.direction or "").lower() == "negative":
            help_rows = []
        hurt_names = _sector_names_bold(hurt_rows, 4)
        help_names = _sector_names_bold(help_rows, 3)
        hurt_why = _sector_why_phrase(hurt_rows, 2)
        help_why = _sector_why_phrase(help_rows, 2)
        if hurt_names:
            line = f"**Under pressure:** {hurt_names}"
            if hurt_why:
                line += f" — {hurt_why}."
            else:
                line += "."
            parts.append(line)
        if help_names:
            line = f"**Relatively better placed:** {help_names}"
            if help_why:
                line += f" — {help_why}."
            else:
                line += "."
            parts.append(line)
        return " ".join(parts)

    tail = [_short_fund_name(f.fund_name) for f in findings.funds if f.news_tilt == "tailwind"][:3]
    head = [_short_fund_name(f.fund_name) for f in findings.funds if f.news_tilt == "headwind"][:3]
    parts: list[str] = []
    if drivers:
        parts.append(f"**Why it matters:** {drivers}.")
    bits: list[str] = []
    if head:
        bits.append("**headwind** from the news: " + ", ".join(f"**{n}**" for n in head))
    if tail:
        bits.append("**tailwind**: " + ", ".join(f"**{n}**" for n in tail))
    if bits:
        parts.append("Among these funds, " + "; ".join(bits) + ".")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def _period(label: str) -> str:
    text = (label or "the period").strip()
    return re.sub(r"\b1 months\b", "1 month", text)


def _signed(v: Any) -> str:
    return f"**{float(v):+.1f}%**" if isinstance(v, (int, float)) else ""


def _down_up(v: Any) -> str:
    if not isinstance(v, (int, float)):
        return ""
    word = "down" if v < 0 else "up"
    return f"**{word} {abs(float(v)):.1f}%**"


def _same_way(a: Any, b: Any) -> bool | None:
    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return None
    if abs(a) < 0.4 or abs(b) < 0.4:
        return None
    return (a < 0 and b < 0) or (a > 0 and b > 0)


def _factor(raw: str) -> str:
    """One complete cause. Drop chopped scraps, bylines, and publisher lines."""
    from news_rag.insight.grounding import strip_media_attribution
    from news_rag.snippet_clean import clean_scraped_snippet

    text = strip_media_attribution(clean_scraped_snippet(raw or ""))
    text = re.sub(r"\b(?:TV18|CNBC-TV18|Moneycontrol|Published|Listen to this article)\b", " ", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < 70 or text.endswith("..") or "share price opened" in text.lower():
        return ""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if len(p.strip()) > 55]
    if not parts:
        return ""
    sentence = parts[0]
    if not re.match(r"^[A-Z]", sentence):
        return ""
    if re.search(
        r"\b(shares? jump|target raised|published|listen|matrix of macro|must try and make sense)\b",
        sentence,
        re.I,
    ):
        return ""
    return sentence


def _top_sectors_by_weight(f: FundFinding, limit: int = 3) -> list[dict[str, Any]]:
    rows = [s for s in (f.sector_mix or []) if isinstance(s, dict) and s.get("sector")]
    rows.sort(key=lambda s: -float(s.get("percentage") or 0))
    return rows[:limit]


def _claim_matches_sector(claim_text: str, sector: str, fund: FundFinding | None = None) -> bool:
    from news_rag.insight.article_quality import claim_matches_label

    extra: set[str] = set()
    if fund:
        for h in fund.top_holdings or []:
            if not isinstance(h, dict):
                continue
            sec = str(h.get("sector") or "").strip().lower()
            label = (sector or "").strip().lower()
            if sec and label and (sec == label or sec in label or label in sec):
                extra |= {t for t in re.findall(r"[a-z]{3,}", str(h.get("name") or "").lower())}
    return claim_matches_label(claim_text, sector, extra)


def _format_claim_bullet(c: dict[str, Any], *, label: str = "") -> str:
    text = polish_insight_sentence(str(c.get("text") or ""), max_chars=_INSIGHT_TEXT_CAP).rstrip(".")
    if not text or not article_text_usable(text) or starts_mid_sentence(text):
        return ""
    prefix = f"**{label}:** " if label else ""
    return f"• {prefix}{text}"


def _diverse_news_bullets(
    findings: Findings,
    f: FundFinding,
    brief: QuestionBrief | None = None,
    *,
    limit: int = 0,
) -> tuple[list[str], set[int]]:
    """One bullet per portfolio sleeve + macro — avoid repeating the same story."""
    s = findings.sector
    if not s or not s.claims:
        return [], set()
    claims = list(s.claims)
    cap = limit if limit > 0 else len(claims)
    sector_order: list[str] = []
    for d in f.drag_sectors[:4]:
        name = str(d.get("sector") or "").strip()
        if name and name not in sector_order:
            sector_order.append(name)
    for row in _top_sectors_by_weight(f, 5):
        name = str(row.get("sector") or "").strip()
        if name and name not in sector_order:
            sector_order.append(name)

    lines: list[str] = []
    used: set[int] = set()
    for sec in sector_order:
        if len(lines) >= cap:
            break
        for i, c in enumerate(claims):
            if i in used:
                continue
            if _claim_matches_sector(str(c.get("text") or ""), sec, f):
                line = _format_claim_bullet(c, label=sec)
                if line:
                    lines.append(line)
                    used.add(i)
                break

    if brief and brief.drivers:
        driver_terms: set[str] = set()
        for d in brief.drivers:
            driver_terms |= {t for t in re.findall(r"[a-z]{3,}", str(d).replace("_", " ").lower())}
        for i, c in enumerate(claims):
            if len(lines) >= cap or i in used:
                continue
            text = str(c.get("text") or "").lower()
            if driver_terms and any(t in text for t in driver_terms):
                label = "Drivers: " + ", ".join(d.replace("_", " ") for d in brief.drivers[:2])
                line = _format_claim_bullet(c, label=label)
                if line:
                    lines.append(line)
                    used.add(i)

    for i, c in enumerate(claims):
        if len(lines) >= cap or i in used:
            continue
        line = _format_claim_bullet(c)
        if line:
            lines.append(line)
            used.add(i)
    return lines, used


def _claim_for_sector(
    findings: Findings, sector: str, *, skip_indices: set[int] | None = None
) -> tuple[str, int | None]:
    skip = skip_indices or set()
    key = (sector or "").strip().lower()
    if not key:
        return "", None
    for i, c in enumerate(findings.sector.claims if findings.sector else []):
        if i in skip:
            continue
        text = str(c.get("text") or "")
        if _claim_matches_sector(text, sector):
            polished = polish_insight_sentence(text, max_chars=_INSIGHT_TEXT_CAP).rstrip(".")
            if polished:
                return polished, i
    return "", None


def _holding_story(drag: dict[str, Any]) -> str:
    for h in drag.get("holdings") or []:
        if not isinstance(h, dict) or not h.get("name"):
            continue
        story = _factor(str(h.get("news") or ""))
        if story:
            wt = float(h.get("weight_pct") or 0)
            wt_bit = f" ({wt:.1f}% of the fund)" if wt else ""
            return f"**{h.get('name')}**{wt_bit}: {story.rstrip('.')}."
    return ""


def _named_fund_snapshot(brief: QuestionBrief, f: FundFinding) -> list[str]:
    """NAV, recent return, largest sleeves — no index laundry list."""
    lines: list[str] = []
    name = _short_fund_name(f.fund_name)
    period = _period(brief.window_label)
    move = _down_up(f.return_window_pct) or "little changed"
    if f.nav is not None:
        date_bit = f" (as of **{f.nav_date}**)" if f.nav_date else ""
        lines.append(f"**Latest NAV:** **₹{f.nav:.2f}**{date_bit}.")
    if f.return_window_pct is not None:
        lines.append(f"**Recent move:** {move} over the last **{period}**.")
    if f.scheme_benchmark and not f.benchmark_return_pct:
        lines.append(f"**Stated benchmark:** {f.scheme_benchmark} (index return not in our feed for this window).")
    top_sec = _top_sectors_by_weight(f, 3)
    if top_sec:
        mix = ", ".join(
            f"**{s.get('sector')}** {float(s.get('percentage') or 0):.0f}%"
            for s in top_sec
        )
        lines.append(f"**Largest sector weights:** {mix}.")
    if f.top_holdings:
        holds = ", ".join(
            f"**{h.get('name')}** ({float(h.get('percentage') or 0):.1f}%)"
            for h in f.top_holdings[:5]
            if h.get("name")
        )
        if holds:
            lines.append(f"**Top holdings:** {holds}.")
    return lines


def _fund_why_narrative(brief: QuestionBrief, findings: Findings) -> str:
    """News-led insight: snapshot, diverse news, then portfolio sleeves (no duplicate bullets)."""
    blocks: list[str] = []
    for f in findings.funds[:1]:
        blocks.append("### At a glance\n")
        blocks.extend(_named_fund_snapshot(brief, f))
        blocks.append("")

        news_lines, used_claims = _diverse_news_bullets(findings, f, brief)
        if news_lines:
            blocks.append("### What the news is saying\n")
            blocks.extend(news_lines)
            blocks.append("")

        drags = list(f.drag_sectors[:3])
        if len(drags) < 2 and f.sector_mix:
            seen = {str(d.get("sector")) for d in drags}
            for s in _top_sectors_by_weight(f, 4):
                name = str(s.get("sector") or "")
                if name and name not in seen:
                    drags.append(
                        {
                            "sector": name,
                            "weight_pct": s.get("percentage"),
                            "index_return_pct": s.get("index_return_pct"),
                            "index_label": s.get("index_label"),
                            "news": "",
                            "holdings": [],
                        }
                    )
                    seen.add(name)
                if len(drags) >= 3:
                    break

        if drags:
            blocks.append("### How this maps to the portfolio\n")
            for drag in drags[:3]:
                sector = str(drag.get("sector") or "").strip()
                if not sector:
                    continue
                weight = float(drag.get("weight_pct") or 0)
                blocks.append(f"**{sector}** — about **{weight:.0f}%** of the fund.")
                hold_line = _holding_story(drag)
                if hold_line:
                    blocks.append(hold_line)
                    blocks.append("")
                    continue
                extra, idx = _claim_for_sector(findings, sector, skip_indices=used_claims)
                if extra:
                    blocks.append(extra.rstrip(".") + ".")
                    if idx is not None:
                        used_claims.add(idx)
                elif _factor(str(drag.get("news") or "")):
                    blocks.append(_factor(str(drag.get("news") or "")).rstrip(".") + ".")
                else:
                    idx_v = drag.get("index_return_pct")
                    if isinstance(idx_v, (int, float)):
                        blocks.append(
                            f"The sector index moved {_down_up(idx_v)} in this window — "
                            f"combine that with the **{sector}** headline above."
                        )
                    else:
                        blocks.append(
                            f"News for **{sector}** is in the section above; the weight means it can sway the fund."
                        )
                blocks.append("")
    return "\n".join(blocks).strip()


def _fund_why_headline(brief: QuestionBrief, findings: Findings) -> str:
    f = findings.funds[0] if findings.funds else None
    if not f:
        return ""
    name = _short_fund_name(f.fund_name)
    move = _down_up(f.return_window_pct) or "little changed"
    nav = ""
    if f.nav is not None:
        nav = f" — NAV **₹{f.nav:.2f}**" + (f" (**{f.nav_date}**)" if f.nav_date else "")
    lead_sector = ""
    names: list[str] = []
    for d in f.drag_sectors[:3]:
        sec = str(d.get("sector") or "").strip()
        if sec and sec not in names:
            names.append(sec)
    if not names:
        names = [str(s.get("sector")) for s in _top_sectors_by_weight(f, 3) if s.get("sector")]
    if names:
        joined = ", ".join(f"**{n}**" for n in names[:3])
        lead_sector = f" Largest sleeves in the story: {joined}."
    return (
        f"**{name}**{nav} is {move} over **{_period(brief.window_label)}**."
        + lead_sector
    )


def _fund_why_closing(brief: QuestionBrief, findings: Findings) -> str:
    f = findings.funds[0] if findings.funds else None
    s = findings.sector
    if not f:
        return ""
    period = _period(brief.window_label)
    move = _down_up(f.return_window_pct) or "moved"
    sleeves = ", ".join(
        f"**{str(d.get('sector'))}** ({float(d.get('weight_pct') or 0):.0f}%)"
        for d in f.drag_sectors[:3]
        if d.get("sector")
    )
    tone = (s.tone_reason if s else "") or ""
    tone = polish_insight_sentence(tone, max_chars=_INSIGHT_TEXT_CAP).rstrip(".") if tone else ""
    if tone and not re.search(r"not in the data|holdings and returns are not", tone, re.I):
        return f"**Bottom line:** Over **{period}** the fund {move}. {tone}."
    if sleeves:
        return (
            f"**Bottom line:** Over **{period}** the fund {move}. "
            f"The story is spread across {sleeves} — read the news bullets by theme rather than one single driver."
        )
    return (
        f"**Bottom line:** Over **{period}** the fund {move}; the mix of sector and macro headlines above "
        "is a better guide than any one line item."
    )


def _assemble(
    brief: QuestionBrief,
    findings: Findings,
    evidence: EvidenceSet,
    *,
    question: str = "",
    headline: str,
    sector_read: str,
    fund_lines: dict[str, str],
    closing: str,
) -> ComposedInsight:
    s = findings.sector
    sector_label = (s.sector_label if s else "") or brief.primary_sector() or "Sector"
    has_sector = bool(brief.primary_sector())
    fund_focus = bool(brief.funds) and not has_sector and not brief.drivers
    sector_title = "**What changed**" if brief.drivers else (
        "**Sector health**" if has_sector else "**What the news says**"
    )
    why_block = _fund_why_narrative(brief, findings) if fund_focus else ""
    if why_block:
        headline = _fund_why_headline(brief, findings) or headline
        closing = _fund_why_closing(brief, findings) or closing

    sector_block: list[str] = []
    if not why_block and (sector_read or "").strip():
        sector_block = [sector_title, "", sector_read]
    idx = _index_line(brief, findings)
    if idx:
        sector_block += ["", idx]
    lists = ""
    if not why_block and not has_sector and s and (s.sectors_negative or s.sectors_positive):
        emphasize = asks_sector_lists(question, brief) or brief.direction == "negative"
        side = brief.direction if brief.direction in ("positive", "negative") else "both"
        lists = _sector_lists_block(s, emphasize_down=emphasize, side=side)
        if lists:
            sector_block += ["", lists]
    market = asks_market_briefing(question) and not brief.funds
    if not why_block and s and s.claims and not has_sector and not brief.wants_funds() and not market:
        key_facts = [
            t for t in (polish_insight_sentence(str(c.get("text") or ""), max_chars=200) for c in s.claims[:6])
            if t and article_text_usable(t) and not starts_mid_sentence(t)
        ][:3]
        if key_facts:
            sector_block += ["", "**Key facts**", "", "\n".join(f"- {t}" for t in key_facts)]
    narrative_blocks = [why_block] if why_block else ["\n".join(sector_block).strip()]

    shown = _shown_funds(findings, question, brief)
    fund_lines = _unique_fund_lines(fund_lines)
    bullets: list[str] = []
    bench_label = ""
    if has_sector and s and s.index_return_pct is not None:
        bench_label = "**Nifty 50**" if any(l.code == "benchmark_substitute" for l in findings.limits) else (
            f"**{s.benchmark_label}**" if s.benchmark_label else ""
        )
    if shown and not why_block:
        for f in shown:
            bullets.append(_fund_bullet(f, brief, sector_label, fund_lines.get(f.isin, ""), bench_label))
        funds_title = (
            "**Funds with the most exposure**"
            if brief.direction in ("positive", "negative")
            else "**Funds most exposed**"
        )
        narrative_blocks.append(
            f"{funds_title}\n\n{_funds_intro(findings, sector_label, shown, has_sector, fund_focus)}"
        )
    elif brief.wants_funds() and not why_block:
        narrative_blocks.append(
            f"**Funds with the most exposure**\n\nNo funds with meaningful **{sector_label}** exposure showed up in the data."
        )

    narrative = "\n\n".join(b for b in narrative_blocks if b)
    caveat = _caveat(evidence)
    closing_full = " ".join(x for x in (closing.strip(), caveat) if x)
    closing_full = (closing_full + " " if closing_full else "") + "For context only — not investment advice."

    headline, narrative, bullets, closing_full = finalize_text_fields(
        headline, narrative, bullets, closing_full, findings.evidence_text
    )
    display = "\n\n".join(
        p for p in [headline, narrative, "\n".join(f"• {b}" for b in bullets), closing_full] if p
    )
    display = _drop_pipeline_voice(display)
    return ComposedInsight(
        headline=headline,
        narrative=narrative,
        bullets=bullets,
        closing_summary=closing_full,
        display=display.strip(),
        sub_ask_coverage=[a.text for a in sorted(brief.sub_asks, key=lambda a: a.order or 0)],
    )


_PIPELINE_VOICE = re.compile(
    r"facts packet|structured facts|no fund isin|holdings were not|were not supplied|"
    r"retrieval implementation|backend processing|average tagged impact",
    re.I,
)


def _drop_pipeline_voice(text: str) -> str:
    kept: list[str] = []
    for para in re.split(r"\n\s*\n", text or ""):
        if _PIPELINE_VOICE.search(para):
            continue
        kept.append(para)
    return "\n\n".join(kept).strip()


def _clean_market_claims(findings: Findings) -> list[str]:
    s = findings.sector
    if not s:
        return []
    out: list[str] = []
    for c in s.claims:
        raw = str(c.get("text") or "")
        line = polish_insight_sentence(raw, max_chars=220)
        if not line or starts_mid_sentence(line) or not article_text_usable(line):
            continue
        if re.search(r"\d+\s+of the\s+\d+\s+articles", line, re.I):
            continue
        out.append(line.rstrip("."))
        if len(out) >= 4:
            break
    return out


def _market_briefing_compose(
    question: str, brief: QuestionBrief, findings: Findings, evidence: EvidenceSet
) -> ComposedInsight:
    window = brief.window_label or "the recent window"
    claims = _clean_market_claims(findings)
    s = findings.sector
    tone_word = {"positive": "positive", "negative": "negative", "mixed": "mixed"}.get(
        (s.tone if s else "") or "", ""
    )
    idx = ""
    if s and s.index_return_pct is not None:
        idx = f" The broad market index is **{s.index_return_pct:+.1f}%** over **{window}**."
    reason = polish_insight_sentence(str(s.tone_reason or ""), max_chars=240) if s else ""
    if reason and re.search(r"\d+\s+of the\s+\d+\s+articles", reason, re.I):
        reason = ""
    themes = [str(t).strip() for t in ((s.news_themes if s else None) or []) if str(t).strip()][:4]

    if reason:
        lead = reason.rstrip(".") + "."
    elif claims:
        lead = claims[0].rstrip(".") + "."
    elif themes:
        lead = f"The main themes in the news are {', '.join(themes)}."
    else:
        lead = f"News flow over **{window}** points to a market driven by a few macro themes."
    tone_bit = f" Overall tone: **{tone_word}**." if tone_word else ""
    headline = f"**Indian market.** {lead}{tone_bit}{idx}"

    drivers = [c for c in claims if c.rstrip(".") not in lead][:4]
    blocks: list[str] = []
    if drivers or themes:
        lines = [f"- {d}." for d in drivers]
        if themes and not drivers:
            lines = [f"- {t}" for t in themes]
        blocks.append("### What drove the market\n\n" + "\n".join(lines))

    sector_lines: list[str] = []
    if s:
        for title, rows in (("Under pressure", s.sectors_negative), ("Holding up better", s.sectors_positive)):
            items = []
            for x in (rows or [])[:5]:
                name = str(x.get("name") or "").strip()
                if not name:
                    continue
                why = polish_insight_sentence(str(x.get("reason") or ""), max_chars=160).rstrip(".")
                items.append(f"- **{name}**" + (f" — {why}" if why else ""))
            if items:
                sector_lines.append(f"**{title}**\n" + "\n".join(items))
    if sector_lines:
        blocks.append(
            "### Sector impact\n\n" + "\n\n".join(sector_lines)
            + "\n\nTreat these as likely channels (funding cost, bond values, input costs, foreign flows), "
            "not proof of what caused the whole move."
        )

    if not blocks:
        blocks.append(
            "### What to watch\n\nBond yields, banking-system liquidity, the rupee and foreign investment flows."
        )
    sector_read = "\n\n".join(blocks)
    def _names(rows) -> str:
        return ", ".join(str(x.get("name")) for x in (rows or [])[:3] if x.get("name"))

    bits = []
    if s and _names(s.sectors_negative):
        bits.append(f"Most under pressure: {_names(s.sectors_negative)}.")
    if s and _names(s.sectors_positive):
        bits.append(f"Holding up better: {_names(s.sectors_positive)}.")
    if not findings.funds:
        bits.append("Fund-level impact needs a named scheme.")
    closing = " ".join(bits)
    out = _assemble(
        brief,
        findings,
        evidence,
        question=question,
        headline=headline,
        sector_read=sector_read,
        fund_lines={},
        closing=closing,
    )
    out.answer_trace = {"mode": "market_briefing"}
    return out


def _stock_quote(evidence: EvidenceSet | None, brief: QuestionBrief) -> dict[str, Any] | None:
    if not evidence:
        return None
    for item in evidence.items:
        data = item.data if isinstance(item.data, dict) else {}
        if item.facet != "stock_price" or data.get("cmp") is None:
            continue
        name = (brief.stocks[0] if brief.stocks else "") or str(data.get("ticker") or "Stock")
        return {
            "name": name,
            "ticker": data.get("ticker"),
            "price_inr": data.get("cmp"),
            "return_1d_pct": data.get("return_1d"),
            "return_1w_pct": data.get("return_1w"),
            "return_1m_pct": data.get("return_1m"),
        }
    return None


def _structured_compose(
    question: str, brief: QuestionBrief, findings: Findings, evidence: EvidenceSet
) -> ComposedInsight:
    if asks_market_briefing(question) and not brief.funds and not findings.funds:
        out = _market_briefing_compose(question, brief, findings, evidence)
        return out
    quote = _stock_quote(evidence, brief)
    if quote and not findings.funds:
        price = quote.get("price_inr")
        day = quote.get("return_1d_pct")
        month = quote.get("return_1m_pct")
        day_txt = f" One-day move **{float(day):+.1f}%**." if isinstance(day, (int, float)) else ""
        month_txt = f" One-month move **{float(month):+.1f}%**." if isinstance(month, (int, float)) else ""
        headline = f"**{quote['name']}** last traded at **₹{price}**."
        sector_read = f"Last close **₹{price}**.{day_txt}{month_txt}"
        out = _assemble(
            brief,
            findings,
            evidence,
            question=question,
            headline=headline,
            sector_read=sector_read,
            fund_lines={},
            closing="Price is the latest close we could fetch. For context only — not investment advice.",
        )
        out.answer_trace = {"mode": "stock_price", "stock": quote}
        return out
    shown = _shown_funds(findings, question, brief)
    out = _assemble(
        brief,
        findings,
        evidence,
        question=question,
        headline=_structured_headline(brief, findings),
        sector_read=_structured_sector_read(findings) or "Not enough news in this run to judge the sector.",
        fund_lines={f.isin: _structured_fund_line(f) for f in shown},
        closing=_structured_closing(findings, brief, question),
    )
    out.answer_trace = {"mode": "structured", "findings": findings.to_dict()}
    return out


# ---------------------------------------------------------------------------
# LLM facts + hybrid compose
# ---------------------------------------------------------------------------


def _article_context_for_interpret(
    evidence: EvidenceSet | None,
    brief: QuestionBrief | None = None,
    *,
    question: str = "",
    limit: int | None = None,
) -> list[dict[str, str]]:
    if not evidence or not evidence.articles:
        return []
    from news_rag.insight.news_reader import _body, select_articles

    settings = get_settings()
    cap = limit or int(getattr(settings, "insight_composer_max_articles", 8))
    arts = select_articles(
        evidence.articles,
        limit=cap,
        brief=brief,
        evidence=evidence,
        question=question,
    )
    out: list[dict[str, str]] = []
    for i, art in enumerate(arts, 1):
        body = _body(art)
        if not body:
            continue
        out.append(
            {
                "index": i,
                "title": str(art.get("title") or "").strip(),
                "impact": art.get("max_impact"),
                "direction": art.get("direction"),
                "body": body,
            }
        )
    return out


def _named_fund_llm_packet(
    question: str,
    brief: QuestionBrief,
    findings: Findings,
    evidence: EvidenceSet,
    news_read: Any = None,
    analysis_brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet = _facts(question, brief, findings, evidence)
    packet["measured_facts"] = measured_facts_block(brief, evidence)
    packet["full_articles"] = _article_context_for_interpret(evidence, brief, question=question)
    packet["cross_cutting"] = list(findings.cross_cutting)
    if news_read is not None:
        packet["news_reader"] = {
            "tone": news_read.tone,
            "tone_reason": news_read.tone_reason,
            "net_read": getattr(news_read, "net_read", "") or "",
            "conflicts": list(getattr(news_read, "conflicts", []) or []),
            "themes": list(news_read.themes or []),
            "claims": [
                {"text": c.text, "sentiment": c.sentiment, "article": c.article}
                for c in (news_read.claims or [])
            ],
            "sectors_positive": [{"name": s.name, "reason": s.reason} for s in news_read.sectors_positive],
            "sectors_negative": [{"name": s.name, "reason": s.reason} for s in news_read.sectors_negative],
        }
    if analysis_brief:
        packet["analysis_brief"] = analysis_brief
    return packet


def _named_fund_block(evidence: EvidenceSet) -> dict[str, Any]:
    for item in evidence.by_facet("fund_attribution"):
        funds = (item.data or {}).get("funds") if isinstance(item.data, dict) else None
        if funds and isinstance(funds[0], dict):
            return funds[0]
    return {}


_META_SENTENCE = re.compile(
    r"[^.!?\n]*(in the data|the facts do not|per the fund'?s records|cannot be settled from this data)[^.!?\n]*[.!?]?",
    re.I,
)


def _strip_meta_language(text: str) -> str:
    cleaned = _META_SENTENCE.sub("", text or "")
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _ensure_attribution_table(text: str, block: dict[str, Any]) -> str:
    from news_rag.insight.holding_attribution import render_attribution_table

    attr = block.get("attribution") if isinstance(block.get("attribution"), dict) else {}
    if not attr or not attr.get("rows"):
        return text
    table = render_attribution_table(attr)
    if "| Holding |" in (text or ""):
        return text
    parts = (text or "").split("\n", 1)
    head = parts[0].strip()
    rest = parts[1].strip() if len(parts) > 1 else ""
    return f"{head}\n\n{table}\n\n{rest}".strip()


def _named_fund_llm_compose(
    question: str,
    brief: QuestionBrief,
    findings: Findings,
    evidence: EvidenceSet,
    structured: ComposedInsight,
    *,
    news_read: Any = None,
    query_log: Any = None,
    pipeline_errors: list[dict[str, str]] | None = None,
    analysis_brief: dict[str, Any] | None = None,
) -> ComposedInsight | None:
    block = _named_fund_block(evidence)
    attr = block.get("attribution") if isinstance(block.get("attribution"), dict) else {}
    if attr.get("rows"):
        from news_rag.insight.holding_attribution import render_investor_answer

        fund = findings.funds[0] if findings.funds else None
        text = render_investor_answer(
            fund_name=_short_fund_name(getattr(fund, "fund_name", "") or block.get("fund_name") or (brief.funds[0] if brief.funds else "The fund")),
            window_label=str(block.get("window_label") or brief.window_label or ""),
            attr=attr,
            benchmark_name=str(getattr(fund, "scheme_benchmark", "") or ""),
            benchmark_return_pct=getattr(fund, "benchmark_return_pct", None),
            alternate_return_pct=block.get("alternate_return_pct"),
        )
        headline = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        if query_log is not None:
            query_log.write("INTERPRET mode=named_fund_attribution")
        return ComposedInsight(
            headline=headline,
            narrative=text,
            bullets=[],
            closing_summary="",
            display=text,
            sub_ask_coverage=[a.text for a in sorted(brief.sub_asks, key=lambda a: a.order or 0)],
            answer_trace={
                "mode": "named_fund_attribution",
                "structured": {
                    "headline": headline,
                    "fund_return_pct": attr.get("fund_return_pct"),
                    "window_label": block.get("window_label") or brief.window_label,
                    "drivers": attr.get("detractors"),
                    "offsets": attr.get("contributors"),
                    "unexplained_pct": attr.get("unexplained_pct"),
                    "explained_pct": attr.get("explained_pct"),
                    "benchmark": {
                        "name": getattr(fund, "scheme_benchmark", "") if fund else "",
                        "return_pct": getattr(fund, "benchmark_return_pct", None) if fund else None,
                    },
                    "data_quality_notes": (
                        [f"alternate_return_pct={block.get('alternate_return_pct')}"]
                        if block.get("alternate_return_pct") is not None
                        else []
                    ),
                },
            },
        )

    settings = get_settings()
    if not llm_api_key_configured(settings):
        return None
    packet = _named_fund_llm_packet(
        question, brief, findings, evidence, news_read, analysis_brief
    )
    block = _named_fund_block(evidence)
    from news_rag.insight.holding_attribution import render_attribution_table

    attr = block.get("attribution") if isinstance(block.get("attribution"), dict) else {}
    table = render_attribution_table(attr) if attr else ""
    user = _composer_user_content(packet, analysis_brief)
    user += (
        "\n\nHOLDING_ATTRIBUTION:\n"
        + json.dumps(
            {
                "fund_return_pct": block.get("fund_return_pct"),
                "window_label": block.get("window_label"),
                "return_notes": block.get("return_notes"),
                "detractors": attr.get("detractors"),
                "contributors": attr.get("contributors"),
                "explained_pct": attr.get("explained_pct"),
                "unexplained_pct": attr.get("unexplained_pct"),
                "top_sector": attr.get("top_sector"),
                "top_sector_weight_pct": attr.get("top_sector_weight_pct"),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n\nATTRIBUTION_TABLE:\n"
        + table
        + "\n\nCONCENTRATION: "
        + (
            f"{attr.get('top_sector')} is {float(attr.get('top_sector_weight_pct') or 0):.2f}% of the holdings priced."
            if attr.get("top_sector")
            else "Concentration not available."
        )
        + "\n\nNarrate HOLDING_ATTRIBUTION. Keep ATTRIBUTION_TABLE unchanged. "
        "Do not call a sector the main drag unless its stocks are the largest detractors."
    )
    try:
        res = call_insight_llm(
            system_prompt=build_named_fund_composer_prompt(),
            user_content=user,
            model_override=composer_model(settings),
            max_tokens=4500,
            temperature=0.2,
            query_log=query_log,
        )
    except Exception as exc:  # noqa: BLE001
        _pipeline_note(pipeline_errors, "compose", str(exc))
        return None
    text = ((res.raw_text if res else "") or "").strip()
    if len(text) < 80:
        return None
    text = re.sub(r"```json.*?```", "", text, flags=re.S).strip()
    text = _strip_meta_language(text)
    text = _ensure_attribution_table(text, block)
    violations = check_composer_guardrails(text, packet, findings.evidence_text)
    if violations:
        text = scrub_composer_text(text, packet, findings.evidence_text)
    text = _drop_pipeline_voice(strip_media_attribution(text))
    if "not investment advice" not in text.lower():
        text = text.rstrip() + "\n\n*For context only — not investment advice.*"
    headline = structured.headline
    for line in text.splitlines():
        if line.strip():
            headline = line.lstrip("#").strip()
            break
    return ComposedInsight(
        headline=headline,
        narrative=text,
        bullets=[],
        closing_summary="",
        display=text,
        sub_ask_coverage=[a.text for a in sorted(brief.sub_asks, key=lambda a: a.order or 0)],
        answer_trace={
            "mode": "named_fund_llm",
            "findings": findings.to_dict(),
            "structured": {
                "headline": headline,
                "fund_return_pct": block.get("fund_return_pct"),
                "window_label": block.get("window_label"),
                "drivers": attr.get("detractors"),
                "offsets": attr.get("contributors"),
                "unexplained_pct": attr.get("unexplained_pct"),
                "explained_pct": attr.get("explained_pct"),
                "benchmark": packet.get("benchmark"),
                "data_quality_notes": block.get("return_notes") or [],
                "concentration": {
                    "top_sector": attr.get("top_sector"),
                    "top_sector_weight_pct": attr.get("top_sector_weight_pct"),
                },
            },
        },
    )


def _fund_why_compose(
    question: str, brief: QuestionBrief, findings: Findings, evidence: EvidenceSet
) -> ComposedInsight:
    return _structured_compose(question, brief, findings, evidence)


def _facts(
    question: str,
    brief: QuestionBrief,
    findings: Findings,
    evidence: EvidenceSet | None = None,
) -> dict[str, Any]:
    s = findings.sector
    list_dir = (brief.direction or "any").strip().lower()
    if list_dir not in ("positive", "negative"):
        list_dir = "any"
    facts: dict[str, Any] = {
        "question": question,
        "intent": getattr(brief, "intent", "why_down"),
        "tone": getattr(brief, "tone", "neutral"),
        "list_direction": list_dir,
        "drivers": list(brief.drivers),
        "window": brief.window_label,
        "benchmark": {
            "name": getattr(brief, "benchmark", "") or (s.benchmark_label if s else "Nifty 50"),
            "return_pct": round(s.index_return_pct, 2) if (s and s.index_return_pct is not None) else None,
        },
        "sector": None,
        "funds": [],
        "missing_data": [],
        "article_context": _article_context_for_interpret(evidence, brief, question=question),
        "measured_facts": measured_facts_block(brief, evidence),
        "stock": _stock_quote(evidence, brief),
    }
    if s:
        facts["sector"] = {
            "label": brief.primary_sector() or s.sector_label,
            "driver": ", ".join(brief.drivers),
            "asks_sector_lists": asks_sector_lists(question, brief),
            "tone": s.tone,
            "tone_reason": s.tone_reason,
            "summary": s.executive_summary,
            "return_pct": round(s.index_return_pct, 2) if s.index_return_pct is not None else None,
            "index": (
                {
                    "name": s.benchmark_label,
                    "return_pct": round(s.index_return_pct, 2),
                    "is_sector_index": not any(l.code == "benchmark_substitute" for l in findings.limits),
                }
                if s.index_return_pct is not None
                else None
            ),
            "claims": [
                {"id": c.get("id"), "text": c.get("text"), "sentiment": c.get("sentiment")}
                for c in s.claims
                if article_text_usable(str(c.get("text") or "")) and not starts_mid_sentence(str(c.get("text") or ""))
            ],
            "sectors_helped": (
                s.sectors_positive
                if list_dir != "negative"
                else []
            ),
            "sectors_hurt": (
                s.sectors_negative
                if list_dir != "positive"
                else []
            ),
        }
    for f in _shown_funds(findings, question, brief):
        facts["funds"].append(
            {
                "isin": f.isin,
                "name": _short_fund_name(f.fund_name),
                "full_name": f.fund_name,
                "return_pct": f.return_window_pct,
                "relative_to_benchmark_pct": f.relative_to_benchmark_pct,
                "picked_for_sector": f.exposure_sector,
                "exposure_pct": f.exposure_pct,
                "top_holdings": f.top_holdings[:5],
                "sector_mix": f.sector_mix,
                "category": f.category,
                "portfolio_as_on": f.as_on,
                "news_tilt": f.news_tilt,
                "alignment": f.alignment,
                "helped_sectors": f.pos_sectors,
                "hurt_sectors": f.neg_sectors,
                "mixed_sectors": f.mixed_sectors,
                "larger_other_sectors": f.other_top_sectors[:3],
                "mechanism": f.mechanism,
                "drags": f.drag_sectors[:3],
                "drag_sectors": f.drag_sectors[:3],
            }
        )
    return facts


def _pipeline_note(
    pipeline_errors: list[dict[str, str]] | None,
    stage: str,
    message: str,
    *,
    tool: str = "",
) -> None:
    if pipeline_errors is None:
        return
    pipeline_errors.append(
        {"stage": stage, "tool": tool, "message": (message or "")[:500]}
    )


def _llm_compose_from_packet(
    question: str,
    brief: QuestionBrief,
    findings: Findings,
    evidence: EvidenceSet,
    *,
    query_log: Any = None,
    pipeline_errors: list[dict[str, str]] | None = None,
    analysis_brief: dict[str, Any] | None = None,
) -> ComposedInsight | None:
    settings = get_settings()
    packet = _facts(question, brief, findings, evidence)
    system_prompt = build_composer_prompt()
    user_content = _composer_user_content(packet, analysis_brief)

    try:
        res = call_insight_llm(
            system_prompt=system_prompt,
            user_content=user_content,
            model_override=composer_model(settings),
            max_tokens=2500,
            temperature=0.2,
            query_log=query_log,
        )
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if query_log is not None:
            query_log.write(f"COMPOSER llm_failed error={msg[:200]}")
        _pipeline_note(pipeline_errors, "compose", msg)
        return None

    if res is None:
        return None
    text = (res.raw_text or "").strip()
    if not text:
        return None

    violations = check_composer_guardrails(text, packet, findings.evidence_text)
    if violations:
        if query_log is not None:
            query_log.write(f"COMPOSER guardrails_violated count={len(violations)}: {violations}")
        original = text
        only_numbers = violations == ["Contains ungrounded numbers."]
        if only_numbers:
            # Cheap, lossless fix: drop just the numbers that are not in the data.
            text = scrub_composer_text(original, packet, findings.evidence_text)
        else:
            repair_user = (
                f"{user_content}\n\n---\nYour previous draft had guardrail violations:\n\n{original}\n\n"
                "Violations:\n" + "\n".join(f"- {v}" for v in violations) + "\n\n"
                "Rewrite the full answer from the FACTS PACKET above, fixing every violation and keeping "
                "all substantive content that answers the user's question. No outlet names, no dates, "
                "no advice, and only numbers present in the packet. Never say data is missing if the "
                "packet contains it."
            )
            try:
                res_repair = call_insight_llm(
                    system_prompt=system_prompt,
                    user_content=repair_user,
                    model_override=composer_model(settings),
                    max_tokens=3000,
                    temperature=0.1,
                    query_log=query_log,
                )
                text_repair = ((res_repair.raw_text if res_repair else "") or "").strip()
                if (
                    len(text_repair) >= max(200, int(len(original) * 0.5))
                    and not check_composer_guardrails(text_repair, packet, findings.evidence_text)
                ):
                    text = text_repair
                else:
                    text = scrub_composer_text(original, packet, findings.evidence_text)
            except Exception:
                text = scrub_composer_text(original, packet, findings.evidence_text)
        if len(text.strip()) < 200:
            return None

    text = _drop_pipeline_voice(strip_media_attribution(text))
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    headline = ""
    for line in lines:
        if line.startswith("#"):
            headline = line.lstrip("#").strip()
            break
        if line and not headline:
            headline = line
            break
    if not headline:
        headline = _structured_headline(brief, findings)

    disclaimer = "For context only — not investment advice."
    if disclaimer.lower() not in text.lower():
        text = text.rstrip() + f"\n\n{disclaimer}"

    return ComposedInsight(
        headline=headline,
        narrative=text,
        bullets=[],
        closing_summary=disclaimer,
        display=text,
        sub_ask_coverage=[a.text for a in sorted(brief.sub_asks, key=lambda a: a.order or 0)],
        answer_trace={
            "mode": "llm_packet_composer",
            "findings": findings.to_dict(),
        },
    )


def _hybrid_compose(
    question: str,
    brief: QuestionBrief,
    findings: Findings,
    evidence: EvidenceSet,
    structured: ComposedInsight,
    query_log: Any,
    pipeline_errors: list[dict[str, str]] | None = None,
) -> ComposedInsight | None:
    settings = get_settings()
    facts = _facts(question, brief, findings, evidence)
    try:
        res = call_json_llm(
            system_prompt=INTERPRET_SYSTEM,
            user_content="FACTS:\n" + json.dumps(facts, ensure_ascii=False),
            context_blocks=[],
            model_override=composer_model(settings),
            max_tokens=2600,
            temperature=0.2,
            query_log=query_log,
            response_schema=INTERPRET_SCHEMA,
            stage="interpret",
        )
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        if query_log is not None:
            query_log.write(f"INTERPRET llm_failed error={msg[:200]}")
        _pipeline_note(pipeline_errors, "interpret", msg)
        return None
    parsed = res.parsed if isinstance(res.parsed, dict) else {}
    if not parsed or getattr(res, "truncated", False):
        return None

    claims = _claim_map(findings)
    fallbacks: list[str] = []
    shown = _shown_funds(findings, question, brief)

    headline = str(parsed.get("headline") or "")
    headline, _ = _render_citations(headline, claims)
    if not _valid_llm_text(headline):
        headline = _structured_headline(brief, findings)
        fallbacks.append("headline")

    sector_read = str(parsed.get("sector_read") or "")
    sector_read, cited = _render_citations(sector_read, claims)
    if not _valid_llm_text(sector_read) or (claims and cited == 0):
        sector_read = _structured_sector_read(findings) or "Not enough news in this run to judge the sector."
        fallbacks.append("sector_read")

    raw_lines = parsed.get("fund_lines") if isinstance(parsed.get("fund_lines"), dict) else {}
    lines_by_isin = {str(k).strip().upper(): v for k, v in raw_lines.items()}
    fund_lines: dict[str, str] = {}
    for f in shown:
        text = str(lines_by_isin.get(f.isin.upper()) or "")
        text, _ = _render_citations(text, claims)
        text = text.strip().rstrip(".")
        if _valid_llm_text(text):
            fund_lines[f.isin] = text
        else:
            fund_lines[f.isin] = _structured_fund_line(f)
            fallbacks.append(f"fund:{f.isin}")

    closing = str(parsed.get("closing") or "")
    closing, _ = _render_citations(closing, claims)
    must_name = []
    if findings.sector and not findings.funds:
        must_name = [str(x.get("name") or "") for x in (findings.sector.sectors_negative or [])[:2]]
    named_ok = not must_name or any(n and n.lower() in closing.lower() for n in must_name)
    if not _valid_llm_text(closing) or not named_ok:
        closing = _structured_closing(findings, brief, question)
        fallbacks.append("closing")

    out = _assemble(
        brief,
        findings,
        evidence,
        question=question,
        headline=headline,
        sector_read=sector_read,
        fund_lines=fund_lines,
        closing=closing,
    )
    out.answer_trace = {
        "mode": "llm_hybrid",
        "field_fallbacks": fallbacks,
        "findings": findings.to_dict(),
    }
    return out


def compose_from_findings(
    question: str,
    brief: QuestionBrief,
    findings: Findings,
    evidence: EvidenceSet,
    *,
    query_log: Any = None,
    pipeline_errors: list[dict[str, str]] | None = None,
    analysis_brief: dict[str, Any] | None = None,
    news_read: Any = None,
) -> ComposedInsight:
    settings = get_settings()

    if brief.funds and not findings.funds:
        fund_name = brief.funds[0]
        headline = f"Could not match **{fund_name}** to our database"
        narrative = (
            f"We could not find holdings or return data for **{fund_name}** in our database of ~1,400 schemes. "
            "Please check the fund name or try searching by AMC and category."
        )
        closing = "For context only — not investment advice."
        display = f"{headline}\n\n{narrative}\n\n{closing}"
        return ComposedInsight(
            headline=headline,
            narrative=narrative,
            bullets=[],
            closing_summary=closing,
            display=display,
            sub_ask_coverage=[a.text for a in sorted(brief.sub_asks, key=lambda a: a.order or 0)],
            answer_trace={"mode": "unmatched_fund", "findings": findings.to_dict()},
        )

    named_fund_focus = bool(brief.funds) and not brief.primary_sector() and not brief.drivers
    structured = (
        _fund_why_compose(question, brief, findings, evidence)
        if named_fund_focus or (brief.funds and any(f.drag_sectors for f in findings.funds))
        else _structured_compose(question, brief, findings, evidence)
    )

    use_llm = bool(getattr(settings, "insight_use_llm_interpret", True)) and llm_api_key_configured(settings)
    if query_log is not None:
        query_log.write(
            f"INTERPRET_MODE hybrid_llm={use_llm} named_fund_structured={named_fund_focus} funds={len(findings.funds)}"
        )
    if named_fund_focus and findings.funds and use_llm:
        llm_named = _named_fund_llm_compose(
            question,
            brief,
            findings,
            evidence,
            structured,
            news_read=news_read,
            query_log=query_log,
            pipeline_errors=pipeline_errors,
            analysis_brief=analysis_brief,
        )
        if llm_named is not None:
            if query_log is not None:
                query_log.write("INTERPRET mode=named_fund_llm")
            return llm_named
        if query_log is not None:
            query_log.write("INTERPRET mode=named_fund_structured_fallback")
        return structured
    if not use_llm:
        return structured

    packet_composed = _llm_compose_from_packet(
        question,
        brief,
        findings,
        evidence,
        query_log=query_log,
        pipeline_errors=pipeline_errors,
        analysis_brief=analysis_brief,
    )
    if packet_composed is not None:
        return packet_composed

    if findings.sector and (findings.sector.claims or findings.funds):
        hybrid = _hybrid_compose(
            question, brief, findings, evidence, structured, query_log, pipeline_errors=pipeline_errors
        )
        if hybrid:
            return hybrid
    if use_llm and pipeline_errors is not None:
        had_llm_issue = any(
            e.get("stage") in ("compose", "interpret", "stream_compose") for e in pipeline_errors
        )
        if had_llm_issue:
            _pipeline_note(
                pipeline_errors,
                "interpret",
                "Showing a structured fallback answer because the LLM composer step failed.",
            )
    return structured
