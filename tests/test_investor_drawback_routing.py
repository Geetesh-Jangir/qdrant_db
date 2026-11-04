from news_rag.insight.contracts import AnswerMode, EvidencePack, ExecutionPlan, ToolCall
from news_rag.insight.investor_drawback import (
    build_drawdown_wave2_calls,
    plan_wants_investor_drawdown_fetch,
    plan_wants_portfolio_drawback,
    plan_wants_pure_concentration,
    question_asks_portfolio_level_drawdown,
    render_portfolio_drawback_answer,
)
from news_rag.insight.portfolio_scope import enforce_portfolio_scope, plan_wants_concentration


def test_drawback_question_is_not_pure_concentration():
    plan = ExecutionPlan(
        planner_reading="Biggest weakness in the user's own portfolio, judged from holdings and concentration",
    )
    assert plan_wants_portfolio_drawback(plan, "whats the biggest drawback in my portfolio")
    assert not plan_wants_pure_concentration(plan, "whats the biggest drawback in my portfolio")
    assert not plan_wants_concentration(plan, "whats the biggest drawback in my portfolio")


def test_pure_concentration_question():
    plan = ExecutionPlan(planner_reading="Portfolio concentration breakdown")
    assert plan_wants_pure_concentration(plan, "how concentrated is my portfolio")
    assert not plan_wants_portfolio_drawback(plan, "how concentrated is my portfolio")


def test_enforce_drawback_strips_catalog_and_adds_modules(monkeypatch):
    monkeypatch.setenv("CLIENT_REF_NO", "CRN-test")
    plan = ExecutionPlan(
        answer_mode=AnswerMode.INSIGHT_FUSION,
        data_need="investor_hybrid",
        funds=["Random Catalog Fund"],
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={"modules": ["summary"]}, wave=1),
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
        ],
    )
    plan = enforce_portfolio_scope(
        plan,
        memory={},
        question="whats the biggest drawback in my portfolio",
    )
    assert plan.funds == []
    assert all(c.tool != "get_fund_data" for c in plan.tool_calls)
    modules = plan.tool_calls[0].arguments.get("modules") or []
    assert "holdings" in modules
    assert "concentration" in modules


def test_build_drawdown_wave2_from_holdings():
    wave1 = [
        {
            "ok": True,
            "tool": "get_investor_portfolio",
            "data": {
                "holdings": [
                    {"scheme_name": "Fund A", "xirr_pct": -5, "aum_inr": 100, "isin": "INF000000001"},
                    {"scheme_name": "Fund B", "xirr_pct": 3, "aum_inr": 500, "isin": "INF000000002"},
                ],
            },
        },
    ]
    calls = build_drawdown_wave2_calls(wave1, max_funds=2)
    assert len(calls) == 2
    assert calls[0].tool == "get_fund_data"
    assert "drawdown" in calls[0].arguments.get("modules", [])


def test_portfolio_drawdown_question_triggers_wave2_fetch():
    plan = ExecutionPlan(
        data_need="investor_risk",
        asked_facts=["drawdown"],
        holding_scope="all_holdings",
    )
    q = "what is the biggest drawdown in my portfolio"
    assert plan_wants_investor_drawdown_fetch(plan, q)
    assert question_asks_portfolio_level_drawdown(q, plan)


def test_render_drawback_includes_underperformers():
    plan = ExecutionPlan(planner_reading="weakness in portfolio")
    pack = EvidencePack(
        data_pack={
            "investor_portfolio": {
                "meta": {"as_of_date": "2026-11-02"},
                "summary": {
                    "invested_inr": 10000,
                    "aum_inr": 10100,
                    "gain_loss_inr": 100,
                    "absolute_return_pct": 1.0,
                    "portfolio_xirr_pct": 1.5,
                },
                "allocation": {"schemeTypeShare": [{"name": "equity", "aum_pct": 100}]},
                "holdings": [
                    {
                        "scheme_name": "Bad Fund",
                        "scheme_category": "contra",
                        "aum_inr": 5000,
                        "invested_inr": 5200,
                        "gain_loss_inr": -200,
                        "xirr_pct": -8.0,
                        "absolute_return_pct": -4.0,
                    },
                ],
                "computed": {
                    "allocation_by_category": [{"category": "contra", "weight_pct": 100}],
                },
            },
        },
    )
    text = render_portfolio_drawback_answer(pack, plan, "biggest drawback in my portfolio")
    assert text is not None
    assert "Bad Fund" in text
    assert "Scheme performance" in text
    assert "Portfolio concentration" not in text or "Underlying concentration" in text
