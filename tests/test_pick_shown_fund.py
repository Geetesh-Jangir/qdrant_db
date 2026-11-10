from news_rag.fund_rating_screen import parse_rating_screen
from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.memory.fund_context import fund_picked_from_prior_answer
from news_rag.insight.plan_enforce import apply_planner_post_hooks

_PRIOR = (
    "| Nippon India Silver ETF | 91.5 | -15.53% |\n"
    "| ICICI Prudential Silver ETF FOF - Growth | 85.75 | -15.68% |\n"
)


def test_pick_one_silver_from_above_is_not_an_unnamed_list() -> None:
    assert parse_rating_screen("pick any of the one silver fund from above and tell me more about it") is None


def test_any_two_of_the_above_compares_the_first_two_listed_funds() -> None:
    from news_rag.insight.memory.fund_context import funds_from_shown_list, merge_fund_isins_map
    from news_rag.insight.plan_enforce import bind_shown_list_followup

    memory = {
        "list_cursor": {
            "rows": [
                {"n": 1, "name": "Nippon India Silver ETF", "id": "INF204KC1402"},
                {"n": 2, "name": "ICICI Prudential Silver ETF FOF - Growth", "id": "INF109KC1Y64"},
                {"n": 3, "name": "HDFC Silver ETF", "id": "INF179KC1DI2"},
            ]
        }
    }
    question = "pick any two of the abovve and compare them"
    assert funds_from_shown_list(question, memory) == [
        "Nippon India Silver ETF",
        "ICICI Prudential Silver ETF FOF - Growth",
    ]
    isins = merge_fund_isins_map(memory)
    assert isins["nippon india silver etf"] == "INF204KC1402"
    assert isins["icici prudential silver etf fof - growth"] == "INF109KC1Y64"
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        funds=["Nippon India Silver ETF"],
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
    )
    out = bind_shown_list_followup(question, plan, memory)
    assert out.funds == [
        "Nippon India Silver ETF",
        "ICICI Prudential Silver ETF FOF - Growth",
    ]
    assert out.tool_calls[0].tool == "compare_funds"


def test_list_positions_and_the_period_the_user_named() -> None:
    from news_rag.insight.memory.fund_context import funds_from_shown_list
    from news_rag.insight.plan_enforce import bind_shown_list_followup
    from news_rag.insight.return_windows import windows_named_in_question

    memory = {
        "list_cursor": {
            "rows": [
                {"n": 1, "name": "Nippon India Silver ETF", "id": "INF204KC1402"},
                {"n": 2, "name": "ICICI Prudential Silver ETF FOF - Growth", "id": "INF109KC1Y64"},
                {"n": 3, "name": "HDFC Silver ETF", "id": "INF179KC1DI2"},
            ]
        }
    }
    assert funds_from_shown_list("the bottom 2", memory)[0].startswith("ICICI")
    assert funds_from_shown_list("the middle one", memory) == ["ICICI Prudential Silver ETF FOF - Growth"]
    assert funds_from_shown_list("the second one", memory) == ["ICICI Prudential Silver ETF FOF - Growth"]
    assert windows_named_in_question("what is the 8 month return") == ["8M"]
    assert windows_named_in_question("two year return") == ["2Y"]
    assert windows_named_in_question("ytd returns") == ["YTD"]
    assert windows_named_in_question("compare the top 2") == []
    plan = ExecutionPlan(routed_by="planner", funds=[], tool_calls=[])
    out = bind_shown_list_followup("the second one, 8 months return", plan, memory)
    assert out.funds == ["ICICI Prudential Silver ETF FOF - Growth"]
    assert out.tool_calls[0].tool == "get_fund_data"
    assert out.tool_calls[0].arguments["windows"] == ["8M"]
    sectors = ExecutionPlan(routed_by="planner", funds=[], tool_calls=[])
    out = bind_shown_list_followup("show their top 10 sectors", sectors, memory)
    assert len(out.funds) == 3
    assert out.tool_calls[0].tool == "get_portfolio_data"
    assert out.tool_calls[0].arguments["top_n"] == 10


def test_pick_one_silver_keeps_the_first_shown_fund_and_its_lookup() -> None:
    question = "pick any of the one silver fund from above and tell me more about it"
    memory = {"chat_turns": [{"user": "tell me a good silver fund", "assistant": _PRIOR}]}
    picked = fund_picked_from_prior_answer(question, memory)
    assert "Nippon India Silver ETF" in picked
    plan = ExecutionPlan(
        routed_by="planner",
        subject_ref="memory_stack",
        funds=[],
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot", "rating"]}, wave=1),
            ToolCall(tool="search_financial_news", arguments={"scope": "all", "topics": []}, wave=1),
        ],
    )
    out = apply_planner_post_hooks(question, plan, memory)
    assert out.funds and "Nippon India Silver ETF" in out.funds[0]
    assert any(call.tool == "get_fund_data" for call in out.tool_calls)
