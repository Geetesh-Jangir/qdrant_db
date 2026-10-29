from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
from news_rag.insight.evidence_pack import build_evidence_pack, render_data_only_template
from news_rag.insight.multi_fact import asks_one_figure, ensure_multi_fact_tools, requested_fund_facts


def test_named_facts_cover_nav_manager_sectors_returns_and_exit_load():
    q = "tell me nav, fund_manager, top 5 sectors, historical performance and exit load of hdfc large cap fund?"
    facts = requested_fund_facts(q)
    assert facts >= {"nav", "managers", "sectors", "returns", "exit_load"}


def test_table_source_lists_the_screen_rows():
    from news_rag.insight.evidence_pack import table_source

    text = table_source(
        {
            "screen": {
                "rankings": [
                    {"fund_name": "Axis Liquid", "return_1m_pct": 5.32, "return_1y_pct": 6.42},
                    {"fund_name": "Tata Liquid", "return_1m_pct": 5.26, "return_1y_pct": 6.32},
                ]
            }
        }
    )
    assert "Axis Liquid" in text
    assert "return_1m_pct=5.32" in text
    assert "Tata Liquid" in text


def test_table_source_keeps_pillar_marks_and_the_fetched_return():
    from news_rag.insight.evidence_pack import table_source

    text = table_source(
        {
            "screen": {
                "rankings": [
                    {
                        "fund_name": "Bandhan Large Cap Fund",
                        "final_score": 79.85,
                        "rs_label": "Best in category",
                        "pillars": {"performance": {"label": "Performance", "score": 37.6, "max": 40}},
                    }
                ]
            },
            "fund:bandhan": {
                "snapshot": {
                    "fund_name": "Bandhan Large Cap Fund",
                    "nav": 74.21,
                    "returns": {"1Y": -7.62},
                    "expense_ratio": {"regular": 2.2},
                },
                "rs_rating": {"label": "Best in category", "final_score": 79.85},
            },
        }
    )
    assert "pillars=Performance 37.6/40" in text
    assert "return_1Y=-7.62" in text
    assert "expense_ratio=2.2" in text


def test_fund_insights_category_average_reaches_the_composer_row():
    from news_rag.insight.evidence_pack import table_source

    text = table_source({
        "fund:hdfc": {
            "fund_name": "HDFC Large Cap Fund - Growth",
            "fund_insights": {
                "benchmark_name": "nifty 100 tri",
                "category_average_returns_pct": {"1Y": -7.9, "3Y": 9.34, "5Y": 7.27},
                "comparison_periods": {
                    "1Y": {
                        "fund_return": -9.79,
                        "benchmark_return": -5.18,
                        "category_average_return": -7.9,
                        "vs_benchmark": -4.61,
                        "vs_category": -1.89,
                    },
                    "3Y": {"fund_return": 7.58, "category_average_return": 9.34, "vs_category": -1.76},
                },
            },
            "rs_rating": {"label": "Good Choice", "final_score": 64.55},
        }
    })
    assert "1Y_fund=-9.79" in text
    assert "1Y_category_avg=-7.9" in text
    assert "1Y_vs_category=-1.89" in text
    assert "1Y_benchmark=-5.18" in text
    assert "3Y_category_avg=9.34" in text
    assert "5Y_category_avg=7.27" in text


def test_a_rating_row_is_filled_with_returns_riskometer_and_category_average(monkeypatch):
    from news_rag.insight.evidence_pack import table_source

    class Index:
        def get_fund_detail(self, isin):
            assert isin == "INF194K01516"
            return {
                "returns": {"1y": -7.62, "3y": 11.33, "5y": 7.78},
                "category_average_returns": {"1Y": -8.0, "3Y": 10.0, "5Y": 8.1},
                "sebi_riskometer": "Very High",
            }

    monkeypatch.setattr("news_rag.fund_search.get_fund_index", lambda: Index())
    monkeypatch.setattr(
        "news_rag.fund_rupeestop_metrics.fetch_vs_benchmark",
        lambda isin: {"periods": {"1Y": {"benchmark_return": -6.1, "vs_benchmark": -1.52}}},
    )
    text = table_source({
        "screen": {
            "rankings": [{
                "isin": "INF194K01516",
                "fund_name": "Bandhan Large Cap Fund",
                "final_score": 79.85,
                "rs_label": "Best in category",
            }]
        }
    })
    assert "return_1y_pct=-7.62" in text
    assert "return_3y_pct=11.33" in text
    assert "return_5y_pct=7.78" in text
    assert "riskometer=Very High" in text
    assert "category_avg_1y_pct=-8.0" in text
    assert "benchmark_1y_pct=-6.1" in text
    assert asks_one_figure("what is the aum of hdfc large cap")
    assert asks_one_figure("what is the nav of axis bluechip")
    assert asks_one_figure("what is the 1 month return of this fund")
    assert asks_one_figure("what is the benchmark of parag parikh flexi cap")
    assert not asks_one_figure("what is the nav and aum of hdfc large cap")
    assert not asks_one_figure("show me 5 funds and their one month returns")
    assert not asks_one_figure(
        "what is the expense ratio of the hdfc large cap fund and what does expense ration means?"
    )


