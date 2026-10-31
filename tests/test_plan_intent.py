from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.plan_intent import normalize_fund_pick_from_planner, plan_wants_alternate_in_category


def test_normalize_fund_pick_from_planner_reading():
    plan = ExecutionPlan(
        goal="Suggest a different flexi cap fund",
        planner_reading="User wants another fund in flexi cap, not the one already named",
        tool_calls=[ToolCall(tool="screen_funds_by_exposure", arguments={"top_n": 1}, wave=1)],
    )
    assert not plan_wants_alternate_in_category(plan)
    normalize_fund_pick_from_planner(plan)
    assert plan_wants_alternate_in_category(plan)
    assert plan.fund_pick == "alternate_in_category"


def test_pick_alternate_tool_arg_counts():
    plan = ExecutionPlan(
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"pick_alternate": True, "top_n": 1},
                wave=1,
            ),
        ],
    )
    assert plan_wants_alternate_in_category(plan)
