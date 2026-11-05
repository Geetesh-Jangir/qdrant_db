from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.fund_name_policy import (
    enforce_user_authorized_funds_only,
    fund_authorized_for_question,
    plan_allows_server_fund_pick,
)
from news_rag.insight.plan_enforce import apply_planner_post_hooks


def test_invented_funds_stripped_when_not_in_chat():
    memory = {
        "frame": {"last_fund_focus": "HDFC Large Cap Fund - Growth"},
        "chat_turns": [
            {"user": "should i buy hdfc large cap fund", "assistant": "ok"},
        ],
    }
    plan = ExecutionPlan(
        funds=["The Wealth Company Arbitrage Fund - Regular Plan - Growth"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)],
    )
    out = enforce_user_authorized_funds_only(
        plan, memory, "what is its expense ratio"
    )
    assert out.funds == []


def test_random_compare_allows_server_pick():
    plan = ExecutionPlan(intent="compare", funds=[])
    q = "compare two random equity funds"
    assert plan_allows_server_fund_pick(q, plan, None) is True


def test_user_named_fund_kept():
    memory = {}
    name = "HDFC Large Cap Fund - Growth"
    assert fund_authorized_for_question(name, "tell me hdfc large cap fund nav", memory)


def test_compare_both_still_rebinds_after_strip():
    memory = {
        "frame": {
            "last_fund_focus": "HDFC Large Cap Fund - Growth",
            "subjects": [{"name": "HDFC Large Cap Fund - Growth", "role": "primary"}],
        },
        "entity_stack": [{"name": "HDFC Large Cap Fund - Growth"}],
        "chat_turns": [
            {"user": "should i buy hdfc large cap fund", "assistant": "..."},
            {"user": "what is the 1 year category avg of absl large cap", "assistant": "..."},
        ],
    }
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
        funds=[
            "The Wealth Company Arbitrage Fund - Regular Plan - Growth",
            "Axis Children's Fund - Compulsory Lock-in - Regular Plan - Growth",
        ],
    )
    out = apply_planner_post_hooks("do the fund comparison of both", plan, memory)
    assert not any("Wealth Company" in n for n in out.funds)
    assert any("HDFC" in n for n in out.funds)
