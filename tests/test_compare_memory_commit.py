"""Compare turns must store the planned pair in memory, not stale cache extras."""

from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.memory.store import reset_memory
from news_rag.insight.memory.update import commit_turn


def test_compare_commit_uses_plan_funds_when_cache_payload_wrong():
    reset_memory("conv-compare-commit")
    plan = ExecutionPlan(
        intent="compare",
        funds=[
            "ICICI Prudential Aggressive Hybrid Fund - Growth",
            "SBI Aggressive Hybrid Fund - Regular Plan - Growth",
        ],
        window_label="1 month",
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
    )
    stale_compare = {
        "ok": True,
        "tool": "compare_funds",
        "fund": "",
        "data": {
            "funds": [
                {"fund_name": "ICICI Prudential Conservative Hybrid Fund - Regular Plan - Growth"},
                {"fund_name": "ICICI Prudential Aggressive Hybrid Fund - Growth"},
            ],
            "holding_overlap": {
                "fund_names": [
                    "ICICI Prudential Conservative Hybrid Fund - Regular Plan - Growth",
                    "ICICI Prudential Aggressive Hybrid Fund - Growth",
                ],
            },
            "fund_briefs": [
                {"fund_name": "ICICI Prudential Conservative Hybrid Fund - Regular Plan - Growth"},
                {"fund_name": "ICICI Prudential Aggressive Hybrid Fund - Growth"},
                {"fund_name": "Edelweiss Aggressive Hybrid Fund - Plan B - Growth"},
            ],
        },
    }
    state = commit_turn("conv-compare-commit", plan, [stale_compare])
    names = [row.get("name") or "" for row in (state.get("frame") or {}).get("subjects") or []]
    assert len(names) == 2
    assert any("SBI" in n for n in names)
    assert any("Aggressive" in n and "ICICI" in n for n in names)
    assert not any("Conservative" in n for n in names)
    assert not any("Edelweiss" in n for n in names)
