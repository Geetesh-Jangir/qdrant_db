from news_rag.ask_composer import _emphasize_impact_text


def test_emphasize_bolds_nav_percent_and_names():
    text = "PPFAS Flexi Cap Fund NAV is ₹80.38 with 1-month return -2.84%."
    out = _emphasize_impact_text(
        text,
        ["PPFAS Flexi Cap Fund"],
        max_bold_spans=12,
    )
    assert "**NAV**" in out or "**PPFAS" in out
    assert "**-2.84%**" in out or "-2.84%" in out
    assert "₹" in out
