"""Planner portfolio_intent maps to a fixed bundle. No question matching."""

from news_rag.insight.contracts import AnswerMode, ExecutionPlan
from news_rag.insight.plan import PLAN_SCHEMA, _PLAN_PROMPT
from news_rag.insight.portfolio_intents import (
    apply_portfolio_intent,
    data_need_for,
    modules_for,
    normalize_portfolio_intent,
    shape_for,
    should_attach_news,
)


def test_unknown_intent_is_none():
    assert normalize_portfolio_intent("not-a-real-intent") == "none"
    assert normalize_portfolio_intent("") == "none"
    assert shape_for("nope") == "none"


def test_fact_bundle_and_shape():
    assert shape_for("aum") == "fact"
    assert modules_for("aum") == ["summary"]
    assert data_need_for("aum") == "investor_summary"
    assert shape_for("portfolio_overview") == "brief"
    assert "allocation" in modules_for("health_check")
    assert "profile_risk" in modules_for("health_check")


def test_schema_lists_portfolio_intent():
    props = PLAN_SCHEMA["properties"]["understanding"]["properties"]
    assert "aum" in props["portfolio_intent"]["enum"]
    assert "none" in props["portfolio_intent"]["enum"]


def test_apply_fact_skips_news_and_composer():
    plan = ExecutionPlan(
        portfolio_intent="aum",
        portfolio_scope="none",
        data_need="none",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        requires_compose=True,
        tool_calls=[],
    )
    from news_rag.insight.contracts import ToolCall

    plan.tool_calls = [ToolCall(tool="search_financial_news", arguments={}, wave=2)]
    apply_portfolio_intent(plan)
    assert plan.portfolio_scope == "investor"
    assert plan.data_need == "investor_summary"
    assert plan.answer_mode == AnswerMode.DATA_ONLY
    assert plan.requires_compose is False
    assert plan.tool_calls == []
    assert should_attach_news("aum") is False
    assert should_attach_news("portfolio_overview") is True
    assert should_attach_news("where_losing") is True
    assert should_attach_news("scheme_performance") is False


def test_prompt_mentions_portfolio_intent():
    assert "portfolio_intent" in _PLAN_PROMPT
    assert "portfolio_overview" in _PLAN_PROMPT


def test_xirr_fact_reads_xirr_module_slice():
    from news_rag.insight.fact_answer import render_portfolio_fact

    data = {
        "meta": {"as_of_date": "2026-11-11"},
        "xirr": {"portfolio_xirr_pct": 12.98},
    }
    text = render_portfolio_fact("xirr", data)
    assert "12.98" in text
    assert "not available" not in text.lower()


def test_st_vs_lt_gains_from_pnl_summary():
    from news_rag.insight.fact_answer import render_portfolio_fact

    book = {
        "meta": {"as_of_date": "2026-11-11"},
        "pnl_summary": {"short_term_gain_inr": 4000.5, "long_term_gain_inr": 802.6},
    }
    text = render_portfolio_fact("st_vs_lt_gains", book)
    assert "4,000.5" in text or "4000.5" in text
    assert "802.6" in text
    assert "not available" not in text.lower()


def test_next_sip_uses_normalized_next_due_date():
    from news_rag.insight.fact_answer import render_portfolio_fact

    book = {
        "sip": {
            "plans": [
                {"scheme_name": "Later Fund", "next_due_date": "2026-11-15"},
                {"scheme_name": "Soon Fund", "next_due_date": "2026-11-12"},
            ]
        }
    }
    text = render_portfolio_fact("next_sip", book)
    assert "2026-11-12" in text
    assert "Soon Fund" in text
    assert "don't have" not in text.lower()


def test_nav_of_scheme_picks_planned_fund_not_first_holding():
    from news_rag.insight.contracts import ExecutionPlan
    from news_rag.insight.fact_answer import render_portfolio_fact

    book = {
        "meta": {"as_of_date": "2026-11-11"},
        "holdings": [
            {"scheme_name": "Invesco India Large & Mid Cap Fund - Regular Plan - Growth", "current_nav": 112.96, "nav_date": "2026-11-09"},
            {"scheme_name": "Quant Small Cap Fund - Growth", "current_nav": 282.7207, "nav_date": "2026-11-09"},
        ],
    }
    plan = ExecutionPlan(funds=["Quant Small Cap Fund - Growth"], portfolio_intent="nav_of_scheme")
    text = render_portfolio_fact("nav_of_scheme", book, plan=plan)
    assert "Quant Small Cap" in text
    assert "282.72" in text
    assert "Invesco" not in text
