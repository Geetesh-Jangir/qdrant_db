from news_rag.fund_rupeestop_metrics import asks_category_performance
from news_rag.fund_rating_categories import match_all_scheme_categories
from news_rag.insight.category_plan import (
    asks_category_composition,
    asks_cross_category_compare,
    asks_fund_holdings_followup,
    ensure_alternate_category_fund_plan,
    ensure_category_composition_plan,
    ensure_category_performance_plan,
    ensure_cross_category_compare_plan,
    ensure_fund_holdings_followup_plan,
    ensure_rating_list_funds,
)
from news_rag.insight.plan_validate import validate_plan_tools
from news_rag.insight.contracts import ExecutionPlan, ToolCall


def test_asks_category_performance_on_follow_up():
    assert asks_category_performance("hows the category is performing")
    assert asks_category_performance("how is this category performing")
    assert not asks_category_performance("which banking sector funds are performing well")


def test_category_performance_replaces_blind_screen_with_memory_fund():
    memory = {
        "frame": {
            "subjects": [
                {
                    "name": "Aditya Birla Sun Life Credit Risk Fund - Regular Plan - Growth",
                    "role": "primary",
                }
            ]
        }
    }
    plan = ExecutionPlan(
        routed_by="planner",
        data_need="category_performance",
        intent="overview",
        funds=[],
        tool_calls=[
            ToolCall(tool="screen_funds_by_exposure", arguments={"top_n": 5, "return_window": "1Y"}, wave=1),
            ToolCall(tool="get_market_snapshot", arguments={"modules": ["index_return"]}, wave=1),
        ],
    )
    ensure_category_performance_plan("hows the category is performing", plan, memory)
    assert plan.funds == ["Aditya Birla Sun Life Credit Risk Fund - Regular Plan - Growth"]
    assert [call.tool for call in plan.tool_calls] == ["get_fund_data"]
    assert plan.tool_calls[0].arguments["windows"] == ["1Y", "3Y", "5Y"]
    assert plan.tool_calls[0].arguments["modules"] == ["snapshot", "vs_benchmark"]
    assert plan.requires_compose is True
    assert plan.asked_facts == []


def test_category_performance_keeps_long_windows_when_planner_named_1m():
    memory = {
        "frame": {
            "period": "1 month",
            "subjects": [{"name": "ABSL Banking Fund", "role": "primary"}],
        }
    }
    plan = ExecutionPlan(
        routed_by="planner",
        data_need="category_performance",
        funds=["ABSL Banking Fund"],
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1M"]},
                wave=1,
            ),
        ],
    )
    ensure_category_performance_plan("how is this category performing", plan, memory)
    assert plan.tool_calls[0].arguments["windows"] == ["1M", "1Y", "3Y", "5Y"]


def test_cross_category_compare_uses_two_rating_screens():
    q = "compare a conservative hybrid and aggressive hybrid fund"
    assert asks_cross_category_compare(q)
    cats = match_all_scheme_categories(q)
    assert "conservative hybrid" in cats
    assert "aggressive hybrid" in cats
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        fund_pick="compare_categories",
        scheme_categories=["conservative hybrid", "aggressive hybrid"],
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"top_n": 1, "focus_question": q},
                wave=1,
            ),
        ],
    )
    ensure_cross_category_compare_plan(q, plan)
    assert len(plan.tool_calls) == 2
    assert all(c.tool == "screen_funds_by_exposure" for c in plan.tool_calls)
    assert plan.tool_calls[0].arguments["rating_screen"] is True
    assert plan.tool_calls[0].arguments["focus_question"] == "conservative hybrid"
    assert plan.tool_calls[1].arguments["focus_question"] == "aggressive hybrid"


def test_what_it_holds_uses_risk_and_full_portfolio():
    memory = {
        "list_cursor": {
            "rows": [{"n": 1, "name": "ICICI Prudential Flexi Cap Fund - Growth"}],
        }
    }
    plan = ExecutionPlan(
        routed_by="planner",
        data_need="fund_holdings_breakdown",
        subject_ref="memory_primary",
        funds=["ICICI Prudential Flexi Cap Fund - Growth"],
        tool_calls=[
            ToolCall(tool="get_portfolio_data", arguments={"sections": ["holdings"], "top_n": 5}, wave=1),
        ],
    )
    assert asks_fund_holdings_followup("tell me what it holds")
    ensure_fund_holdings_followup_plan("tell me what it holds", plan, memory)
    tools = [c.tool for c in plan.tool_calls]
    assert tools == ["get_fund_data", "get_portfolio_data"]
    assert plan.tool_calls[0].arguments["modules"] == ["risk", "snapshot"]
    assert plan.tool_calls[1].arguments["sections"] == ["holdings", "sectors"]

    plan2 = ExecutionPlan(
        routed_by="planner",
        tool_calls=[ToolCall(tool="get_portfolio_data", arguments={"sections": ["holdings"]}, wave=1)],
    )
    validate_plan_tools("tell me what it holds", plan2, memory)
    assert any(c.tool == "get_fund_data" for c in plan2.tool_calls)
    assert "sectors" in plan2.tool_calls[-1].arguments["sections"]


