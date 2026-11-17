from ai_insight.holding_insights.llm import (
    INSIGHT_WORD_MAX,
    INSIGHT_WORD_MIN,
    parse_insight_lines,
)
from ai_insight.holding_insights.prompt import SYSTEM_PROMPT


def _sample_paragraph(num_sentences: int, words_per_sentence: int) -> str:
    word = "word"
    return " ".join(" ".join([word] * words_per_sentence) + "." for _ in range(num_sentences))


def test_parse_paragraph_within_word_budget():
    text = _sample_paragraph(3, 10)
    ok, lines, reason = parse_insight_lines({"skip": False, "insight": text, "reason_if_skipped": None})
    assert ok and len(lines) == 1 and reason is None


def test_collapses_legacy_multiline_to_one_paragraph():
    text = (
        "Margin repricing after rate hikes matters most for private bank holders this week.\n"
        "Leadership changes keep governance and execution risk in focus for the stock.\n"
        "Watch deposit growth and retail loan momentum before reading margin recovery as done."
    )
    ok, lines, reason = parse_insight_lines({"skip": False, "insight": text, "reason_if_skipped": None})
    assert ok and len(lines) == 1 and "\n" not in lines[0] and reason is None


def test_rejects_too_few_words():
    text = "One short sentence only."
    ok, _, reason = parse_insight_lines({"skip": False, "insight": text, "reason_if_skipped": None})
    assert not ok and "words" in (reason or "")


def test_rejects_too_many_words():
    text = _sample_paragraph(3, 26)
    ok, _, reason = parse_insight_lines({"skip": False, "insight": text, "reason_if_skipped": None})
    assert not ok and "words" in (reason or "")


def test_trims_slightly_long_paragraph():
    insight = (
        "Rate hikes should widen HDFC Bank's margins as loans reprice upward, a key relief after recent pressure. "
        "Leadership churn under incoming CEO Anup Bagchi and the leak probe keep governance the main overhang. "
        "Holders should watch whether deposit growth and retail lending can turn the margin recovery into steadier earnings."
    )
    ok, lines, reason = parse_insight_lines({"skip": False, "insight": insight, "reason_if_skipped": None})
    assert ok and reason is None and len(lines) == 1
    words = len(lines[0].split())
    assert INSIGHT_WORD_MIN <= words <= INSIGHT_WORD_MAX


def test_prompt_insight_not_summary():
    lower = SYSTEM_PROMPT.lower()
    assert "insight" in lower and "summar" in lower
    assert "24" in lower and "36" in lower
    assert "paragraph" in lower
    assert "impact" in lower and "holder" in lower
    assert INSIGHT_WORD_MIN <= 30 <= INSIGHT_WORD_MAX