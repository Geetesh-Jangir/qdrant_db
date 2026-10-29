from news_rag.fund_drawdown import (
    asks_category_drawdown,
    average_peer_drawdown,
    collapse_episodes,
    ensure_drawdown_tools,
    investment_amount,
    is_drawdown_definition,
    normalize_drawdown_payload,
    periods_for_question,
    render_drawdown_body,
    rupee_loss,
)
from news_rag.insight.contracts import AnswerMode, EvidencePack, ExecutionPlan, ToolCall
from news_rag.insight.evidence_pack import render_data_only_template
from news_rag.insight.multi_fact import ensure_multi_fact_tools, ensure_screen_facts


def _plan(question_tools, funds=None):
    return ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        requires_compose=True,
        funds=funds or ["HDFC Large Cap Fund"],
        tool_calls=question_tools,
    )


def _open_episode():
    return normalize_drawdown_payload(
        {
            "data": {
                "fundName": "Nippon India Power & Infra Fund",
                "period": "1y",
                "maxDrawdown": -13.02,
                "peakDate": "2026-06-22",
                "peakDateLabel": "22nd jun 2026",
                "peakNav": 392.05,
                "troughDate": "2026-10-23",
                "troughDateLabel": "23rd oct 2026",
                "troughNav": 340.99,
                "recovery": {"recovered": False, "currentPctBelowPeak": 10.97, "daysUnderwater": 127},
                "fallVsRecoverySpeed": {"fallDays": 123},
            }
        }
    )


def _recovered_episode(period):
    return normalize_drawdown_payload(
        {
            "data": {
                "period": period,
                "maxDrawdown": -25.83,
                "peakDate": "2024-09-27",
                "peakDateLabel": "27th sep 2024",
                "peakNav": 383.04,
                "troughDate": "2025-02-28",
                "troughDateLabel": "28th feb 2025",
                "troughNav": 284.09,
                "recovery": {
                    "recovered": True,
                    "recoveryDateLabel": "4th may 2026",
                    "recoveryTimeDays": 430,
                },
                "fallVsRecoverySpeed": {"fallDays": 154},
            }
        }
    )


def test_open_episode_states_the_current_gap():
    text = render_drawdown_body({"fund_name": "Nippon", "episodes": [_open_episode()]})
    assert "13.02%" in text
    assert "has not recovered" in text
    assert "10.97%" in text
    assert "127 days" in text


def test_recovered_episode_states_the_repair():
    text = render_drawdown_body({"episodes": [_recovered_episode("3y")]})
    assert "25.83%" in text
    assert "Recovered on 4th may 2026" in text
    assert "154 days" in text
    assert "430 days" in text
    assert "has not recovered" not in text


def test_same_peak_and_trough_render_once():
    episodes = [_recovered_episode("3y"), _recovered_episode("5y")]
    assert len(collapse_episodes(episodes)) == 1
    text = render_drawdown_body({"episodes": episodes})
    assert "3Y and 5Y" in text
    assert text.count("25.83%") == 1


def test_default_periods_are_one_three_and_five():
    periods, note = periods_for_question("what is the maximum drawdown of this fund?", comparison=False)
    assert periods == ["1y", "3y", "5y"]
    assert note == ""


def test_ten_year_and_since_start_are_extra_on_one_fund():
    ten, _note = periods_for_question("what is the 10 year drawdown?", comparison=False)
    assert ten == ["1y", "3y", "5y", "10y"]
    started, _note = periods_for_question("drawdown since the fund started", comparison=False)
    assert started == ["1y", "3y", "5y", "inception"]


def test_comparison_stays_on_one_three_and_five():
    periods, _note = periods_for_question("compare the 10 year drawdown", comparison=True)
    assert periods == ["1y", "3y", "5y"]
    assert "10y" not in periods
    named, _note = periods_for_question("their 3-year drawdown", comparison=True)
    assert named == ["3y"]


def test_two_year_request_does_not_substitute_three_year():
    periods, note = periods_for_question("what is the 2 year drawdown?", comparison=False)
    assert periods == []
    assert "3" in note
    assert "3y" not in periods


def test_everyday_words_count_as_drawdown():
    from news_rag.insight.multi_fact import requested_fund_facts

    for question in (
        "what is the drawback of hdfc large cap?",
        "what is the fallback of hdfc large cap?",
        "how much did hdfc large cap fall down?",
        "what is the worst down of hdfc large cap?",
    ):
        assert "drawdown" in requested_fund_facts(question)
        plan = _plan([ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)])
        ensure_drawdown_tools(question, plan)
        assert plan.tool_calls[0].arguments["modules"] == ["drawdown"]


def test_plain_drawdown_does_not_keep_a_planner_category_flag():
    plan = _plan(
        [
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["drawdown"], "include_category": True, "periods": ["1y", "3y", "5y"]},
                wave=1,
            )
        ]
    )
    ensure_drawdown_tools("what is the maximum drawdown of hdfc large cap?", plan)
    assert "include_category" not in plan.tool_calls[0].arguments


