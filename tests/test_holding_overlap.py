from news_rag.fund_search import build_holding_overlap
from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
from news_rag.insight.evidence_pack import build_evidence_pack, render_data_only_template


def _detail(name: str, holdings: dict) -> dict:
    return {
        "fund_name": name,
        "fund_short_name": name,
        "holdings": holdings,
        "nav": 10,
        "aum": 100,
        "category": "Large Cap",
        "expense_ratio": {"regular": 1.0},
        "exit_load_summary": "This fund has no exit load.",
    }


def test_overlap_uses_full_stock_list_and_skips_cash():
    left = _detail(
        "Fund A",
        {
            "Reliance Industries Limited": {"percentage": 8.2, "industry": "Oil"},
            "TREPS / Reverse Repo Investments": {"percentage": 4.0, "industry": "Cash"},
            "Small Name": {"percentage": 0.2, "industry": "Equity"},
        },
    )
    right = _detail(
        "Fund B",
        {
            "Reliance Industries Ltd": {"percentage": 5.5, "industry": "Oil"},
            "TREPS / Reverse Repo Investments": {"percentage": 3.0, "industry": "Cash"},
            "Other Co": {"percentage": 2.0, "industry": "Equity"},
        },
    )
    overlap = build_holding_overlap([left, right])
    assert overlap["overlap_count"] == 1
    assert overlap["rows"][0]["stock"].startswith("Reliance")
    assert overlap["rows"][0]["weights"]["Fund A"] == 8.2
    assert overlap["rows"][0]["weights"]["Fund B"] == 5.5


def test_no_overlap_message_and_overlap_table():
    plan = ExecutionPlan(intent="compare", answer_mode=AnswerMode.DATA_ONLY, funds=["Fund A", "Fund B"])
    empty = build_evidence_pack(
        plan,
        [{
            "tool": "compare_funds",
            "ok": True,
            "data": {"holding_overlap": {"fund_names": ["Fund A", "Fund B"], "overlap_count": 0, "rows": []}, "fund_briefs": []},
        }],
        [],
    )
    text = render_data_only_template(empty, plan)
    assert text is not None
    assert "no overlapping stock holding" in text

    present = build_evidence_pack(
        plan,
        [{
            "tool": "compare_funds",
            "ok": True,
            "data": {
                "holding_overlap": {
                    "fund_names": ["Fund A", "Fund B"],
                    "overlap_count": 1,
                    "rows": [{"stock": "Reliance Industries", "weights": {"Fund A": 8.2, "Fund B": 5.5}}],
                },
                "fund_briefs": [
                    {
                        "fund_name": "Fund A",
                        "nav": 56.98,
                        "aum": 1000,
                        "expense_ratio": 1.25,
                        "category": "Large Cap",
                        "top_sector": "Banks (30.08%)",
                        "exit_load_summary": "This fund has no exit load.",
                        "returns": {"1Y": 12.5, "3Y": 8.1},
                    },
                    {
                        "fund_name": "Fund B",
                        "nav": 100,
                        "aum": 2000,
                        "expense_ratio": 1.5,
                        "category": "Large Cap",
                        "top_sector": "Banks (22.00%)",
                        "exit_load_summary": "Exit load is 1% if you leave within 1 year.",
                        "returns": {"1Y": 9.0},
                    },
                ],
            },
        }],
        [],
    )
    table = render_data_only_template(present, plan)
    assert table is not None
    assert "Top sector" in table
    assert "Banks (30.08%)" in table
    assert "### Historical returns" in table
    assert "12.50%" in table
    assert "Reliance Industries" in table
    assert "8.20%" in table
    assert "5.50%" in table


def test_compare_table_includes_risk_for_both_funds():
    from news_rag.insight.evidence_pack import _render_fund_compare_markdown

    text = _render_fund_compare_markdown(
        {
            "holding_overlap": {"fund_names": ["Axis Midcap", "Quant Mid Cap"], "rows": []},
            "fund_briefs": [
                {"fund_name": "Axis Midcap", "nav": 115.06, "returns": {}},
                {"fund_name": "Quant Mid Cap", "nav": 206.47, "returns": {}},
            ],
        },
        [
            {
                "fund_name": "Axis Midcap",
                "risk": {
                    "fund_name": "Axis Midcap",
                    "riskometer": "Very High",
                    "label": "Good Choice",
                    "final_score": 64.47,
                    "assets": [{"label": "Equity", "percentage": 90.25}],
                    "market_cap": [{"label": "Mid Cap", "percentage": 65.38}],
                },
            },
            {
                "fund_name": "Quant Mid Cap",
                "risk": {
                    "fund_name": "Quant Mid Cap",
                    "riskometer": "Very High",
                    "label": "Average",
                    "final_score": 54.3,
                    "assets": [{"label": "Equity", "percentage": 86.76}],
                    "market_cap": [{"label": "Mid Cap", "percentage": 72.68}],
                },
            },
        ],
    )
    assert "### Risk" in text
    assert "Good Choice" in text
    assert "Average" in text
    assert "64.47" in text
    assert "54.30" in text
    assert "Very High" in text


def test_compare_and_risk_stay_on_the_first_wave():
    from news_rag.insight.multi_fact import ensure_compare_template

    plan = ExecutionPlan(
        routed_by="planner",
        tool_calls=[
            ToolCall(tool="screen_funds_by_exposure", arguments={"top_n": 2}, wave=1),
            ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=2),
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=2),
        ],
    )
    ensure_compare_template(plan, "compare any two mid cap funds and also do risk analysis of both")
    assert [call.wave for call in plan.tool_calls] == [1, 1, 1]
    assert "risk" in plan.tool_calls[2].arguments["modules"]
    assert "drawdown" in plan.tool_calls[2].arguments["modules"]
    assert plan.requires_compose is True


def test_extra_part_brief_names_both_funds():
    from news_rag.insight.evidence_pack import extra_part_brief

    text = extra_part_brief(
        {
            "fund:Axis": {
                "fund_name": "Axis Midcap",
                "risk": {"lines": "SEBI riskometer: Very High. RupeeStop assessment: 64.47, Good Choice."},
            },
            "fund:Quant": {
                "fund_name": "Quant Mid Cap",
                "risk": {"lines": "SEBI riskometer: Very High. RupeeStop assessment: 54.30, Average."},
            },
        }
    )
    assert "Axis Midcap" in text
    assert "Quant Mid Cap" in text
    assert "Good Choice" in text
    assert "Average" in text
