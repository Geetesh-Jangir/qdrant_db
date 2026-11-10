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
    assert [call.wave for call in plan.tool_calls] == [1, 2, 2]
    assert plan.tool_calls[2].arguments["modules"] == ["snapshot"]


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


def test_a_comparison_keeps_one_three_and_five_years_plus_benchmark_and_rating():
    from news_rag.insight.evidence_pack import table_source
    from news_rag.insight.tool_runners import _compare_return_windows, _enrich_compare_brief

    assert _compare_return_windows("compare them") == ["1Y", "3Y", "5Y"]
    assert _compare_return_windows("compare their 1 month returns") == ["1M"]

    brief = _enrich_compare_brief(
        {
            "fund_name": "Bandhan Large Cap",
            "isin": "",
            "category": "large cap",
            "sebi_riskometer": "Very High",
            "returns": {"1w": -0.17, "1m": -0.96, "1y": -7.62, "3y": 11.33, "5y": 7.78, "ytd": -9.46},
            "category_average_returns": {"1Y": -8.0, "3Y": 10.0, "5Y": 8.0},
        },
        ["1Y", "3Y", "5Y"],
    )
    assert set(brief["returns"]) == {"1Y", "3Y", "5Y"}
    assert brief["returns"]["1Y"] == -7.62
    assert brief["riskometer"] == "Very High"

    text = table_source({
        "compare": {
            "fund_briefs": [
                {
                    "fund_name": "Bandhan Large Cap",
                    "category": "large cap",
                    "benchmark": "BSE 100 TRI",
                    "riskometer": "Very High",
                    "rs_label": "Best in category",
                    "rs_score": 79.85,
                    "pillars": {"risk": {"label": "Risk", "score": 15.5, "max": 25}},
                    "return_windows": ["1Y", "3Y", "5Y"],
                    "returns": {"1W": -0.17, "1Y": -7.62, "2Y": -0.31, "3Y": 11.33, "5Y": 7.78},
                    "comparison": {
                        "1Y": {
                            "fund_return": -7.62,
                            "benchmark_return": -6.1,
                            "vs_benchmark": -1.52,
                            "category_average_return": -8.0,
                            "vs_category": 0.38,
                        },
                    },
                },
                {
                    "fund_name": "HDFC Large Cap",
                    "category": "large cap",
                    "return_windows": ["1Y", "3Y", "5Y"],
                    "returns": {"1M": -1.94, "1Y": -9.79},
                    "comparison": {"1Y": {"fund_return": -9.79, "benchmark_return": -6.1, "category_average_return": -8.0}},
                },
            ]
        }
    })
    assert "1W=" not in text
    assert "1M=" not in text
    assert "2Y=" not in text
    assert "1Y fund=-7.62" in text
    assert "benchmark=-6.1" in text
    assert "category_avg=-8.0" in text
    assert "riskometer=Very High" in text
    assert "pillars=Risk 15.5/25" in text


def test_unnamed_catalog_periods_are_measured_together(monkeypatch) -> None:
    import threading
    import time

    from news_rag.insight.tool_runners import _compare_return_windows, _measure_briefs

    assert _compare_return_windows("compare their 8 month returns") == ["8M"]
    assert _compare_return_windows("two year return of the top 2") == ["2Y"]
    state = {"open": 0, "max": 0}
    lock = threading.Lock()

    def _calc(isin, windows, inception_date=""):
        del inception_date
        with lock:
            state["open"] += 1
            state["max"] = max(state["max"], state["open"])
        time.sleep(0.05)
        with lock:
            state["open"] -= 1
        return {windows[0]: 4.2}, []

    monkeypatch.setattr("news_rag.insight.return_windows.returns_for_windows", _calc)
    monkeypatch.setattr("news_rag.fund_rupeestop_metrics.fetch_vs_benchmark", lambda isin: None)
    monkeypatch.setattr("news_rag.fund_risk.headline_rating", lambda detail: None)
    briefs = _measure_briefs(
        [
            {"fund_name": "A", "isin": "INF000000001", "returns": {}},
            {"fund_name": "B", "isin": "INF000000002", "returns": {}},
        ],
        ["8M"],
    )
    assert state["max"] == 2
    assert [row["returns"]["8M"] for row in briefs] == [4.2, 4.2]
