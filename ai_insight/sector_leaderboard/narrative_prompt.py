"""Second-pass four-beat narrative for sector pulse."""

from __future__ import annotations

import json
from typing import Any

from ai_insight.common.narrative import DRAFT_BEAT_PROPERTIES, narrative_limits_text
from ai_insight.common.prose_guard import FOUR_BEAT_FLOW, READER_VOICE
from ai_insight.sector_leaderboard.schema import INSIGHT_ID

PROMPT_VERSION = "v4"

NARRATIVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["what_happened", "why", "impacted", "investor_meaning"],
    "properties": {
        **DRAFT_BEAT_PROPERTIES,
        "observations": {"type": "array", "items": {"type": "string"}},
    },
}

SYSTEM = """You write the Sector Pulse card body in four beats for mutual-fund readers.

""" + READER_VOICE + FOUR_BEAT_FLOW + """

Sector Pulse rules:
- Use week_movers (best/worst index week %) and best_theme / worst_theme from FACTS.
- Beat what_happened: which indices led/lagged this week (% from FACTS).
- Beat why: themes from FACTS and STORIES — not new themes outside them.
- Beat impacted: named sectors and the news thread; link winners vs laggards.
- Beat investor_meaning: hedged read on sector rotation or diversification — no advice.

""" + narrative_limits_text() + """
"""

VERIFY = """Check the narrative JSON. supported false if numbers/themes are not in FACTS or STORIES, or advice is given.
too_long if beats exceed word/sentence caps. Return supported, unsupported_claims, too_long, unclear_phrases, revised.
"""

REVISE = """Rewrite using verifier notes. Same four beats. Shorter if too_long."""


def build_narrative_user(facts: dict[str, Any], stories_block: str) -> str:
    from ai_insight.common.narrative import compact_facts

    compact = compact_facts(INSIGHT_ID, facts)
    return (
        f"INSIGHT: {INSIGHT_ID}\n"
        f"FACTS\n{json.dumps(compact, ensure_ascii=False, default=str)}\n\n"
        f"STORIES\n{stories_block or '(none)'}"
    )