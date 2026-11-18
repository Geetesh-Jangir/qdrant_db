"""Prompts for a sector index card and the rotation card."""

from __future__ import annotations

import json

from ai_insight.common.evidence import EvidenceArticle, format_evidence_block
from ai_insight.common.prose_guard import READER_VOICE

SECTOR_BODY_STYLE = """
Body style for mutual-fund readers (match this tone and shape, not a data dump):

- Start with sector_headline_label from FACTS (e.g. "banking sector"). Never use index_display or Nifty names in the body.
- Exactly 2 short sentences, ≤ 38 words total. One paragraph, no bullets, no newlines.
- Sentence 1: week % move and today's move only if it changes the story; one hedged why from ARTICLES.
- Sentence 2: one offset or risk in plain English (start with "However," "While," or "Still,") — hedged.
- No bar trivia: no best/worst day, no full range, no listing multiple stats (chips hold the %).
- When article_count is 0: week/today % plus one momentum line from FACTS only — no complaint about missing news.

Examples (shape only — use only numbers and themes from FACTS and ARTICLES):

The banking sector gained 5.3% this week on loan-growth and rate-cut hopes. However, tighter provisioning rules may cap gains near term.

The IT sector fell 4.7% this week as AI spending fears and weak deal flow weighed on outsourcers. Still, Make-in-India tailwinds may help a few domestic names.
"""

SECTOR_OVERRIDE = """
Sector cards override the generic reader voice: no 3-sentence template, no bar-by-bar recap. Follow SECTOR_BODY_STYLE only.
"""

HEADLINE_STYLE = """
Headline format (mandatory shape):
- Use sector_headline_label from FACTS only — never index_display (Nifty Bank, Nifty IT, etc.).
- Pattern: {sector_headline_label} gained/fell {week %} week — {short why}, {portfolio hook ending with the word your}
- week_change_pct: one decimal with %; "gained" or "fell"; say "week" once.
- After —: brief why from ARTICLES, then a natural hook for mutual-fund readers (pick tone for up/down): e.g. "a tailwind for your", "worth watching in your", "with the biggest lift for your", "a pressure on holdings in your". End with your as the final word — no fund or scheme name after it (names are added later in code).
- Avoid stiff hooks ("affecting your"). No AMC or fund names. ≤ 18 words. Do not repeat the body verbatim.

Examples (shape only):
banking sector gained 5.3% week — loan growth, a tailwind for your
IT sector fell 4.7% week — weak deals, a drag on holdings in your
"""

SYSTEM = """You explain ONE sector index — only the FACTS and ARTICLES in the user message belong to this index.

""" + READER_VOICE + SECTOR_OVERRIDE + HEADLINE_STYLE + SECTOR_BODY_STYLE + """

Output rules:
- headline: follow HEADLINE_STYLE (sector label + gained/fell + week % + why).
- body: 2 sentences, ≤ 38 words, following SECTOR_BODY_STYLE.
- article_count > 0: themes from ARTICLES only. narrative_mode price_only: FACTS bars only, still 2 sentences.
- driver_cluster_ids: ids used. reason_unclear true only when article_count is 0.
- observations: optional, max 2 short strings. No advice.
"""

VERIFY = """Check the draft. supported is false when a cause or number is not in the facts or articles, or the direction word disagrees with the week change.
Return supported, unsupported_claims, too_long, unclear_phrases, revised.
too_long is true if body is not 2 sentences or exceeds 38 words, or headline exceeds 18 words, or reads like a bar-by-bar recap.
too_long is true if headline omits week % from FACTS, lacks "gained" or "fell", lacks "—", does not end with the word your, names a fund/AMC, or uses index_display / Nifty names.
"""

REVISE = """Rewrite the draft from the verifier notes. Keep the hedge. Set reason_unclear when the news does not explain the move.
headline: HEADLINE_STYLE. body: 2 sentences, ≤ 38 words, SECTOR_BODY_STYLE. Shorter and punchier — cut filler.
"""

ROTATION = """How sector indices moved vs each other this week. Use only the tables given.
Write 2 short sentences, ≤ 38 words, plain English — leaders, laggards, one hedged read on rotation. No bar trivia.
headline ≤ 12 words, include leader index and its week %.
Return the same JSON shape, with driver_cluster_ids copied from the stories you use.
"""


def build_user(facts: dict, evidence: list[EvidenceArticle]) -> str:
    return "FACTS\n" + json.dumps(facts, ensure_ascii=False, default=str) + "\n\nARTICLES\n" + (format_evidence_block(evidence) or "(none)")