def test_cached_episode_does_not_keep_a_later_category_sentence():
    import time

    from news_rag import fund_drawdown as drawdown

    episode = {"isin": "INF179K01BE2", "period": "3y", "max_drawdown": -16.59}
    drawdown._cache[("INF179K01BE2", "3y")] = (time.time() + 60, episode)
    try:
        first = drawdown.fetch_trailing_drawdown("INF179K01BE2", "3y")
        first["category_sentence"] = "cached by mistake"
        second = drawdown.fetch_trailing_drawdown("INF179K01BE2", "3y")
        assert "category_sentence" not in second
    finally:
        drawdown._cache.pop(("INF179K01BE2", "3y"), None)


def test_drawdown_nav_and_benchmark_all_reach_the_composer():
    from news_rag.insight.multi_fact import ensure_multi_fact_tools

    q = "what is the drawdown of absl large cap fund and tell me the nav of this fund and show benchmark performance?"
    plan = _plan(
        [
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
            ToolCall(tool="get_market_snapshot", arguments={}, wave=1),
        ],
        funds=["Aditya Birla Sun Life Large Cap Fund - Regular Plan - Growth"],
    )
    ensure_multi_fact_tools(q, plan)
    ensure_drawdown_tools(q, plan)
    arguments = plan.tool_calls[0].arguments
    assert "snapshot" in arguments["modules"]
    assert "drawdown" in arguments["modules"]
    assert set(plan.asked_facts) >= {"drawdown", "nav", "benchmark", "returns"}
    assert plan.requires_compose is True
    assert "1Y" in arguments["windows"]


def test_risk_analysis_without_periods_still_loads_one_three_and_five_year(monkeypatch):
    from news_rag.fund_drawdown import load_fund_drawdown

    seen: list[list[str]] = []

    def fake_fetch(isin: str, periods: list[str]) -> list[dict]:
        seen.append(list(periods))
        return [
            {"period": period, "max_drawdown": -12.5, "fund_name": "Bandhan Large Cap", "recovered": True}
            for period in periods
        ]

    monkeypatch.setattr("news_rag.fund_drawdown.fetch_drawdown_periods", fake_fetch)
    monkeypatch.setattr(
        "news_rag.fund_search.resolve_fund_for_query",
        lambda name: ({"isin": "INF194K01516", "fund_name": name, "category": "large cap"}, [], []),
    )
    monkeypatch.setattr(
        "news_rag.fund_search.get_fund_index",
        lambda: type("Index", (), {"catalog_entry": lambda self, isin: {"category": "large cap"}})(),
    )
    payload = load_fund_drawdown("Bandhan Large Cap Fund", [], "do the risk analysis of the bandhan large cap?")
    assert seen == [["1y", "3y", "5y"]]
    assert [row["period"] for row in payload["episodes"]] == ["1y", "3y", "5y"]
    assert payload["periods"] == ["1y", "3y", "5y"]


def test_drawdown_question_fetches_only_the_drawdown_module():
    plan = _plan(
        [
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
            ToolCall(tool="search_financial_news", arguments={}, wave=1),
        ]
    )
    ensure_drawdown_tools("what is the maximum drawdown of hdfc large cap?", plan)
    assert [call.tool for call in plan.tool_calls] == ["get_fund_data"]
    assert plan.tool_calls[0].arguments["modules"] == ["drawdown"]
    assert plan.tool_calls[0].arguments["periods"] == ["1y", "3y", "5y"]
    assert "include_category" not in plan.tool_calls[0].arguments
    assert plan.requires_compose is False


def test_ten_year_question_includes_the_extra_period():
    plan = _plan([ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)])
    ensure_drawdown_tools("what is the 10 year drawdown of hdfc large cap?", plan)
    assert plan.tool_calls[0].arguments["periods"] == ["1y", "3y", "5y", "10y"]


def test_category_drawdown_asks_for_the_peer_average():
    assert asks_category_drawdown("is this fund's drawdown better than its category average?")
    plan = _plan([ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)])
    ensure_drawdown_tools("is this fund's drawdown better than its category average?", plan)
    assert plan.tool_calls[0].arguments["include_category"] is True
    assert "10y" not in plan.tool_calls[0].arguments["periods"]


