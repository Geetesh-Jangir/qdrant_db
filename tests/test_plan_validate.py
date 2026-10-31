from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.plan_validate import validate_plan_tools


def test_validate_adds_risk_when_planner_only_portfolio_holdings():
    memory = {"list_cursor": {"rows": [{"name": "ICICI Prudential Flexi Cap Fund - Growth"}]}}
    plan = ExecutionPlan(
        routed_by="planner",
        funds=["ICICI Prudential Flexi Cap Fund - Growth"],
        tool_calls=[
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": ["holdings"], "top_n": 3},
                wave=1,
            ),
        ],
    )
    out = validate_plan_tools("top holdings of the fund", plan, memory)
    modules = next(c for c in out.tool_calls if c.tool == "get_fund_data").arguments["modules"]
    assert "risk" in modules
    port = next(c for c in out.tool_calls if c.tool == "get_portfolio_data")
    assert "sectors" in port.arguments["sections"]
    assert port.arguments["top_n"] >= 5
