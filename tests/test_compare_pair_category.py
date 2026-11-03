from news_rag.fund_rating_screen import pick_compare_pair_in_category
from news_rag.insight.capabilities.catalog import validate_capability_args
from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.plan_enforce import apply_planner_post_hooks


def test_validate_capability_args_keeps_compare_pair():
    args = validate_capability_args(
        "screen_funds_by_exposure",
        {
            "rating_screen": True,
            "focus_question": "large cap",
            "top_n": 2,
            "compare_pair": True,
            "rating_fetch_n": 20,
        },
    )
    assert args.get("compare_pair") is True
    assert args.get("rating_fetch_n") == 20


def test_random_equity_compare_uses_same_category_screen(monkeypatch):
    monkeypatch.setattr(
        "news_rag.insight.category_plan.pick_random_scheme_category_for_compare",
        lambda _q: ("mid cap", "equity"),
    )
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        fund_pick="random_in_category",
        funds=[
            "Aditya Birla Sun Life CRISIL-IBX Financial Services 3 to 6 Months Debt Index Fund - Regular Plan - Growth",
        ],
        tool_calls=[
            ToolCall(tool="screen_funds_by_exposure", arguments={"rating_screen": True, "top_n": 2}, wave=1),
            ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1),
        ],
    )
    q = "compare any random two equity funds that needs to be in category"
    out = apply_planner_post_hooks(q, plan, None)
    assert out.funds == []
    assert len(out.tool_calls) == 1
    assert out.tool_calls[0].tool == "screen_funds_by_exposure"
    args = out.tool_calls[0].arguments
    assert args.get("compare_pair") is True
    assert args.get("focus_question") == "mid cap"
    assert out.scheme_category == "mid cap"


def test_named_hdfc_invesco_compare_keeps_compare_funds():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        funds=[],
        tool_calls=[
            ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1),
        ],
    )
    q = "compare hdfc large cap fund with invesco india large cap fund"
    out = apply_planner_post_hooks(q, plan, None)
    assert out.intent == "compare"
    assert len(out.tool_calls) == 1
    assert out.tool_calls[0].tool == "compare_funds"
    assert len(out.funds) >= 2
    joined = " ".join(out.funds).lower()
    assert "hdfc" in joined and "invesco" in joined


def test_unnamed_large_cap_compare_plan():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        funds=["Edelweiss Large Cap Fund"],
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"top_n": 2, "focus_question": "large cap", "rating_screen": True},
                wave=1,
            ),
        ],
    )
    out = apply_planner_post_hooks("compare two large cap funds", plan, None)
    assert out.intent == "compare"
    assert out.funds == []
    assert len(out.tool_calls) == 1
    args = out.tool_calls[0].arguments
    assert args.get("compare_pair") is True
    assert args.get("focus_question") == "large cap"


def test_pick_compare_pair_walks_tiers():
    def fake_fetch(_fund_type: str, _category: str) -> dict:
        return {
            "data": {
                "ratings": [
                    {
                        "isin": "INFAAA11111",
                        "fundName": "Alpha Large Cap",
                        "finalScore": 90,
                        "label": "Best in category",
                        "schemeCategory": "large cap",
                    },
                    {
                        "isin": "INFBBB22222",
                        "fundName": "Beta Large Cap",
                        "finalScore": 75,
                        "label": "Recommended",
                        "schemeCategory": "large cap",
                    },
                ],
            },
        }

    result = pick_compare_pair_in_category(
        fund_type="equity",
        category="large cap",
        fetch=fake_fetch,
    )
    assert result.get("success") is True
    labels = [r.get("rs_label") for r in result.get("rankings") or []]
    assert len(labels) == 2
    assert labels[0] == "Best in category"
    assert labels[1] == "Recommended"