def test_comparison_keeps_compare_funds_and_drops_ten_year():
    plan = _plan(
        [ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
        funds=["HDFC Large Cap Fund", "ICICI Prudential Bluechip Fund"],
    )
    ensure_drawdown_tools("compare the 10 year drawdown of these funds", plan)
    assert plan.tool_calls[0].tool == "compare_funds"
    assert plan.tool_calls[0].arguments["drawdown_periods"] == ["1y", "3y", "5y"]


def test_screen_question_keeps_the_screen_tool():
    q = "give me 5 random banking sector invested funds with their 3 year drawdown"
    plan = _plan(
        [ToolCall(tool="screen_funds_by_exposure", arguments={"sector": "Banking", "top_n": 5}, wave=1)],
        funds=[],
    )
    ensure_screen_facts(q, plan)
    ensure_drawdown_tools(q, plan)
    assert [call.tool for call in plan.tool_calls] == ["screen_funds_by_exposure"]


def test_why_question_keeps_the_news_tool():
    plan = _plan(
        [
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
            ToolCall(tool="search_financial_news", arguments={"scope": "fund"}, wave=1),
        ]
    )
    ensure_drawdown_tools("why did this fund fall from its peak?", plan)
    assert "search_financial_news" in [call.tool for call in plan.tool_calls]
    assert "drawdown" in plan.tool_calls[0].arguments["modules"]
    assert plan.requires_compose is True


def test_expense_question_does_not_add_drawdown():
    q = "what is the expense ratio of hdfc large cap?"
    plan = _plan([ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)])
    ensure_multi_fact_tools(q, plan)
    ensure_drawdown_tools(q, plan)
    assert plan.tool_calls[0].arguments["modules"] == ["snapshot"]


def test_two_year_drawdown_does_not_call_a_tool():
    plan = _plan([ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)])
    ensure_drawdown_tools("what is the 2 year drawdown of hdfc large cap?", plan)
    assert plan.tool_calls == []
    assert "10 years" in plan.direct_reply


def test_definition_does_not_call_a_tool():
    assert is_drawdown_definition("what does a drawdown of -20% mean?")
    plan = _plan([ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1)])
    ensure_drawdown_tools("what does a drawdown of -20% mean?", plan)
    assert plan.tool_calls == []
    assert "peak-to-trough" in plan.direct_reply


def test_top_sector_count_is_not_an_investment_amount():
    assert investment_amount(
        "what is the drawdown and the top 8 sectors of this fund?"
    ) is None


def test_several_facts_include_each_sector_weight():
    from news_rag.insight.evidence_pack import investor_fact_brief

    brief = investor_fact_brief(
        {
            "fund:ABSL": {
                "snapshot": {"fund_name": "ABSL Large Cap", "nav": 490.42, "nav_date": "2026-10-27"},
                "drawdown": {"episodes": [], "question": ""},
            },
            "portfolio:ABSL": {
                "as_on": "2026-09-30",
                "sectors": [
                    {"sector": "Banks", "weight_pct": 26.78},
                    {"sector": "Retailing", "weight_pct": 7.2},
                ],
            },
        },
        ["drawdown", "nav", "sectors"],
    )
    assert "₹490.42" in brief
    assert "Banks: 26.78%" in brief
    assert "Retailing: 7.20%" in brief


def test_rupee_loss_uses_the_drawdown_percentage():
    assert investment_amount("if I had invested ₹1 lakh before the peak") == 100_000
    assert rupee_loss(100_000, -13.02) == 13020.0
    text = render_drawdown_body(
        {"episodes": [_open_episode()]},
        "if I had invested ₹1 lakh before the peak, how much would I have lost?",
    )
    assert "13,020.00" in text


def test_peer_average_and_gap_sentence():
    assert average_peer_drawdown([-20.0, -10.0]) == -15.0
    text = render_drawdown_body(
        {
            "episodes": [
                {
                    **_open_episode(),
                    "category_sentence": "The average worst fall of 4 other funds in this category was 20.00%. This fund's fall was 6.98 percentage points shallower.",
                }
            ]
        }
    )
    assert "shallower" in text


def test_screen_table_shows_the_drawdown_column():
    plan = ExecutionPlan(intent="lookup", answer_mode=AnswerMode.DATA_ONLY, funds=[])
    pack = EvidencePack(
        data_pack={
            "screen": {
                "rankings": [
                    {
                        "fund_name": "Banking Fund A",
                        "drawdown_3y": "13.02% · still 10.97% below the peak",
                    }
                ]
            }
        }
    )
    text = render_data_only_template(pack, plan)
    assert text is not None
    assert "3Y worst fall" in text
    assert "13.02%" in text


def test_compare_table_shows_the_drawdown_row():
    plan = ExecutionPlan(
        intent="compare",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["Fund A", "Fund B"],
    )
    pack = EvidencePack(
        data_pack={
            "compare": {
                "fund_briefs": [{"fund_name": "Fund A"}, {"fund_name": "Fund B"}],
                "holding_overlap": {"rows": [], "fund_names": ["Fund A", "Fund B"]},
                "drawdown_cells": {"1y": ["13.02% · still 10.97% below the peak", "8.00% · recovered on 1st jan 2026"]},
            }
        }
    )
    text = render_data_only_template(pack, plan)
    assert text is not None
    assert "1Y worst fall" in text
    assert "13.02%" in text
    assert "8.00%" in text
