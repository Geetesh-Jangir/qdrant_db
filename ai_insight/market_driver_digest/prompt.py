"""Market driver prompts."""

from __future__ import annotations

import json

from ai_insight.common.evidence import EvidenceArticle, format_evidence_block
from ai_insight.common.prose_guard import READER_VOICE
from ai_insight.market_driver_digest.schema import PROMPT_VERSION

SYSTEM = """You explain why Nifty moved today for everyday investors.

""" + READER_VOICE + """

Output rules:
- headline ≤ 12 words. body ≤ 5 sentences, ≤ 110 words.
- FACTS hold today's prices, macro series, flows. ARTICLES are full macro stories (many items).
- Pick the 2–3 macro themes that fit best (crude, rupee, FII chatter, banks, global risk, earnings, RBI).
- observations: 2–4 short strings listing signals you connected (for logging).
- cited_cluster_ids: ids from ARTICLES you used.
- No advice.
"""

VERIFY = """Check the draft against the same facts and articles. Return supported, unsupported_claims, too_long, unclear_phrases, and revised.
supported is false if the draft invents a number or an event, gives advice, or cites two clusters about the same subject as primary and secondary.
too_long is true when the headline exceeds 12 words or the body exceeds 3 sentences or 55 words.
"""

REVISE = """Rewrite the draft using the verifier notes. Keep the same rules. Return nulls instead of stretching a cause the articles do not support.
"""


def build_user(facts: dict, evidence: list[EvidenceArticle]) -> str:
    return "FACTS\n" + json.dumps(facts, ensure_ascii=False, default=str) + "\n\nARTICLES\n" + (format_evidence_block(evidence) or "(none)")


__all__ = ["PROMPT_VERSION", "SYSTEM", "VERIFY", "REVISE", "build_user"]