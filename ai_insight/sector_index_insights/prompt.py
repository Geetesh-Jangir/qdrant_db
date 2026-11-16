"""Prompts for a sector index card and the rotation card."""

from __future__ import annotations

import json

from ai_insight.common.evidence import EvidenceArticle, format_evidence_block
from ai_insight.common.prose_guard import READER_VOICE

SECTOR_BODY_STYLE = """
Body style for mutual-fund readers (match this tone and shape, not a data dump):

- Start body with the index name from FACTS (e.g. "Nifty Bank").
- Use 2 short sentences, ≤ 50 words total. One paragraph, no bullets, no newlines.
- Sentence 1: week % and today's move when it matters; one plain-English reason from ARTICLES (hedged).
- Sentence 2: main worry or offset (start with "However," "While," or similar) from ARTICLES or FACTS (hedged).
- Use everyday words: "supported by", "may hurt", "could put pressure on" — not jargon (explain ECL, NIM, etc. in simple words if needed).
- Skip bar trivia: no best/worst day of the week, no full week range unless one line like "well below its weekly high".
- At most one index level ("closing near X") only when momentum is the story; chips hold the exact %.
- When article_count is 0: week/today % plus one momentum line from FACTS only — no complaint about missing news.

Examples (illustrative shape only — use only numbers and themes from FACTS and ARTICLES):

Nifty Bank gained 10.13% this week, supported by strong loan growth and better profits at state-run banks. However, expected RBI rate hikes in December and new rules requiring banks to set aside money for possible loan losses could put pressure on banks.

Nifty IT was almost flat today and is down 0.38% this week, closing near 31,941. The index remains well below its weekly high, showing weak momentum and limited recovery so far.

Nifty Pharma fell 1.53% today but remains up 2.8% for the week. New rules to cut prices on 137 cancer drugs and a recall order for a liver drug may hurt sales and profits for some drugmakers.

Nifty Metal fell 1.5% today and is down 0.22% for the week. While Indian steel demand may improve, higher import costs, weak business in the UK, and uncertainty over US tariffs could put pressure on steelmakers' profits.
"""

SECTOR_OVERRIDE = """
Sector cards override the generic reader voice: no 3-sentence template, no listing best/worst days or full weekly ranges, no dumping every bar stat. Follow SECTOR_BODY_STYLE only.
"""

SYSTEM = """You explain ONE sector index — only the FACTS and ARTICLES in the user message belong to this index.

""" + READER_VOICE + SECTOR_OVERRIDE + SECTOR_BODY_STYLE + """

Output rules:
- headline ≤ 10 words (short label; do not repeat the full body).
- body: 2 sentences, ≤ 50 words, following SECTOR_BODY_STYLE.
- article_count > 0: themes from ARTICLES only. narrative_mode price_only: FACTS bars only, still 2 sentences.
- driver_cluster_ids: ids used. reason_unclear true only when article_count is 0.
- observations: optional, max 3 short strings. No advice.
"""

VERIFY = """Check the draft. supported is false when a cause or number is not in the facts or articles, or the direction word disagrees with the week change.
Return supported, unsupported_claims, too_long, unclear_phrases, revised.
too_long is true if body is not 2 sentences or exceeds 50 words, or reads like a bar-by-bar recap (best/worst day, full range).
"""

REVISE = """Rewrite the draft from the verifier notes. Keep the hedge. Set reason_unclear when the news does not explain the move.
body: 2 sentences, ≤ 50 words, SECTOR_BODY_STYLE. No extra price detail.
"""

ROTATION = """How sector indices moved vs each other this week. Use only the tables given.
Write 2 short sentences, ≤ 50 words, plain English — leaders, laggards, one hedged read on rotation. No bar trivia.
headline ≤ 10 words.
Return the same JSON shape, with driver_cluster_ids copied from the stories you use.
"""


def build_user(facts: dict, evidence: list[EvidenceArticle]) -> str:
    return "FACTS\n" + json.dumps(facts, ensure_ascii=False, default=str) + "\n\nARTICLES\n" + (format_evidence_block(evidence) or "(none)")