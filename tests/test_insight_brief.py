from news_rag.insight.brief import build_question_brief


def test_heuristic_auto_question_facets():
    q = (
        "Tell me about the automobile sector and which funds are highly impacted. "
        "Are they positive or negative? Last 6 months and other sectors in those funds."
    )
    brief = build_question_brief(q)
    assert "exposure_link" in brief.evidence_needs
    assert "fund_composition" in brief.evidence_needs
    assert brief.window_days >= 150
    assert len(brief.sub_asks) >= 2