def test_manager_name_question_fetches_managers_not_the_snapshot():
    q = "what is the name of the fund manager of hdfc large cap"
    assert "managers" in requested_fund_facts(q)
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)],
    )
    ensure_multi_fact_tools(q, plan)
    assert plan.tool_calls[0].arguments["modules"] == ["managers"]


def test_multi_fact_plan_adds_snapshot_managers_and_sectors():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["managers"]}, wave=1)],
    )
    q = "tell me the aum and fund manager details about the hdfc large cap fund?"
    ensure_multi_fact_tools(q, plan)
    modules = plan.tool_calls[0].arguments["modules"]
    assert "snapshot" in modules
    assert "managers" in modules


def test_multi_fact_answer_keeps_aum_and_managers():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot", "managers"]}, wave=1),
        ],
    )
    pack = build_evidence_pack(
        plan,
        [
            {
                "tool": "get_fund_data",
                "ok": True,
                "fund": "HDFC Large Cap Fund",
                "data": {
                    "snapshot": {
                        "fund_name": "HDFC Large Cap Fund",
                        "nav": 100.5,
                        "aum": 37293.95,
                        "aum_as_on_date": "2026-09-30",
                        "exit_load_summary": "This fund has no exit load.",
                    },
                    "managers": {
                        "fund_name": "HDFC Large Cap Fund",
                        "current": [{"name": "Rahul Baijal", "designation": "Fund Manager"}],
                        "past": [],
                    },
                },
            }
        ],
        [],
    )
    text = render_data_only_template(pack, plan)
    assert text is not None
    assert "37,293.95" in text
    assert "Rahul Baijal" in text
    assert "no exit load" in text


def _fund_plan(calls, asked=None):
    return ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        asked_facts=asked or [],
        tool_calls=calls,
    )


def test_manager_question_keeps_one_manager_call():
    q = "tell me about the fund manager of the hdfc large cap fund"
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        requires_compose=True,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["managers"]}, wave=1),
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
            ToolCall(tool="search_financial_news", arguments={}, wave=1),
            ToolCall(tool="get_market_snapshot", arguments={}, wave=1),
        ],
    )
    ensure_multi_fact_tools(q, plan)
    assert len(plan.tool_calls) == 1
    assert plan.tool_calls[0].tool == "get_fund_data"
    assert plan.tool_calls[0].arguments["modules"] == ["managers"]
    assert plan.requires_compose is False
    assert plan.answer_mode == AnswerMode.DATA_ONLY

    pack = build_evidence_pack(
        plan,
        [
            {
                "tool": "get_fund_data",
                "ok": True,
                "fund": "HDFC Large Cap Fund",
                "data": {
                    "snapshot": {
                        "fund_name": "HDFC Large Cap Fund",
                        "nav": 1285.86,
                        "aum": 37293.95,
                        "expense_ratio": {"regular": 1.58},
                        "exit_load_summary": "This fund has no exit load.",
                    },
                    "managers": {
                        "fund_name": "HDFC Large Cap Fund",
                        "current": [{"name": "Rahul Baijal", "designation": "Fund Manager"}],
                        "past": [],
                    },
                },
            }
        ],
        [],
    )
    text = render_data_only_template(pack, plan)
    assert "Rahul Baijal" in text
    assert "Current NAV" not in text
    assert "AUM" not in text


