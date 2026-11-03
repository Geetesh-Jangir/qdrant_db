from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.investor_subject import enforce_deictic_and_memory_primary_fund, reconcile_deictic_planner_fund
from news_rag.insight.memory.fund_context import deictic_fund_context_active, touch_fund_entity_ttl
from news_rag.insight.memory.state import empty_state, expire_stale_entities, push_fund


def test_deictic_inactive_after_no_fund_gist_strips_planner_fund():
    memory = {
        "turn_count": 2,
        "gists": [{"turn": 1, "gist": "no fund; no period; a general answer"}],
        "frame": {"last_fund_focus": "", "subjects": []},
        "entity_stack": [],
    }
    assert not deictic_fund_context_active(memory)
    plan = ExecutionPlan(
        funds=["DSP India T.I.G.E.R. Fund - Regular Plan - Growth"],
        subject_ref="memory_primary",
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["managers"]}, wave=1)],
    )
    reconcile_deictic_planner_fund(plan, memory, "who is the fund manager of this fund")
    enforce_deictic_and_memory_primary_fund(plan, memory, "who is the fund manager of this fund")
    assert plan.funds == []


def test_repeated_fund_mention_refreshes_entity_ttl():
    state = empty_state("conv-refresh")
    frame = state["frame"]
    state["turn_count"] = 8
    push_fund(state, {"name": "HDFC Large Cap Fund - Growth", "id": "INF1"}, period="1Y", facts=["snapshot"], turn=3)
    touch_fund_entity_ttl(
        state,
        frame,
        "HDFC Large Cap Fund - Growth",
        turn=8,
        period="1 month",
        facts=["managers"],
    )
    assert frame.get("last_fund_focus_turn") == 8
    stack = state.get("entity_stack") or []
    hdfc = next(row for row in stack if "HDFC" in row.get("name", ""))
    assert hdfc.get("turn") == 8
    expire_stale_entities(state, 10)
    names = [row.get("name") for row in state.get("entity_stack") or []]
    assert "HDFC Large Cap Fund - Growth" in names
