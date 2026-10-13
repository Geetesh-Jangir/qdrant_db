from news_rag.insight.brief import _heuristic_brief, build_question_brief, plan_evidence


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


def test_market_which_sectors_down_plans_sector_impact():
    q = "whats happening in the market right now? and which sectors are going down?"
    brief = _heuristic_brief(q)
    needs = plan_evidence(brief, q)
    assert "market_overview" in needs
    assert "sector_impact_direction" in needs
    assert "exposure_link" not in needs
