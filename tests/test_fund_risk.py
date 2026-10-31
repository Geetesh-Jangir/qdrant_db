from news_rag.fund_risk import (
    asks_risk_trend_comparison,
    asks_sebi_riskometer,
    ensure_risk_tools,
    exposure_from_detail,
    normalize_rating,
    render_risk_lines,
)
from news_rag.insight.contracts import AnswerMode, EvidencePack, ExecutionPlan, ToolCall
from news_rag.insight.evidence_pack import investor_fact_brief, render_data_only_template
from news_rag.insight.multi_fact import ensure_multi_fact_tools

_RATING = {
    "success": True,
    "data": {
        "fundType": "equity",
        "finalScore": 64.55,
        "maxPossibleScore": 100,
        "label": "Good Choice",
        "inputs": {"sharpe": 1.23, "beta": 0.91, "stdDev": 12.4, "sortino": 1.1, "alpha": 0.4},
        "pillars": {
            "performance": {"score": 32.05, "max": 40},
            "risk": {"score": 10.5, "max": 25},
            "portfolioQuality": {"score": 15.5, "max": 25},
            "fundManager": {"score": 6.5, "max": 10},
        },
    },
}

_DETAIL = {
    "sebi_riskometer": "Very High",
    "asset_allocation": [
        {"label": "Equity", "percentage": 98.4},
        {"label": "Cash", "percentage": 1.09},
        {"label": "Debt", "percentage": 0.51},
    ],
    "market_cap": [
        {"label": "Large Cap", "percentage": 82.91},
        {"label": "Mid Cap", "percentage": 14.60},
        {"label": "Small Cap", "percentage": 0},
    ],
}


def _public_summary(question: str = "How risky is this fund?") -> dict:
    summary = normalize_rating(_RATING) or {}
    summary.update(exposure_from_detail(_DETAIL))
    summary["lines"] = render_risk_lines(summary, question)
    return summary


def test_api_label_is_kept_as_sent():
    payload = {
        "data": {
            "fundType": "equity",
            "finalScore": 64.55,
            "maxPossibleScore": 100,
            "label": "Recommended",
        }
    }
    summary = normalize_rating(payload)
    assert summary is not None
    assert summary["label"] == "Recommended"
    assert summary["final_score"] == 64.55


def test_category_question_explains_the_ranges_without_a_tool_call():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["risk"]}, wave=1)],
    )
    ensure_risk_tools("How are the score labels categorized?", plan)
    assert plan.tool_calls == []
    assert plan.requires_compose is True
    assert "80 to 100" in plan.concept_brief
    assert "60 to 69 Good Choice" in plan.concept_brief
    assert "0 to 49 Underperformer" in plan.concept_brief


def test_public_summary_keeps_pillar_marks_and_drops_inputs():
    summary = _public_summary()
    assert summary["final_score"] == 64.55
    assert summary["label"] == "Good Choice"
    assert summary["fund_type"] == "equity"
    assert summary["pillars"]["performance"]["score"] == 32.05
    assert summary["pillars"]["performance"]["max"] == 40
    assert summary["pillars"]["fundManager"]["score"] == 6.5
    assert "inputs" not in summary
    assert "sharpe" not in str(summary).lower()


def test_debt_pillar_max_uses_api_max_score_field():
    from news_rag.fund_risk import normalize_rating

    payload = {
        "data": {
            "fundType": "debt",
            "finalScore": 63,
            "label": "Good Choice",
            "pillars": {
                "performance": {"score": 21, "maxScore": 35},
                "risk": {"score": 8, "maxScore": 25},
                "portfolioQuality": {"score": 20, "maxScore": 25},
                "fundManager": {"score": 14, "maxScore": 15},
            },
        }
    }
    summary = normalize_rating(payload)
    assert summary is not None
    assert summary["pillars"]["performance"]["max"] == 35
    assert summary["pillars"]["fundManager"]["max"] == 15
    assert summary["pillars"]["fundManager"]["score"] == 14


