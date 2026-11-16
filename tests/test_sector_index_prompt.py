"""Sector index prompt contract."""

from ai_insight.sector_index_insights.prompt import SECTOR_BODY_STYLE, SYSTEM, VERIFY
from ai_insight.sector_index_insights.schema import PROMPT_VERSION


def test_sector_prompt_version_bumped():
    assert PROMPT_VERSION == "v2"


def test_sector_prompt_targets_two_sentence_cards():
    assert "2 sentences" in SYSTEM
    assert "2 sentences" in VERIFY
    assert "well below its weekly high" in SECTOR_BODY_STYLE
    assert "no best/worst day" in SECTOR_BODY_STYLE.lower() or "Skip bar trivia" in SECTOR_BODY_STYLE