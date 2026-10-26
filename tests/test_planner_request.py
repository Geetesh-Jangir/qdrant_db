from news_rag.insight.plan import parse_plan


def test_planner_request_overrides_default_three_and_both_slices():
    """Planner said top 5 holdings, but tool args fell back to 3 and both slices."""
    plan = parse_plan(
        {
            "scope": {"kind": "in_scope"},
            "understanding": {
                "goal": "Top holdings",
                "intent": "lookup",
                "answer_mode": "DATA_ONLY",
            },
            "request": {
                "count": 5,
                "portfolio_slice": "holdings",
                "reading": "Top 5 holdings of Axis ELSS Tax Saver",
            },
            "entities": {"funds": ["Axis ELSS - Tax Saver Fund"]},
            "tool_calls": [
                {
                    "tool": "get_portfolio_data",
                    "arguments": {"sections": ["holdings", "sectors"], "top_n": 3},
                    "wave": 1,
                }
            ],
        }
    )
    args = plan.tool_calls[0].arguments
    assert plan.planner_count == 5
    assert plan.planner_portfolio_slice == "holdings"
    assert args["top_n"] == 5
    assert args["sections"] == ["holdings"]


def test_planner_request_sectors_only_keeps_count():
    plan = parse_plan(
        {
            "scope": {"kind": "in_scope"},
            "understanding": {"goal": "sectors", "intent": "lookup", "answer_mode": "DATA_ONLY"},
            "request": {"count": 5, "portfolio_slice": "sectors", "reading": "Top 5 sectors"},
            "tool_calls": [
                {"tool": "get_portfolio_data", "arguments": {"top_n": 3}, "wave": 1}
            ],
        }
    )
    assert plan.tool_calls[0].arguments["sections"] == ["sectors"]
    assert plan.tool_calls[0].arguments["top_n"] == 5


def test_missing_request_does_not_invent_a_count():
    plan = parse_plan(
        {
            "scope": {"kind": "in_scope"},
            "understanding": {"goal": "NAV", "intent": "lookup", "answer_mode": "DATA_ONLY"},
            "tool_calls": [{"tool": "get_fund_data", "arguments": {"modules": ["snapshot"]}, "wave": 1}],
        }
    )
    assert plan.planner_count == 0
    assert plan.planner_portfolio_slice == "none"
    assert plan.tool_names == ["get_fund_data"]
