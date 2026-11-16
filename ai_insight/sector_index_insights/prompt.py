"""Prompts for a sector index card and the rotation card."""

from __future__ import annotations

import json

from ai_insight.common.evidence import EvidenceArticle, format_evidence_block
from ai_insight.common.prose_guard import READER_VOICE

SYSTEM = """You explain ONE sector index — only the FACTS and ARTICLES in the user message belong to this index.

""" + READER_VOICE + """

Output rules:
- headline ≤ 12 words. body ≤ 5 sentences, ≤ 110 words.
- Open with week % and today % from facts.bars. Name which day was strongest/weakest using bar dates.
- article_count in FACTS: if > 0, name at least two themes from ARTICLES and tie them to the move (hedged).
- narrative_mode price_only: use only bars (high/low, close vs week range). No news blame.
- driver_cluster_ids: ids used. reason_unclear true only when article_count is 0.
- observations: 2–4 short signals you saw.
- No advice.
"""

VERIFY = """Check the draft. supported is false when a cause or number is not in the facts or articles, or the direction word disagrees with the week change.
Return supported, unsupported_claims, too_long, unclear_phrases, revised.
"""

REVISE = """Rewrite the draft from the verifier notes. Keep the hedge. Set reason_unclear when the news does not explain the move.
"""

ROTATION = """You describe how sector indices moved relative to each other this week. Use only the tables given. Hedge. No advice. headline <= 12 words, body <= 55 words and 3 sentences.
Return the same JSON shape, with driver_cluster_ids copied from the stories you use.
"""


def build_user(facts: dict, evidence: list[EvidenceArticle]) -> str:
    return "FACTS\n" + json.dumps(facts, ensure_ascii=False, default=str) + "\n\nARTICLES\n" + (format_evidence_block(evidence) or "(none)")