def test_general_pillar_max_question_uses_concept_brief():
    from news_rag.fund_risk import asks_pillar_structure, asks_rating_concept, ensure_risk_tools

    question = "what are the rupeestop pillars and what is each pillar max score"
    assert asks_pillar_structure(question)
    assert asks_rating_concept(question)
    plan = ExecutionPlan(intent="lookup", answer_mode=AnswerMode.DATA_ONLY, funds=[], tool_calls=[])
    ensure_risk_tools(question, plan)
    assert plan.tool_calls == []
    assert "depends on the fund type" in plan.concept_brief


def test_fund_quality_question_maps_to_portfolio_quality_pillar():
    from news_rag.fund_risk import asks_pillar_mark, pillar_focus

    q = "whats the fund quality of the absl Banking & PSU Debt Fund"
    assert pillar_focus(q) == "portfolioQuality"
    assert asks_pillar_mark(q)


def test_fund_manager_name_ask_is_not_fund_manager_pillar():
    from news_rag.fund_risk import pillar_focus, rating_lead

    q = "tell me a random fund and tell me the name of the fund manager"
    assert pillar_focus(q) == ""
    lead = rating_lead(
        {
            "final_score": 70,
            "label": "Recommended",
            "pillars": {"fundManager": {"label": "Fund manager", "score": 4.75, "max": 10}},
        },
        q,
    )
    assert lead == ""


def test_what_is_rs_rating_goes_to_the_composer_with_the_pillars():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=[],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)],
    )
    ensure_risk_tools("what is rs rating", plan)
    assert plan.tool_calls == []
    assert plan.requires_compose is True
    assert plan.direct_reply == ""
    assert "four pillars" in plan.concept_brief
    assert "portfolio quality" in plan.concept_brief
    assert "fund manager" in plan.concept_brief
    assert "fund pages" not in plan.concept_brief.lower()


def test_good_choice_versus_very_high_does_not_look_up_a_fund():
    plan = ExecutionPlan(
        intent="explain_cause",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["Choice Overnight Fund - Regular Plan - Growth"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["risk"]}, wave=1)],
    )
    ensure_risk_tools("How can a fund be a Good Choice and still have Very High risk?", plan)
    assert plan.tool_calls == []
    assert plan.funds == []
    assert plan.requires_compose is True
    assert "four pillars" in plan.concept_brief
    assert "Very High" in plan.concept_brief
    assert "not a statement that the fund is low risk" in plan.concept_brief


def test_portfolio_quality_score_is_the_mark_not_the_formula():
    from news_rag.fund_risk import rating_lead

    text = rating_lead(_public_summary(), "What is the portfolio quality score?")
    assert "15.5 out of 25" in text
    assert "32.05" not in text
    assert "sharpe" not in text.lower()
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)],
    )
    ensure_risk_tools("What is the portfolio quality score?", plan)
    assert plan.tool_calls
    assert plan.direct_reply == ""


def test_methodology_question_is_refused():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["risk"]}, wave=1)],
    )
    ensure_risk_tools("How do you calculate the score?", plan)
    assert plan.tool_calls == []
    assert "not shown" in plan.direct_reply


def test_risk_answer_keeps_exposure_and_drops_sharpe():
    text = _public_summary("How risky is HDFC Large Cap?")["lines"]
    assert "Very High" in text
    assert "98.40%" in text
    assert "82.91%" in text
    assert "64.55" in text
    assert "Good Choice" in text
    assert "do not add to 100" in text
    assert "1.23" not in text
    assert "sharpe" not in text.lower()
    assert "32.05" not in text
    assert "10.5" not in text
    assert "80 to 100" not in text


def test_why_good_choice_uses_the_api_label_and_explains_the_ranges():
    text = render_risk_lines(_public_summary(), "Why is this fund a Good Choice?")
    assert "Good Choice" in text
    assert "64.55" in text
    assert "60 to 69 Good Choice" in text
    assert "Equity" not in text


