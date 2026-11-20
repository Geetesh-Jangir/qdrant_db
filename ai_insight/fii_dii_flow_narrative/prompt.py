"""Flow narrative prompts."""

from __future__ import annotations

import json
import re
from typing import Any

from ai_insight.common.evidence import EvidenceArticle, format_evidence_block
from ai_insight.common.narrative import FLOW_KEYS, _compact_news_map, narrative_limits_text

# Gross buy/sell is often null in history; prompt uses net-only series in DATASETS.
_FLOW_PROMPT_KEYS = tuple(k for k in FLOW_KEYS if "gross" not in k)
from ai_insight.common.prose_guard import READER_VOICE, scrub_refusal_prose
from ai_insight.fii_dii_flow_narrative.schema import INSIGHT_ID, LEGACY_FLOW_SECTIONS, PROMPT_VERSION

HEADLINE_STYLE = """
Headline (short card title — not part of the paragraph):
- Pattern: FII net buy / net sell ₹{net} crore — {3–6 word hedged read}
- Use fii_net_crore from FACTS. Always include "net". ≤ 12 words. No advice.
"""

FII_ANALYST_INSTRUCTIONS = """
You are a senior Indian financial market analyst writing evidence-based insights for mutual fund investors.

Transform FACTS, DATASETS, and ARTICLES into **2–3 selected relationships** (`observations`), then **one selective paragraph** that explains only those relationships.

## Workflow (required)

1. Read DATASETS.synthesis_hints (flow_history, sector_leaders_laggards, suggested_tensions, macro_for_flows), flow_index_date_context, and ARTICLES.
2. Output **observations**: exactly **2–3 strings**. Each must state a **relationship or tension** (not a lone statistic). Examples:
   - FII net buying over multiple sessions while DII net selling partially offsets foreign inflows.
   - Weekly index performance led by banks while IT lagged (uneven market strength).
   - Hedged news explanation only when ARTICLES support it.
3. Use **suggested_tensions** as candidates; keep only if DATASETS and ARTICLES support them.
4. Write **paragraph** expanding **only** what observations, FACTS, and ARTICLES support. Do not add sectors, macro levels, or why-claims outside that set.

## Insight quality and data-selection rules

- Lead with the single most important insight in the paragraph, not a list of market statistics.
- Use **net buyers / net sellers / net buy / net sell** whenever citing FII/DII flows (data is net ₹ crore only). Never describe net flows as gross buying or selling (avoid "bought Indian shares" without "net").
- Include a statistic only when it supports an observation, explains a change, establishes a meaningful contrast, or changes the investor takeaway.
- Prioritize **relationships between datasets** over standalone numbers.
- Explain what changed, what the evidence suggests, and why it matters to investors.
- Distinguish observed facts from possible explanations. Never present correlation as proven causation.
- Do not infer that foreign investors caused a sector rally because inflows and sector returns occurred in the same period.
- Do not claim currency movements made India cheaper for foreign investors without valuation or relative-market evidence.
- Label each date (YYYY-MM-DD) when comparing flows to Nifty moves (use flow_index_date_context). If flow_trade_date ≠ card_trading_date, name both before comparing.
- Avoid repeating statistics unless the second number adds meaningful context.
- Exclude index milestones (records, nine-month highs), lone rupee/Brent prints, and sector stats that do not change the insight.
- Prefer the **strongest sector contrast** (e.g. banks vs IT week %) over listing every sector.
- Connect mutual funds through **conditional** category exposure (banking-tilted vs IT-tilted equity funds) when clear; otherwise omit investor lines.
- Include a risk or counterpoint only when it materially changes the interpretation.
- If evidence cannot explain why, state what is known and what remains unconfirmed instead of inventing causes.
- Never end with a generic prediction or warning that could apply to any market day.

## Paragraph shape (one string, no headings or bullets)

Implicit beats in order when evidence supports each; skip beats that add nothing:

1. **What matters** — multi-day FII/DII net pattern and offset (e.g. 5d totals, net buy vs net sell session counts).
2. **Market impact** — sector/index divergence tied to observations (week % on at most two contrasting sectors).
3. **Investor relevance** — conditional MF implication only when mechanism is clear.
4. **What to watch** — one concrete monitor tied to flows or sector gap; or close on the strongest supported fact.

Target **100–150 words**. Prefer two or three strong insights over many weak observations.

## Evidence

- FII/DII: **net ₹ crore only** (fii_dii_net_history). No gross buy/sell.
- Set no_clear_driver true when news does not support a defensible why for an observation.
- FII net buy ≠ Nifty must rise; DII net sell ≠ mass MF redemption.

## Output constraints

- **observations**: 2–3 relationship strings (required).
- **paragraph**: exactly one paragraph (no newlines inside).
- No headings, bullets, tables, or XML/HTML inside JSON string values.
- Return JSON only: headline, paragraph, observations, chosen_cluster_ids, confidence, no_clear_driver.
"""

