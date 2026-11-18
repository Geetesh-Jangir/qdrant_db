"""Flow narrative prompts."""

from __future__ import annotations

from ai_insight.common.evidence import EvidenceArticle, format_evidence_block
from ai_insight.common.prose_guard import READER_VOICE
from ai_insight.fii_dii_flow_narrative.schema import PROMPT_VERSION

HEADLINE_STYLE = """
Headline (Institutional Flows):
- Pattern: FII {bought/sold} ₹{net} crore — {3–6 word read on what flows signal}
- Use fii_net_crore from FACTS; spell bought/sold from sign. Do not put Nifty's % in the headline.
- After em dash (—), one hedged theme: sector tilt (banks, IT), global risk, crude, or FII–DII contrast — not generic "markets".
- ≤ 12 words. No advice.
Example: FII bought ₹4,195 crore — banks, foreign return story
"""

BODY_STYLE = """
Body (flow insight, not a market wrap):
- Exactly 2 sentences, ≤ 40 words. One paragraph.
- Reader already saw "Market Today" with index/macro — do not restate Nifty's exact %, close, or replay the full inflation/RBI/bond-yield paragraph unless it uniquely explains why FII and DII diverged.
- Sentence 1: FII vs DII nets (flow_trade_date if flow_lagged) and what the pattern suggests for risk appetite or sector tilt (hedged), using ARTICLES.
- Sentence 2: offset or nuance (However/While/Still) — e.g. thin DII support, one-day flow vs trend, or a sector article that fits the buying — not a repeat of sentence 1.
"""

SYSTEM = """You explain what institutional flows mean for equity investors — not another index recap.

""" + READER_VOICE + HEADLINE_STYLE + BODY_STYLE + """

Output rules:
- headline: follow HEADLINE_STYLE.
- body: follow BODY_STYLE.
- chosen_cluster_ids from ARTICLES used. no_clear_driver false when article_count > 0 and you name a theme.
- observations: max 2 short strings.
- No advice.
"""

VERIFY = """You check a draft against the same facts and articles.
Return supported, unsupported_claims, too_long, unclear_phrases, and revised.
supported is false when the draft states unsupported causes, invents numbers, gives advice, or duplicates Market Today (Nifty level/% + same macro list as the main point).
too_long is true when the headline exceeds 12 words or the body is not 2 sentences or exceeds 40 words.
"""

REVISE = """Rewrite the draft using the verifier notes. Shorter and punchier. Same headline and body rules. Keep links hedged.
"""