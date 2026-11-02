from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
from news_rag.insight.plan_enforce import (
    apply_planner_post_hooks,
    repair_data_need_tools,
    resolve_planner_subject_refs,
)


def test_resolve_memory_primary_fund():
    memory = {
        "frame": {"subjects": [{"name": "HDFC Flexi Cap Fund - Growth", "role": "primary"}]},
    }
    plan = ExecutionPlan(routed_by="planner", subject_ref="memory_primary", tool_calls=[])
    resolve_planner_subject_refs(plan, memory)
    assert plan.funds == ["HDFC Flexi Cap Fund - Growth"]


def test_memory_stack_resolves_comparison_pair():
    memory = {
        "frame": {
            "subject_kind": "comparison",
            "subjects": [
                {"name": "ICICI Prudential Aggressive Hybrid Fund - Growth", "role": "primary"},
                {"name": "SBI Aggressive Hybrid Fund - Regular Plan - Growth", "role": "primary"},
            ],
        },
        "list_cursor": {
            "rows": [{"name": "SBI Aggressive Hybrid Fund - Regular Plan - Growth"}],
        },
    }
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        subject_ref="memory_stack",
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
    )
    resolve_planner_subject_refs(plan, memory, "compare both aggressive hybrid funds")
    assert len(plan.funds) == 2
    assert "ICICI" in plan.funds[0] or "ICICI" in plan.funds[1]


def test_category_performance_does_not_replace_compare_funds():
    memory = {
        "frame": {
            "subject_kind": "comparison",
            "subjects": [
                {"name": "ICICI Prudential Conservative Hybrid Fund - Regular Plan - Growth", "role": "primary"},
                {"name": "ICICI Prudential Aggressive Hybrid Fund - Growth", "role": "primary"},
            ],
        },
        "list_cursor": {
            "rows": [{"name": "SBI Aggressive Hybrid Fund - Regular Plan - Growth"}],
        },
    }
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        data_need="category_performance",
        subject_ref="memory_stack",
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
    )
    plan = apply_planner_post_hooks("compare both of the aggressive hybrid funds", plan, memory)
    assert plan.intent == "compare"
    assert any(c.tool == "compare_funds" for c in plan.tool_calls)
    assert not any(c.tool == "get_fund_data" for c in plan.tool_calls)
    assert len(plan.funds) == 2
    assert not any("Conservative" in n for n in plan.funds)


def test_aggressive_hybrid_compare_uses_memory_not_conservative_frame():
    memory = {
        "frame": {
            "subject_kind": "comparison",
            "subjects": [
                {"name": "ICICI Prudential Conservative Hybrid Fund - Regular Plan - Growth", "role": "primary"},
                {"name": "ICICI Prudential Aggressive Hybrid Fund - Growth", "role": "primary"},
            ],
        },
        "entity_stack": [
            {"name": "ICICI Prudential Aggressive Hybrid Fund - Growth", "facts": ["screen_funds_by_exposure"]},
            {"name": "ICICI Prudential Conservative Hybrid Fund - Regular Plan - Growth", "facts": ["screen_funds_by_exposure"]},
        ],
        "list_cursor": {
            "rows": [{"name": "SBI Aggressive Hybrid Fund - Regular Plan - Growth"}],
        },
    }
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
        funds=[
            "Edelweiss Aggressive Hybrid Fund - Plan B - Growth",
            "ICICI Prudential Aggressive Hybrid Fund - Growth",
        ],
    )
    q = "compare both the aggressive hybrid fund"
    plan = apply_planner_post_hooks(q, plan, memory)
    assert len(plan.funds) == 2
    assert any("SBI" in n for n in plan.funds)
    assert any("ICICI" in n and "Aggressive" in n for n in plan.funds)
    assert not any("Conservative" in n for n in plan.funds)
    assert not any("Edelweiss" in n for n in plan.funds)