def test_expense_ratio_renders_only_the_expense_ratio():
    q = "what is the expense ratio of hdfc large cap"
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        requires_compose=True,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
            ToolCall(tool="search_financial_news", arguments={}, wave=1),
        ],
    )
    ensure_multi_fact_tools(q, plan)
    assert [call.tool for call in plan.tool_calls] == ["get_fund_data"]
    assert plan.tool_calls[0].arguments["modules"] == ["snapshot"]
    pack = build_evidence_pack(
        plan,
        [
            {
                "tool": "get_fund_data",
                "ok": True,
                "fund": "HDFC Large Cap Fund",
                "data": {
                    "snapshot": {
                        "fund_name": "HDFC Large Cap Fund",
                        "nav": 1285.86,
                        "category": "Large Cap",
                        "benchmark": "Nifty 100",
                        "expense_ratio": {"regular": 1.58, "as_on_date": "2026-09-30"},
                        "exit_load_summary": "This fund has no exit load.",
                        "aum": 37293.95,
                        "returns": {"1M": 1.2},
                    }
                },
            }
        ],
        [],
    )
    text = render_data_only_template(pack, plan)
    assert "1.58%" in text
    assert "Current NAV" not in text
    assert "Exit load" not in text
    assert "AUM" not in text
    assert "Historical Returns" not in text


def test_aum_and_exit_load_render_only_those_lines():
    q = "what is the aum and exit load of hdfc large cap"
    plan = ExecutionPlan(
        intent="lookup",
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)],
    )
    ensure_multi_fact_tools(q, plan)
    assert plan.tool_calls[0].arguments["modules"] == ["snapshot"]
    assert set(plan.asked_facts) >= {"aum", "exit_load"}
    assert plan.requires_compose is True
    plan.requires_compose = False
    pack = build_evidence_pack(
        plan,
        [
            {
                "tool": "get_fund_data",
                "ok": True,
                "fund": "HDFC Large Cap Fund",
                "data": {
                    "snapshot": {
                        "fund_name": "HDFC Large Cap Fund",
                        "nav": 1285.86,
                        "expense_ratio": {"regular": 1.58},
                        "exit_load_summary": "This fund has no exit load.",
                        "aum": 37293.95,
                        "returns": {"1Y": 12.0},
                    }
                },
            }
        ],
        [],
    )
    text = render_data_only_template(pack, plan)
    assert "37,293.95" in text
    assert "no exit load" in text
    assert "Current NAV" not in text
    assert "Expense ratio" not in text
    assert "Historical Returns" not in text


def test_plain_fund_overview_is_not_reduced_to_one_fact():
    q = "tell me about HDFC Large Cap"
    plan = ExecutionPlan(
        intent="lookup",
        requires_compose=True,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot", "managers"]}, wave=1),
            ToolCall(tool="search_financial_news", arguments={}, wave=1),
            ToolCall(tool="get_market_snapshot", arguments={}, wave=1),
        ],
    )
    ensure_multi_fact_tools(q, plan)
    assert [call.tool for call in plan.tool_calls] == [
        "get_fund_data",
        "search_financial_news",
        "get_market_snapshot",
    ]
    assert plan.asked_facts == []
    assert plan.requires_compose is True


def test_two_fund_calls_for_the_same_fund_are_merged():
    plan = _fund_plan(
        [ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot", "managers"]}, wave=1)]
    )
    pack = build_evidence_pack(
        plan,
        [
            {
                "tool": "get_fund_data",
                "ok": True,
                "fund": "HDFC Large Cap Fund",
                "data": {
                    "managers": {
                        "fund_name": "HDFC Large Cap Fund",
                        "current": [{"name": "Rahul Baijal"}],
                    }
                },
            },
            {
                "tool": "get_fund_data",
                "ok": True,
                "fund": "HDFC Large Cap Fund",
                "data": {
                    "snapshot": {
                        "fund_name": "HDFC Large Cap Fund",
                        "nav": 100.5,
                        "aum": 37293.95,
                    }
                },
            },
        ],
        [],
    )
    stored = pack.data_pack["fund:HDFC Large Cap Fund"]
    assert stored["managers"]["current"][0]["name"] == "Rahul Baijal"
    assert stored["snapshot"]["aum"] == 37293.95
