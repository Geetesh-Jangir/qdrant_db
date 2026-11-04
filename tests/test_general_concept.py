from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.general_concept import (
    apply_pure_concept_plan,
    question_is_pure_general_concept,
)
from news_rag.insight.plan_enforce import apply_planner_post_hooks


def test_large_cap_vs_mid_cap_is_pure_concept():
    q = "what is large cap and how is it different from mid cap"
    assert question_is_pure_general_concept(q)
    plan = ExecutionPlan(
        routed_by="planner",
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)],
    )
    plan = apply_pure_concept_plan(plan, q)
    assert plan.tool_calls == []
    assert plan.requires_compose is True


def test_named_large_cap_scheme_keeps_tools():
    q = "what is the aum and expense ratio of hdfc large cap fund"
    assert not question_is_pure_general_concept(q)
    plan = ExecutionPlan(
        routed_by="planner",
        planner_task="data",
        funds=["HDFC Large Cap Fund - Growth"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)],
    )
    plan = apply_pure_concept_plan(plan, q)
    assert any(call.tool == "get_fund_data" for call in plan.tool_calls)


def test_my_funds_is_not_pure_concept():
    q = "show me the rs rating of all my funds"
    assert not question_is_pure_general_concept(q)


def test_all_holdings_metrics_adds_investor_tool():
    memory = {
        "holdings_in_chat": [
            {"name": "Fund A - Growth", "isin": "INF000000001", "category": "large cap"},
            {"name": "Fund B - Growth", "isin": "INF000000002", "category": "mid cap"},
        ],
    }
    plan = ExecutionPlan(
        routed_by="planner",
        portfolio_scope="investor",
        data_need="investor_holding",
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["rating"]}, wave=1)],
    )
    plan = apply_planner_post_hooks("rs rating of all my funds", plan, memory)
    assert any(c.tool == "get_investor_portfolio" for c in plan.tool_calls)
    assert str(plan.holding_scope or "") == "all_holdings"
    assert len(plan.funds or []) == 2