def test_category_composition_uses_memory_fund_for_this_holds():
    memory = {
        "list_cursor": {
            "rows": [{"n": 1, "name": "ICICI Prudential Flexi Cap Fund - Growth"}],
        }
    }
    plan = ExecutionPlan(
        routed_by="planner",
        data_need="category_composition",
        scheme_category="flexi cap",
        subject_ref="memory_primary",
        tool_calls=[ToolCall(tool="get_portfolio_data", arguments={"sections": ["holdings"]}, wave=1)],
    )
    ensure_category_composition_plan("what this flexi cap holds", plan, memory)
    assert plan.funds == ["ICICI Prudential Flexi Cap Fund - Growth"]
    assert all(c.tool != "screen_funds_by_exposure" for c in plan.tool_calls)
    assert "ICICI Prudential Flexi Cap Fund" in (plan.presentation_notes or "")


def test_category_composition_uses_rated_fund_and_risk_data():
    assert asks_category_composition("what does flexi cap holds")
    plan = ExecutionPlan(
        routed_by="planner",
        data_need="category_composition",
        scheme_category="flexi cap",
        intent="explain_cause",
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"top_n": 1, "focus_question": "example"},
                wave=1,
            ),
        ],
    )
    ensure_category_composition_plan("what does flexi cap holds", plan)
    assert plan.intent == "lookup"
    tools = [c.tool for c in plan.tool_calls]
    assert tools[0] == "screen_funds_by_exposure"
    assert plan.tool_calls[0].arguments.get("rating_screen") is True
    assert "get_fund_data" in tools
    assert plan.tool_calls[1].arguments["modules"] == ["risk", "rating", "snapshot"]
    assert "flexi cap" in (plan.concept_brief or "").lower()
    assert "market cap" in (plan.presentation_notes or "").lower()


def test_alternate_aggressive_hybrid_excludes_memory_funds():
    q = "name any other aggressive hybrid fund"
    memory = {
        "frame": {
            "subjects": [
                {"name": "ICICI Prudential Aggressive Hybrid Fund - Growth", "role": "primary"},
                {"name": "Aditya Birla Sun Life Aggressive Hybrid Omni FOF - Growth", "role": "primary"},
                {"name": "Sundaram Conservative Hybrid Fund - Growth", "role": "primary"},
            ],
        },
        "entity_stack": [
            {"name": "ICICI Prudential Aggressive Hybrid Fund - Growth"},
            {"name": "Aditya Birla Sun Life Aggressive Hybrid Omni FOF - Growth"},
        ],
        "list_cursor": {
            "rows": [{"name": "ICICI Prudential Aggressive Hybrid Fund - Growth"}],
            "filters": {"focus_question": q, "rating_screen": True},
        },
    }
    plan = ExecutionPlan(
        routed_by="planner",
        goal="Name another aggressive hybrid fund not already in the chat",
        planner_reading="Another aggressive hybrid fund, not a repeat",
        fund_pick="alternate_in_category",
        scheme_category="aggressive hybrid",
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={
                    "top_n": 1,
                    "focus_question": q,
                    "rating_screen": True,
                    "pick_alternate": True,
                },
                wave=1,
            ),
        ],
    )
    ensure_alternate_category_fund_plan(q, plan, memory)
    assert len(plan.tool_calls) == 1
    args = plan.tool_calls[0].arguments
    assert args["focus_question"] == "aggressive hybrid"
    assert args.get("rating_fetch_n", 0) >= 10
    ex_names = args.get("exclude_names") or []
    assert any("ICICI" in n for n in ex_names)
    assert not any("Sundaram Conservative" in n for n in ex_names)
    assert "another" in (plan.presentation_notes or "").lower()


def test_rating_list_uses_list_cursor_not_memory_subjects():
    memory = {
        "list_cursor": {
            "rows": [
                {"name": "Bandhan Flexi Cap Fund", "isin": "INF123"},
                {"name": "HDFC Flexi Cap Fund", "isin": "INF456"},
            ]
        },
        "frame": {
            "subjects": [{"name": "ABSL Banking & PSU Debt", "id": "INF209K01LV0", "role": "primary"}],
        },
    }
    plan = ExecutionPlan(
        routed_by="planner",
        data_need="rating_for_screened_list",
        funds=["ABSL Banking & PSU Debt"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)],
    )
    ensure_rating_list_funds("show rupeestop rating of these funds", plan, memory)
    assert plan.funds == ["Bandhan Flexi Cap Fund", "HDFC Flexi Cap Fund"]
    assert plan.tool_calls[0].tool == "get_fund_data"
    assert plan.tool_calls[0].arguments["modules"] == ["rating"]
    assert plan.asked_facts == ["rating"]
    assert "RupeeStop score" in (plan.presentation_notes or "")
