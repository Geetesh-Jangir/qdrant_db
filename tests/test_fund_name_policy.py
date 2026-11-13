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


def test_server_pick_strips_chat_only_funds():
    memory = {
        "chat_turns": [
            {
                "user": "pick a random fund",
                "assistant": "ITI Small Cap Fund - Regular Plan - Growth is a small cap scheme.",
            }
        ],
    }
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        funds=["ITI Small Cap Fund - Regular Plan - Growth"],
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"compare_pair": True, "random_sample": True, "top_n": 2},
                wave=1,
            ),
            ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1),
        ],
    )
    out = enforce_user_authorized_funds_only(
        plan,
        memory,
        "pick two random equity funds and compare them",
    )
    assert out.funds == []


def test_prior_answer_names_are_authorized():
    memory = {
        "chat_turns": [
            {
                "user": "which funds",
                "assistant": "HDFC BSE Sensex ETF and Bandhan BSE Sensex ETF",
            }
        ]
    }
    assert fund_authorized_for_question("HDFC BSE Sensex ETF", "tell me about those funds", memory)
    assert not fund_authorized_for_question("Axis NIFTY IT ETF", "tell me about those funds", memory)


def test_compare_these_two_funds_binds_chat_pair():
    memory = {
        "chat_turns": [
            {"user": "what is hdfc large cap fund", "assistant": "HDFC Large Cap Fund - Growth is a large cap scheme."},
            {"user": "what is absl large cap", "assistant": "Aditya Birla Sun Life Large Cap Fund is a large cap scheme."},
        ],
        "frame": {"last_fund_focus": "Aditya Birla Sun Life Large Cap Fund"},
    }
    plan = ExecutionPlan(routed_by="planner", intent="compare", tool_calls=[], funds=[])
    out = apply_planner_post_hooks("compare these two funds", plan, memory)
    assert any(c.tool == "compare_funds" for c in out.tool_calls)
    assert len(out.funds) >= 2


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
