from news_rag.fund_rating_screen import (
    asks_balanced_long_horizon_fund_menu,
    asks_ideal_portfolio_shape,
    balanced_portfolio_examples_spec,
    ensure_rating_screen,
)
from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.plan_enforce import apply_planner_post_hooks, maybe_install_balanced_portfolio_screen


def test_long_horizon_fund_names_uses_seven_sleeves():
    q = "i am thing for more than 10 years can you tell me some fund names for it"
    assert asks_balanced_long_horizon_fund_menu(q)
    spec = balanced_portfolio_examples_spec(q)
    assert spec is not None
    assert len(spec.walk_category_pairs) == 7
    assert spec.spread_categories
    cats = {cat for _ft, cat in spec.walk_category_pairs}
    assert "large cap" in cats
    assert "corporate bond" in cats
    assert "gold etf" in cats


def test_ensure_rating_screen_does_not_rewrite_from_question_text():
    q = "i am thing for more than 10 years can you tell me some fund names for it"
    plan = ExecutionPlan(
        routed_by="planner",
        intent="rank",
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={
                    "focus_question": "large cap",
                    "rating_screen": True,
                    "top_n": 5,
                    "return_window": "5Y",
                },
                wave=1,
            )
        ],
    )
    ensure_rating_screen(q, plan)
    assert plan.tool_calls[0].arguments["top_n"] == 5
    assert plan.tool_calls[0].arguments["focus_question"] == "large cap"


def test_misclassified_allocation_with_investor_tool_never_clears_tools():
    plan = ExecutionPlan(
        routed_by="planner",
        data_need="portfolio_allocation",
        horizon_years=None,
        tool_calls=[
            ToolCall(
                tool="get_investor_portfolio",
                arguments={"modules": ["allocation"]},
                wave=1,
            )
        ],
    )
    assert not maybe_install_balanced_portfolio_screen("Show my portfolio allocation", plan, None)
    assert any(c.tool == "get_investor_portfolio" for c in plan.tool_calls)
    assert plan.data_need == "investor_summary"
    assert (plan.direct_reply or "") == ""


def test_portfolio_allocation_without_screen_signals_does_not_clarify_horizon():
    plan = ExecutionPlan(
        routed_by="planner",
        data_need="portfolio_allocation",
        horizon_years=None,
        tool_calls=[],
    )
    assert not maybe_install_balanced_portfolio_screen("latest market news", plan, None)
    assert plan.tool_calls == []
    assert (plan.direct_reply or "") == ""


def test_ideal_portfolio_without_planner_allocation_does_not_install_a_screen():
    q = "for a ideal portfolio show should it look like and what categories and assets it should hold"
    plan = ExecutionPlan(
        routed_by="planner",
        data_need="category_composition",
        tool_calls=[],
    )
    assert not maybe_install_balanced_portfolio_screen(q, plan, None)
    out = apply_planner_post_hooks(q, plan, None)
    assert not any(c.tool == "screen_funds_by_exposure" for c in out.tool_calls)
    assert not any(c.tool == "get_fund_data" for c in out.tool_calls)