def test_compare_followup_not_replaced_by_list_cursor_rating_hook():
    memory = {
        "frame": {
            "subject_kind": "comparison",
            "subjects": [
                {"name": "ICICI Prudential Aggressive Hybrid Fund - Growth", "role": "primary"},
                {"name": "SBI Aggressive Hybrid Fund - Regular Plan - Growth", "role": "primary"},
            ],
        },
        "list_cursor": {
            "rows": [{"name": "SBI Aggressive Hybrid Fund - Regular Plan - Growth"}],
        },
    }
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        data_need="rating_for_screened_list",
        subject_ref="memory_stack",
        tool_calls=[
            ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1),
            ToolCall(tool="get_fund_data", arguments={"modules": ["rating"]}, wave=1),
        ],
    )
    plan = apply_planner_post_hooks("why is sbi rated above icici", plan, memory)
    assert len(plan.funds) == 2
    assert any(c.tool == "compare_funds" for c in plan.tool_calls)


def test_compare_these_equity_funds_uses_latest_equity_category_pair():
    memory = {
        "frame": {
            "subject_kind": "single_fund",
            "subjects": [{"name": "UTI Nifty IT ETF", "role": "primary"}],
        },
        "entity_stack": [
            {"name": "UTI Nifty IT ETF", "facts": ["screen_funds_by_exposure"]},
            {"name": "SBI Aggressive Hybrid Fund - Regular Plan - Growth", "facts": ["screen_funds_by_exposure"]},
            {"name": "ICICI Prudential Aggressive Hybrid Fund - Growth", "facts": ["screen_funds_by_exposure"]},
            {"name": "Taurus Large Cap Fund - Regular Plan - Growth", "facts": ["screen_funds_by_exposure"]},
            {"name": "Bandhan Large Cap Fund - Regular Plan - Growth", "facts": ["screen_funds_by_exposure"]},
        ],
        "list_cursor": {
            "rows": [{"name": "ICICI Prudential Value Fund - Growth"}],
            "filters": {
                "pick_alternate": True,
                "focus_question": "equity",
            },
        },
        "category_funds_in_chat": [
            {
                "category": "aggressive hybrid",
                "fund_names": [
                    "SBI Aggressive Hybrid Fund - Regular Plan - Growth",
                    "ICICI Prudential Aggressive Hybrid Fund - Growth",
                ],
            },
            {
                "category": "large cap",
                "fund_names": [
                    "Taurus Large Cap Fund - Regular Plan - Growth",
                    "Bandhan Large Cap Fund - Regular Plan - Growth",
                ],
            },
        ],
    }
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        subject_ref="memory_stack",
        funds=[
            "ICICI Prudential Value Fund - Growth",
            "Taurus Large Cap Fund - Regular Plan - Growth",
            "Bandhan Large Cap Fund - Regular Plan - Growth",
        ],
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
    )
    out = apply_planner_post_hooks("compare these equity funds", plan, memory)
    assert len(out.funds) == 2
    assert "Taurus" in out.funds[0] or "Taurus" in out.funds[1]
    assert "Bandhan" in out.funds[0] or "Bandhan" in out.funds[1]
    assert not any("Value Fund" in n for n in out.funds)
    assert not any("Hybrid" in n for n in out.funds)


def test_repair_holdings_breakdown_adds_risk():
    plan = ExecutionPlan(
        routed_by="planner",
        data_need="fund_holdings_breakdown",
        funds=["Axis Fund"],
        tool_calls=[
            ToolCall(tool="get_portfolio_data", arguments={"sections": ["holdings"], "top_n": 5}, wave=1),
        ],
    )
    repair_data_need_tools(plan)
    tools = [c.tool for c in plan.tool_calls]
    assert tools[0] == "get_fund_data"
    assert "risk" in plan.tool_calls[0].arguments["modules"]
    assert "sectors" in plan.tool_calls[-1].arguments["sections"]


def test_planner_pillars_in_rating_fetches_full_rating():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        subject_ref="memory_primary",
        funds=["HDFC Large Cap Fund - Growth"],
        tool_calls=[],
    )
    memory = {
        "frame": {"subjects": [{"name": "HDFC Large Cap Fund - Growth", "role": "primary"}]},
    }
    out = apply_planner_post_hooks("what are the pillars in rating", plan, memory)
    assert any(c.tool == "get_fund_data" for c in out.tool_calls)
    call = next(c for c in out.tool_calls if c.tool == "get_fund_data")
    assert call.arguments.get("pillars") is True