def test_score_question_names_the_pillars_without_their_numbers():
    text = render_risk_lines(_public_summary(), "What is the RupeeStop score?")
    assert "64.55" in text
    assert "Good Choice" in text
    assert "portfolio quality" in text
    assert "Equity" not in text
    assert "32.05" not in text


def test_how_risky_fetches_risk_and_drawdown():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        requires_compose=True,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="search_financial_news", arguments={}, wave=1)],
    )
    ensure_multi_fact_tools("How risky is HDFC Large Cap?", plan)
    ensure_risk_tools("How risky is HDFC Large Cap?", plan)
    call = next(item for item in plan.tool_calls if item.tool == "get_fund_data")
    assert "risk" in call.arguments["modules"]
    assert "drawdown" in call.arguments["modules"]
    assert "sharpe" not in str(call.arguments).lower()


def test_why_very_high_keeps_the_risk_fetch():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="search_financial_news", arguments={}, wave=1)],
    )
    ensure_multi_fact_tools("why is it Very High?", plan)
    ensure_risk_tools("why is it Very High?", plan)
    call = next(item for item in plan.tool_calls if item.tool == "get_fund_data")
    assert "risk" in call.arguments["modules"]
    assert "drawdown" in call.arguments["modules"]
    assert any(item.tool == "search_financial_news" for item in plan.tool_calls)


def test_sebi_risk_score_question_is_detected():
    assert asks_sebi_riskometer("whats the sebi risk score of this")
    assert not asks_sebi_riskometer("what is the risk pillar score")


def test_less_riskier_question_gets_trend_composer_note():
    assert asks_risk_trend_comparison("is it less riskier?")
    plan = ExecutionPlan(
        routed_by="planner",
        intent="explain_cause",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["Aditya Birla Sun Life Banking & PSU Debt Fund - Growth"],
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["risk", "drawdown", "rating"], "periods": ["1y", "3y", "5y"]},
                wave=1,
            )
        ],
    )
    ensure_risk_tools("is it less riskier?", plan)
    assert "We can't get that data right now" in (plan.presentation_notes or "")
    assert plan.requires_compose is True


def test_strip_removes_risk_trend_apology():
    from news_rag.insight.fund_display import strip_missing_data_caveats

    prose = (
        "**Short answer: the data here cannot show whether this fund has become less risky over time.** "
        "We only have one snapshot of risk measures, with no earlier reading to compare against."
    )
    cleaned = strip_missing_data_caveats(prose)
    assert "snapshot" not in cleaned.lower()
    assert "earlier reading" not in cleaned.lower()


def test_risk_pillar_question_keeps_the_fund_lookup():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)],
    )
    ensure_risk_tools("What is the risk pillar?", plan)
    assert plan.direct_reply == ""
    call = next(item for item in plan.tool_calls if item.tool == "get_fund_data")
    assert call.arguments["modules"] == ["rating"]
    assert plan.requires_compose is True


def test_planner_pillar_question_replaces_wrong_modules():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["Taurus Large Cap Fund - Regular Plan - Growth"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["managers"]}, wave=1)],
    )
    ensure_risk_tools("tell me about the risk pillar of this fund", plan)
    call = next(item for item in plan.tool_calls if item.tool == "get_fund_data")
    assert call.arguments["modules"] == ["rating"]


def test_score_question_does_not_add_drawdown():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)],
    )
    ensure_multi_fact_tools("What is the RupeeStop score of HDFC Large Cap?", plan)
    ensure_risk_tools("What is the RupeeStop score of HDFC Large Cap?", plan)
    call = plan.tool_calls[0]
    assert call.arguments["modules"] == ["risk"]
    assert plan.requires_compose is False


