"""Closing summary helpers on composed answers."""

from news_rag.ask_composer import _clamp_closing_words, _closing_from_bullets, _word_count


def test_word_count_basic():
    assert _word_count("one two three") == 3


def test_clamp_closing_trims_long_text():
    long = " ".join(["word"] * 200)
    out = _clamp_closing_words(long)
    assert _word_count(out) <= 165
    assert out.endswith(".")


def test_closing_from_bullets_builds_prose():
    bullets = [
        "**HDFC Large Cap** NAV is **₹100** with **1 year** return **+12%**.",
        "News on **IT** earnings may affect top holding **Infosys**.",
    ]
    closing = _closing_from_bullets("HDFC Large Cap overview", bullets, "How is HDFC Large Cap doing?")
    assert closing
    assert _word_count(closing) >= 10
