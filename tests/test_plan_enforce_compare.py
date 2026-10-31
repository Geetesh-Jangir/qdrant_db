from news_rag.insight.contracts import ExecutionPlan
from news_rag.insight.plan_enforce import apply_planner_post_hooks
from news_rag.insight.plan_intent import reconcile_planner_intent


def test_compare_categories_not_replaced_by_composition():
    q = "compare a conservative hybrid and aggressive hybrid fund"
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        fund_pick="compare_categories",
        data_need="category_composition",
        tool_calls=[],
    )
    reconcile_planner_intent(plan, q)
    assert plan.data_need == "none"
    assert len(plan.scheme_categories) >= 2

    plan2 = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        fund_pick="compare_categories",
        data_need="category_composition",
        tool_calls=[],
    )
    out = apply_planner_post_hooks(q, plan2, None)
    tools = [c.tool for c in out.tool_calls]
    assert tools.count("screen_funds_by_exposure") == 2
    assert "get_portfolio_data" not in tools