def test_risk_only_template_shows_the_public_lines():
    summary = _public_summary("How risky is this fund?")
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        requires_compose=False,
        funds=["HDFC Large Cap Fund"],
        asked_facts=["risk"],
    )
    pack = EvidencePack(data_pack={"fund:HDFC Large Cap Fund": {"risk": summary}})
    text = render_data_only_template(pack, plan)
    assert text is not None
    assert "Very High" in text
    assert "82.91%" in text
    assert "sharpe" not in text.lower()


def test_risk_analysis_lead_does_not_treat_the_pillar_as_the_risk_level():
    from news_rag.fund_risk import exposure_from_detail, rating_lead
    from news_rag.insight.fund_display import strip_missing_data_caveats
    from news_rag.insight.grounding import cores_in_text, derived_cores, strip_ungrounded_numbers

    text = rating_lead(_public_summary(), "do the risk analysis of the bandhan large cap?")
    assert "Risk pillar" in text
    assert "10.5 out of 25" in text
    assert "does not say the fund is more risky or less risky" in text
    exposure = exposure_from_detail(
        {
            "market_cap": [
                {"label": "Large Cap", "percentage": 80.54},
                {"label": "Mid Cap", "percentage": 10.87},
                {"label": "Small Cap", "percentage": 7.76},
            ]
        }
    )
    assert exposure["smaller_companies_pct"] == 18.63
    allowed = cores_in_text("10.87 7.76") | derived_cores(cores_in_text("10.87 7.76"))
    kept = strip_ungrounded_numbers("about 18.63% sits in smaller companies", allowed)
    assert "18.63%" in kept
    cleaned = strip_missing_data_caveats(
        "The fund is Very High risk. Drawdown history is not available in this data."
    )
    assert "Very High" in cleaned
    assert "not available" not in cleaned


def test_rating_lead_lists_every_mark_for_a_fund_question():
    from news_rag.fund_risk import blocked_reply, rating_lead

    text = rating_lead(_public_summary(), "tell me about hdfc large cap")
    assert "64.55" in text
    assert "Good Choice" in text
    assert "32.05/40" in text
    assert "6.5/10" in text
    assert "sharpe" not in text.lower()
    assert blocked_reply("which model is used for generating the response?")
    assert "built" in blocked_reply("which model is used?")
    assert blocked_reply("how do you calculate the score?") == "Internal calculations are not shown."


def test_missing_apology_and_private_leak_are_removed():
    from news_rag.insight.fund_display import strip_missing_data_caveats, strip_private_leaks

    text = "The 1-year return is not in the data, so it cannot be compared.\nNAV is 74."
    cleaned = strip_missing_data_caveats(text)
    assert "cannot be compared" not in cleaned
    assert "NAV is 74" in cleaned
    leaked = "This answer uses claude. NAV is 74."
    hidden = strip_private_leaks(leaked)
    assert "claude" not in hidden.lower()
    assert "NAV is 74" in hidden


def test_vs_benchmark_module_is_not_replaced_by_snapshot():
    from news_rag.insight.capabilities.catalog import validate_capability_args

    args = validate_capability_args("get_fund_data", {"modules": ["vs_benchmark", "rating"]})
    assert args["modules"] == ["vs_benchmark", "rating"]
    assert "snapshot" not in args["modules"]
    assert "return_series" not in args["modules"]
    assert "attribution" not in args["modules"]


def test_mixed_question_adds_risk_lines_to_the_note():
    summary = _public_summary("What is the NAV and how risky is this fund?")
    pack = {
        "fund:HDFC Large Cap Fund": {
            "snapshot": {"fund_name": "HDFC Large Cap Fund", "nav": 1123.45, "nav_date": "2026-10-27"},
            "risk": summary,
        }
    }
    text = investor_fact_brief(pack, ["nav", "risk"])
    assert "NAV" in text
    assert "Very High" in text
    assert "98.40%" in text
    assert "sharpe" not in text.lower()
