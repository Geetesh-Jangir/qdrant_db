from unittest.mock import patch

from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.plan_enforce import apply_planner_post_hooks
from news_rag.insight.plan_intent import reconcile_planner_intent


def test_compare_categories_not_replaced_by_composition():
    q = "compare a conservative hybrid and aggressive hybrid fund"
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        fund_pick="compare_categories",
        data_need="category_composition",
        tool_calls=[],
    )
    reconcile_planner_intent(plan, q)
    assert plan.data_need == "none"
    assert len(plan.scheme_categories) >= 2

    plan2 = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        fund_pick="compare_categories",
        data_need="category_composition",
        tool_calls=[],
    )
    out = apply_planner_post_hooks(q, plan2, None)
    tools = [c.tool for c in out.tool_calls]
    assert tools.count("screen_funds_by_exposure") == 2
    assert "get_portfolio_data" not in tools


def test_compare_above_funds_keeps_planner_chat_pair_not_last_focus():
    memory = {
        "frame": {
            "subject_kind": "single_fund",
            "last_fund_focus": "Magnum Hybrid Long Short Fund - Regular Plan - Growth",
            "subjects": [{"name": "Magnum Hybrid Long Short Fund - Regular Plan - Growth", "role": "primary"}],
        },
        "chat_turns": [
            {"user": "what is Quantum ELSS Tax Saver", "assistant": "Quantum ELSS Tax Saver Fund - Regular Plan - Growth"},
            {"user": "what is Samco Special Opportunities Fund", "assistant": "Samco Special Opportunities Fund - Regular Plan - Growth"},
            {"user": "compare these two funds", "assistant": "Could you tell me a little more?"},
            {"user": "what is Magnum Hybrid Long Short Fund", "assistant": "Magnum Hybrid Long Short Fund - Regular Plan - Growth"},
        ],
    }
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        subject_ref="memory_stack",
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
        funds=[
            "Quantum ELSS Tax Saver Fund - Regular Plan - Growth",
            "Samco Special Opportunities Fund - Regular Plan - Growth",
        ],
    )
    out = apply_planner_post_hooks("compare the above funds", plan, memory)
    joined = " ".join(out.funds)
    assert "Quantum" in joined
    assert "Samco" in joined
    assert not any("Magnum" in n for n in out.funds)
    assert not any("Wealth Company" in n for n in out.funds)
    assert any(c.tool == "compare_funds" for c in out.tool_calls)


def test_compare_funds_survives_nav_api_404():
    from news_rag.tools import run_compare_funds

    details = [
        {"isin": "INF200K30015", "fund_name": "Magnum Hybrid Long Short Fund", "nav": 10.42, "returns": {"1M": 1.0}},
        {"isin": "INF2F0001305", "fund_name": "Peer Fund", "nav": 11.0, "returns": {"1M": 2.0}},
    ]

    def _boom(isin):
        raise RuntimeError(f"RupeeStop NAV API returned status 404 for ISIN {isin}")

    with patch("news_rag.tools.get_fund_nav_history", side_effect=_boom):
        out = run_compare_funds(details, compare_on="nav", return_window="1M")
    assert out.get("ok") is True
    assert len((out.get("data") or {}).get("funds") or []) == 2
