from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.fact_slots import slots_from_plan
from news_rag.insight.plan_catalog_bind import enforce_planner_catalog_plan
from news_rag.insight.plan_enforce import apply_planner_post_hooks


def _book():
    return {
        "frame": {"last_fund_focus": "Quant Small Cap Fund - Growth", "subjects": []},
        "holdings_in_chat": [
            {"name": "Quant Small Cap Fund - Growth", "isin": "INF966L01AA0", "category": "small cap"},
            {"name": "Invesco India Large & Mid Cap Fund - Regular Plan - Growth", "isin": "INF205K01247"},
        ],
    }


def test_deictic_one_month_uses_get_fund_data_not_investor_pnl():
    memory = _book()
    plan = ExecutionPlan(
        data_need="investor_pnl",
        subject_ref="memory_primary",
        window_days=30,
        window_label="last 1 month",
        tool_calls=[],
    )
    plan = apply_planner_post_hooks("whats the last one month changes in this fund", plan, memory)
    tools = [c.tool for c in plan.tool_calls]
    assert plan.funds == ["Quant Small Cap Fund - Growth"]
    assert "get_fund_data" in tools
    gfd = next(c for c in plan.tool_calls if c.tool == "get_fund_data")
    assert gfd.arguments.get("windows") == ["1M"]


def test_aum_slot_renders_from_snapshot():
    from news_rag.insight.fact_slots import render_asked_facts

    results = [
        {
            "ok": True,
            "tool": "get_fund_data",
            "fund": "HDFC Large Cap Fund - Growth",
            "data": {
                "snapshot": {
                    "fund_name": "HDFC Large Cap Fund - Growth",
                    "aum": 37293.95,
                    "aum_as_on_date": "2026-09-30",
                }
            },
        }
    ]
    table = render_asked_facts(["aum"], results)
    assert "37,293.95" in table
    assert "2026-09-30" in table


def test_snapshot_modules_without_returns_do_not_add_return_slots():
    plan = ExecutionPlan(
        asked_facts=["aum"],
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1Y", "3Y", "5Y"]},
            )
        ],
    )
    slots = slots_from_plan(plan)
    assert slots == ["aum"]
    assert not any(s.startswith("return:") for s in slots)
