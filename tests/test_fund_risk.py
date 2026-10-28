from news_rag.fund_risk import (
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


def test_public_summary_drops_pillars_and_inputs():
    summary = _public_summary()
    assert summary["final_score"] == 64.55
    assert summary["label"] == "Good Choice"
    assert summary["fund_type"] == "equity"
    blob = " ".join(summary.keys()).lower()
    assert "pillar" not in blob
    assert "input" not in blob
    assert "sharpe" not in blob
    assert "32.05" not in str(summary)


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


def test_portfolio_quality_question_is_refused_without_a_tool_call():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)],
    )
    ensure_risk_tools("What is the portfolio quality score?", plan)
    assert plan.tool_calls == []
    assert plan.direct_reply == "Internal calculations are not shown."


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


def test_risk_pillar_question_is_refused():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)],
    )
    ensure_risk_tools("What is the risk pillar?", plan)
    assert plan.tool_calls == []
    assert plan.direct_reply == "Internal calculations are not shown."


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
