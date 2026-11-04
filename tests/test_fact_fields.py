from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
from news_rag.insight.fields import bind_fields_to_tools, fields_from_question


def test_aum_then_aum_and_expense_are_separate_turns():
    first = fields_from_question("what is the aum of hdfc large cap fund")
    second = fields_from_question("what is the aum and expense ratio of this fund")
    assert first == ["aum"]
    assert second == ["aum", "expense_ratio"]


def test_nav_only_keeps_snapshot_and_drops_rating():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot", "rating", "limits"], "windows": ["1Y", "3Y", "5Y"]},
                wave=1,
            )
        ],
    )
    plan = bind_fields_to_tools("what is the nav of hdfc large cap fund", plan)
    call = next(item for item in plan.tool_calls if item.tool == "get_fund_data")
    assert call.arguments["modules"] == ["snapshot"]
    assert "rating" not in call.arguments["modules"]
    assert plan.asked_fields == ["nav"]


def test_book_value_uses_investor_summary_only():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        portfolio_scope="investor",
        tool_calls=[
            ToolCall(
                tool="get_investor_portfolio",
                arguments={"modules": ["summary", "holdings", "sip"]},
                wave=1,
            )
        ],
    )
    plan = bind_fields_to_tools("what is the aum of my portfolio", plan)
    call = next(item for item in plan.tool_calls if item.tool == "get_investor_portfolio")
    assert call.arguments["modules"] == ["summary"]
    assert plan.asked_fields == ["book_value"]


def test_compare_plan_is_not_pruned():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund", "Invesco Large Cap Fund"],
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
    )
    plan = bind_fields_to_tools("compare hdfc large cap and invesco large cap", plan)
    assert [call.tool for call in plan.tool_calls] == ["compare_funds"]