SYSTEM = FII_ANALYST_INSTRUCTIONS + """

""" + READER_VOICE + HEADLINE_STYLE + """

""" + narrative_limits_text()

VERIFY = """
Review observations and paragraph against FACTS, DATASETS, ARTICLES, and system instructions.

Return:
{
  "supported": true,
  "unsupported_claims": [],
  "too_long": false,
  "unclear_phrases": [],
  "repetitive_content": [],
  "weak_insights": [],
  "missing_mechanisms": [],
  "revised": { ... full draft JSON with observations + paragraph ... }
}

Set supported=false if:
- observations missing, fewer than 2, or more than 3; or items are lone stats not relationships;
- multi-paragraph or newlines in paragraph; bullets/headings inside paragraph;
- gross-flow phrasing ("bought Indian shares", "FII buying" without "net");
- paragraph introduces sectors, macro levels, or explanations not implied by observations + FACTS + ARTICLES;
- invented data; unsupported causation; fund advice without conditional language;
- statistic laundry list (>4 distinct figures without a clear insight);
- FII flows "drove" a sector rally; rupee/Brent level "made India cheaper" without evidence;
- index milestones (record, nine-month high) without investor mechanism;
- generic closing ("flows can reverse quickly", "if sentiment turns") without tied evidence;
- Nifty or flow figures compared across days without each YYYY-MM-DD.

Set too_long=true if headline >12 words or paragraph exceeds ~150 words.

Flag weak_insights when observations duplicate paragraph content as raw numbers, or paragraph ignores the lead observation.

Flag unclear_phrases for cross-day comparisons without dates.

Return valid JSON only.
"""

REVISE = """Rewrite the full draft JSON per verifier: fix observations (2–3 relationships), then a shorter paragraph
that cites only those observations plus supported facts. Use net-flow wording. Same JSON shape."""

_TAG_LEAK = re.compile(r"</?[\w_#:]+[^>]*>", re.IGNORECASE)


ANALYST_TASK = """
Step 1 — Select 2–3 evidence-backed relationships for `observations` using synthesis_hints.flow_history,
synthesis_hints.suggested_tensions, sector_leaders_laggards, flow_index_date_context, and ARTICLES.
Default lead when data supports it: FII net buying pattern with DII net selling partially offsetting.
Second when data supports it: banks (or week leader) up vs IT (or week laggard) down — uneven market strength.
Optional third: hedged why from ARTICLES only.

Step 2 — Write `paragraph` in one block (~100–150 words): what matters → market impact → conditional investor relevance → what to watch.
Do not repeat the latest daily FII net if 5d totals and session counts already tell the story; include latest only if it changes the pattern.

Populating `observations` is mandatory before writing the paragraph.
"""


def _legacy_paragraph(data: dict) -> str:
    parts: list[str] = []
    for key in LEGACY_FLOW_SECTIONS:
        text = str(data.get(key) or "").strip()
        if text:
            parts.append(text)
    return " ".join(parts)


