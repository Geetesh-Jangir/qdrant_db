"""Market driver prompts."""

from __future__ import annotations

import json

from ai_insight.common.evidence import EvidenceArticle, format_evidence_block
from ai_insight.common.prose_guard import READER_VOICE
from ai_insight.market_driver_digest.schema import PROMPT_VERSION

HEADLINE_STYLE = """
Headline (Market Today):
- Pattern: Nifty {signed today %} today — {3–6 word hedged macro why}
- Use nifty_change_pct from FACTS with sign. Say "today" once.
- After em dash (—), one plain macro cause fragment (yields, crude, global risk, rupee) — not FII crore figures.
- ≤ 12 words. Do not repeat the body.
Examples:
Nifty -0.6% today — bond yields, inflation fears
Nifty +0.4% today — crude dip, easing global risk
"""

BODY_STYLE = """
Body (insight, not a recap):
- Exactly 2 sentences, ≤ 40 words. One paragraph.
- This card is "Market Today" beside "Institutional Flows" on the same page — do not repeat that card's job.
- Do not quote FII/DII net crore in the body (flows have their own card). At most one short hedged clause if flows clearly explain today's index move.
- Do not list every stat (level, week range, Bank Nifty %) — chips hold numbers.
- Sentence 1: what today's move means — the single best macro "so what" from ARTICLES tied to the direction (hedged).
- Sentence 2: tension or second driver (However/While/Still) — why the move could stick or reverse; must add a new angle, not repeat sentence 1.
"""

SYSTEM = """You explain why Nifty moved today for everyday investors — one clear insight, not a news digest.

""" + READER_VOICE + HEADLINE_STYLE + BODY_STYLE + """

Output rules:
- headline: follow HEADLINE_STYLE.
- body: follow BODY_STYLE.
- FACTS hold today's prices, macro series, flows. ARTICLES are macro stories — pick the 2 best themes for today's session (crude, rupee, RBI, global risk). Prefer implication over event listing.
- observations: max 2 short strings (logging).
- cited_cluster_ids: ids from ARTICLES you used.
- No advice.
"""

VERIFY = """Check the draft against the same facts and articles. Return supported, unsupported_claims, too_long, unclear_phrases, and revised.
supported is false if the draft invents a number or event, gives advice, cites unsupported causes, or reads like a duplicate institutional-flows recap (FII/DII nets as the main story).
too_long is true when the headline exceeds 12 words, omits today's % or "—" why, or the body is not 2 sentences or exceeds 40 words.
"""

REVISE = """Rewrite the draft using the verifier notes. Shorter and punchier — cut filler. Same headline and body rules.
"""