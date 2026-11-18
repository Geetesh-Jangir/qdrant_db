from ai_insight.holding_insights.llm import (
    INSIGHT_WORD_MAX,
    INSIGHT_WORD_MIN,
    parse_insight_lines,
)
from ai_insight.holding_insights.prompt import SYSTEM_PROMPT

_SAMPLE_HEADLINE = "HDFC Bank up 3.4% on MCLR hikes after RBI repo move"


def _sample_paragraph(num_sentences: int, words_per_sentence: int) -> str:
    word = "word"
    return " ".join(" ".join([word] * words_per_sentence) + "." for _ in range(num_sentences))


def _payload(insight: str, *, headline: str = _SAMPLE_HEADLINE) -> dict:
    return {
        "skip": False,
        "headline": headline,
        "insight": insight,
        "reason_if_skipped": None,
    }


def test_parse_paragraph_within_word_budget():
    text = _sample_paragraph(3, 10)
    ok, lines, hl, reason = parse_insight_lines(_payload(text), week_change_pct=3.4)
    assert ok and len(lines) == 1 and hl == _SAMPLE_HEADLINE and reason is None


def test_collapses_legacy_multiline_to_one_paragraph():
    text = (
        "Margin repricing after rate hikes matters most for private bank holders this week.\n"
        "Leadership changes keep governance and execution risk in focus for the stock.\n"
        "Watch deposit growth and retail loan momentum before reading margin recovery as done."
    )
    ok, lines, _, reason = parse_insight_lines(_payload(text), week_change_pct=3.4)
    assert ok and len(lines) == 1 and "\n" not in lines[0] and reason is None


def test_rejects_too_few_words():
    text = "One short sentence only."
    ok, _, _, reason = parse_insight_lines(_payload(text), week_change_pct=3.4)
    assert not ok and "words" in (reason or "")


def test_rejects_too_many_words():
    text = _sample_paragraph(3, 26)
    ok, _, _, reason = parse_insight_lines(_payload(text), week_change_pct=3.4)
    assert not ok and "words" in (reason or "")


def test_trims_slightly_long_paragraph():
    insight = (
        "Rate hikes should widen HDFC Bank's margins as loans reprice upward, a key relief after recent pressure. "
        "Leadership churn under incoming CEO Anup Bagchi and the leak probe keep governance the main overhang. "
        "Holders should watch whether deposit growth and retail lending can turn the margin recovery into steadier earnings."
    )
    ok, lines, _, reason = parse_insight_lines(_payload(insight), week_change_pct=3.4)
    assert ok and reason is None and len(lines) == 1
    words = len(lines[0].split())
    assert INSIGHT_WORD_MIN <= words <= INSIGHT_WORD_MAX


def test_headline_must_match_week_pct():
    insight = _sample_paragraph(3, 10)
    bad_hl = "HDFC Bank up 9% on random narrative spin from thin air"
    ok, _, _, reason = parse_insight_lines(_payload(insight, headline=bad_hl), week_change_pct=3.4)
    assert not ok and reason == "headline_week_pct_mismatch"


def test_headline_down_pct_without_minus_matches_negative_week():
    insight = _sample_paragraph(3, 10)
    hl = "Infosys down 4.35% as US visa curbs weigh on margins"
    ok, lines, got_hl, reason = parse_insight_lines(_payload(insight, headline=hl), week_change_pct=-4.35)
    assert ok and reason is None and got_hl == hl and lines


def test_headline_portfolio_hook_soft_word_budget():
    insight = _sample_paragraph(3, 10)
    hl = (
        "HDFC Bank gained 1.05% week — margin repricing after RBI hikes, "
        "a key theme to watch in your"
    )
    ok, lines, got_hl, reason = parse_insight_lines(_payload(insight, headline=hl), week_change_pct=1.05)
    assert ok and reason is None and got_hl == hl and lines


def test_headline_wrong_direction_with_matching_magnitude_fails():
    insight = _sample_paragraph(3, 10)
    hl = "Infosys up 4.35% as visa headlines dominate the narrative"
    ok, _, _, reason = parse_insight_lines(_payload(insight, headline=hl), week_change_pct=-4.35)
    assert not ok and reason == "headline_week_pct_mismatch"


def test_prompt_insight_not_summary():
    lower = SYSTEM_PROMPT.lower()
    assert "insight" in lower and "summar" in lower
    assert "24" in lower and "36" in lower
    assert "paragraph" in lower
    assert "headline" in lower
    assert "impact" in lower and "week change" in lower and "stock insight" in lower
    assert INSIGHT_WORD_MIN <= 30 <= INSIGHT_WORD_MAX