def normalize_fii_draft(data: dict) -> dict:
    out = dict(data)
    para = str(out.get("paragraph") or out.get("body") or "").strip()
    if not para:
        para = _legacy_paragraph(out)
    out["paragraph"] = _clean_paragraph(para)
    cited = out.get("chosen_cluster_ids")
    if cited is None:
        cited = out.get("cited_cluster_ids") or out.get("driver_cluster_ids") or []
    if not isinstance(cited, list):
        cited = []
    out["chosen_cluster_ids"] = [str(item) for item in cited if item]
    obs = out.get("observations")
    if not isinstance(obs, list):
        obs = []
    out["observations"] = [str(item).strip() for item in obs if str(item).strip()]
    out.setdefault("confidence", "medium")
    out.setdefault("no_clear_driver", False)
    out.setdefault("headline", "")
    for key in LEGACY_FLOW_SECTIONS:
        out.pop(key, None)
    out.pop("cited_cluster_ids", None)
    out.pop("driver_cluster_ids", None)
    out.pop("body", None)
    return out


def _clean_paragraph(text: str) -> str:
    cleaned = scrub_refusal_prose(text)
    cleaned = _TAG_LEAK.sub("", cleaned)
    cleaned = cleaned.replace("\n\n", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def assemble_fii_body(data: dict) -> str:
    return _clean_paragraph(str(data.get("paragraph") or ""))


def persist_fii_sections(facts: dict, data: dict) -> None:
    facts["narrative_beats"] = {"paragraph": str(data.get("paragraph") or "").strip()}


def compact_flow_facts(facts: dict) -> dict[str, Any]:
    out: dict[str, Any] = {"insight_id": INSIGHT_ID}
    for key in _FLOW_PROMPT_KEYS:
        if key in facts and facts[key] is not None:
            out[key] = facts[key]
    for key in ("trading_date", "article_count", "news_note", "flow_note", "prominence"):
        if key in facts and facts[key] is not None:
            out[key] = facts[key]
    out["DATE_CONTEXT"] = {
        "trading_date": facts.get("trading_date"),
        "flow_trade_date": facts.get("flow_trade_date"),
        "flow_lagged": facts.get("flow_lagged"),
        "news_note": facts.get("news_note"),
        "flow_note": facts.get("flow_note"),
    }
    if facts.get("fund_data"):
        out["FUND_DATA"] = facts["fund_data"]
    else:
        out["FUND_DATA"] = None
        out["FUND_DATA_note"] = (
            "No fund-level holdings in this card. Discuss mutual fund categories by mechanism only."
        )
    if facts.get("week_pulse"):
        out["week_pulse"] = facts["week_pulse"]
    if facts.get("sector_tilt_hint"):
        out["sector_tilt_hint"] = facts["sector_tilt_hint"]
    if facts.get("nifty_change_pct") is not None:
        out["nifty_change_pct"] = facts["nifty_change_pct"]
    if facts.get("banknifty_change_pct") is not None:
        out["banknifty_change_pct"] = facts["banknifty_change_pct"]
    aligned = facts.get("aligned_market_flows") or []
    if aligned:
        out["aligned_market_flows"] = aligned[-7:]
    if facts.get("flow_totals"):
        out["flow_totals"] = facts["flow_totals"]
    datasets = facts.get("datasets")
    if datasets:
        slim = dict(datasets)
        # Full sector daily for every index stays in envelope facts; prompt gets rank + focus slices.
        slim.pop("sector_indices_7d", None)
        out["DATASETS"] = slim
    news_map = facts.get("news_map")
    if news_map:
        out["news_map"] = _compact_news_map(news_map)
    limitations = (datasets or {}).get("data_limitations") if datasets else None
    if limitations:
        out["data_limitations"] = limitations
    return out


def build_user(facts: dict, evidence: list[EvidenceArticle]) -> str:
    compact = compact_flow_facts(facts)
    articles = format_evidence_block(evidence) or "(none)"
    return (
        f"INSIGHT: {INSIGHT_ID}\n"
        f"{ANALYST_TASK.strip()}\n\n"
        f"FACTS\n{json.dumps(compact, ensure_ascii=False, default=str)}\n\n"
        f"ARTICLES\n{articles}"
    )


__all__ = [
    "PROMPT_VERSION",
    "SYSTEM",
    "VERIFY",
    "REVISE",
    "ANALYST_TASK",
    "assemble_fii_body",
    "build_user",
    "compact_flow_facts",
    "normalize_fii_draft",
    "persist_fii_sections",
]