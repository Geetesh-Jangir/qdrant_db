"""Answer markdown repair."""

from news_rag.insight.answer_markdown import normalize_answer_markdown


def test_separator_and_bold_and_blank_line():
    raw = "Value is **12\n| Fund | Value |\n| Alpha | 10 |"
    text = normalize_answer_markdown(raw)
    assert text.count("**") % 2 == 0
    assert "| --- | --- |" in text
    assert "\n\n| Fund | Value |" in text


def test_pads_short_row():
    raw = "| A | B |\n| --- | --- |\n| only |"
    text = normalize_answer_markdown(raw)
    assert "| only | — |" in text
