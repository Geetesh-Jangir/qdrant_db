"""Draft → body assembly respects config limits."""

from ai_insight.common.config import load_config
from ai_insight.common.narrative import assemble_body, persist_narrative_beats


def _draft():
    return {
        "what_happened": "FIIs were net buyers today.",
        "why": "Global risk eased after softer oil.",
        "impacted": "Bank and IT stories led the news flow.",
        "investor_meaning": "Sentiment may favour domestic cyclicals near term.",
    }


def test_assembled_body_within_word_limit():
    cfg = load_config()
    body = assemble_body(_draft())
    words = len(body.split())
    assert words <= cfg.body_max_words


def test_persist_narrative_beats():
    facts: dict = {}
    persist_narrative_beats(facts, _draft())
    assert facts["narrative_beats"]["why"].startswith("Global")