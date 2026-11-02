from news_rag.insight.compare_evidence import resolve_compare_fund_pair
from news_rag.insight.contracts import ExecutionPlan, ToolCall


def test_resolve_pair_anchor_plus_screen_pick():
    plan = ExecutionPlan(
        funds=["Kotak Contra Fund - Regular Plan - Growth"],
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={
                    "pick_rating_better": True,
                    "exclude_names": ["Kotak Contra Fund - Regular Plan - Growth"],
                },
                wave=1,
            ),
        ],
    )
    wave1 = [
        {
            "tool": "screen_funds_by_exposure",
            "ok": True,
            "data": {
                "rankings": [{"fund_name": "DSP Value Fund - Regular Plan - Growth"}],
            },
        },
    ]
    pair = resolve_compare_fund_pair(plan, wave1)
    assert pair == [
        "Kotak Contra Fund - Regular Plan - Growth",
        "DSP Value Fund - Regular Plan - Growth",
    ]


def test_resolve_pair_two_screen_rankings():
    plan = ExecutionPlan(
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"compare_pair": True},
                wave=1,
            ),
        ],
    )
    wave1 = [
        {
            "ok": True,
            "tool": "screen_funds_by_exposure",
            "data": {
                "rankings": [
                    {"fund_name": "Fund A"},
                    {"fund_name": "Fund B"},
                ],
            },
        },
    ]
    assert resolve_compare_fund_pair(plan, wave1) == ["Fund A", "Fund B"]
