from news_rag.insight.contracts import ExecutionPlan
from news_rag.insight.fund_name_gate import clarify_plan_if_fund_unknown
from news_rag.insight.plan_enforce import apply_planner_post_hooks

_IDEAL_Q = (
    "for a ideal portfolio show should it look like and what categories "
    "and assets it should hold"
)


def test_ideal_portfolio_does_not_bind_catalog_fund():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="overview",
        data_need="category_composition",
        tool_calls=[],
        funds=[],
    )
    out = apply_planner_post_hooks(_IDEAL_Q, plan, None)
    assert not out.funds
    assert not any(c.tool in ("get_fund_data", "get_portfolio_data") for c in out.tool_calls)
    final = clarify_plan_if_fund_unknown(out, None, _IDEAL_Q)
    assert not final.funds
    assert not any(c.tool in ("get_fund_data", "get_portfolio_data") for c in final.tool_calls)
