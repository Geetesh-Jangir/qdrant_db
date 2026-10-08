"""Relationship facts, follow-up tool choice, and universe search on the agent."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from news_rag.ask_agent import _SPECIAL_TOOLS, _accumulate, _parse_decision, _run_special
from news_rag.ask_execution import ExecutionBundle
from news_rag.ask_plan import AskPlan, PlannedTool
from news_rag.name_resolution import ResolvedNames
from news_rag.relationships import trace_relationships
from news_rag.stock_fund_ranking import funds_holding_stock


def test_trace_marks_holding_direct_and_news_name_indirect():
    result = trace_relationships(
        driver="crude oil",
        target="HDFC Flexi Cap",
        holdings_rows=[{"name": "Reliance Industries", "percentage": 8.2}],
        sector_rows=[{"sector": "Information Technology", "percentage": 12.0}],
        articles=[
            {
                "title": "Crude oil jumps on supply risk",
                "snippet": "Higher crude raises costs for paint makers and airlines.",
                "entity_names": ["crude oil", "Asian Paints"],
                "holding_names": [],
                "sector_names": ["Chemicals"],
                "direction": "negative",
            }
        ],
        fund_name="HDFC Flexi Cap",
    )
    assert any(row["name"] == "Asian Paints" and row["kind"] == "indirect" for row in result["indirect_news"])
    direct_names = {row["name"] for row in result["direct"]}
    assert "Asian Paints" not in direct_names


def test_trace_marks_a_held_name_as_direct():
    result = trace_relationships(
        driver="Reliance Industries",
        holdings_rows=[{"name": "Reliance Industries Limited", "percentage": 6.5}],
        sector_rows=[],
        articles=[],
        fund_name="Sample Fund",
    )
    assert result["direct"]
    assert result["direct"][0]["kind"] == "direct"
    assert result["direct"][0]["channel"] == "holding"
    assert result["direct"][0]["weight_pct"] == 6.5
    assert result["indirect_news"] == []


def test_agent_follow_up_after_holdings():
    first = {
        "status": "need_tools",
        "why": "Need the holdings before news.",
        "question_reading": {
            "intent": "How holdings news hits the fund",
            "must_cover": ["holding weights"],
            "sentiment": "any",
        },
        "entities": [{"raw": "HDFC Flexi", "role": "fund_scheme", "cleaned_phrase": "HDFC Flexi Cap Fund"}],
        "tools": [{"tool": "fund_top_stocks", "purpose": "list holdings", "fund_entity_index": 0}],
    }
    second = {
        "status": "need_tools",
        "why": "Holdings are in. Fetch their news.",
        "question_reading": {"intent": "How holdings news hits the fund"},
        "information_gaps": ["news on Reliance"],
        "tools": [
            {
                "tool": "holdings_news",
                "purpose": "news for the top holding",
                "depends_on": "fund_top_stocks",
                "entity_filters": ["Reliance Industries"],
            }
        ],
    }
    _, first_plan = _parse_decision(first)
    _, second_plan = _parse_decision(second)
    plan = _accumulate(first_plan, second_plan)
    names = [tool.tool for tool in plan.tools]
    assert names == ["fund_top_stocks", "holdings_news"]
    assert plan.tools[1].depends_on == "fund_top_stocks"
    assert plan.information_gaps == ["news on Reliance"]


def test_universe_search_is_callable_from_the_agent():
    assert "fund_universe_search" in _SPECIAL_TOOLS
    plan = AskPlan()
    bundle = ExecutionBundle(names=ResolvedNames())
    tool = PlannedTool(tool="fund_universe_search", category="ELSS", amc="HDFC", top_n=2, purpose="list ELSS")
    with patch("news_rag.ask_agent.run_fund_universe_discovery", return_value={"ok": True, "data": {"funds": [], "count": 0}, "error": ""}) as mocked:
        result = _run_special(tool, plan, bundle)
    mocked.assert_called_once()
    assert result["ok"] is True


def test_funds_holding_stock_keeps_the_count_when_the_scan_finds_nothing():
    with patch("news_rag.stock_fund_ranking.default_holder_candidates", return_value=[{"isin": "INFTEST", "fund_name": "Test"}]), patch(
        "news_rag.stock_fund_ranking.scan_schemes_holding_stock", return_value=[]
    ):
        payload = funds_holding_stock("Infosys Limited", limit=3)
    assert payload["fund_count"]
    assert payload["industry"]
    assert payload["funds"] == []
    assert payload["fund_list_available"] is False
    assert "did not find named schemes" in payload["note"].lower()


def test_holder_compare_drops_a_fund_with_no_weight():
    from news_rag.ask_agent import _rows_for_compare

    bundle = ExecutionBundle(names=ResolvedNames())
    bundle.tool_results["screen_funds_0"] = {
        "ok": True,
        "data": {
            "stock_name": "ICICI Bank",
            "rankings": [
                {"fund_name": "Holder A", "isin": "INFA", "weight_pct": 6.43, "holding_name": "ICICI Bank Ltd."},
                {"fund_name": "Holder B", "isin": "INFB", "weight_pct": 4.2, "holding_name": "ICICI Bank Ltd."},
                {"fund_name": "Quantum Nifty 50 ETF", "isin": "INFQ", "return_1m_pct": 7.47},
            ],
        },
    }
    rows = _rows_for_compare(bundle, PlannedTool(tool="compare_funds", stock_name="ICICI Bank", top_n=2))
    assert [row["fund_name"] for row in rows] == ["Holder A", "Holder B"]


def test_fund_gap_screens_the_amc_in_the_question():
    from news_rag.ask_agent import _fill_fund_ranking_gap

    bundle = ExecutionBundle(names=ResolvedNames())
    plan = AskPlan()
    with patch(
        "news_rag.tools.run_screen_funds",
        return_value={"ok": True, "data": {"rankings": [{"fund_name": "HDFC Flexi", "isin": "INFX", "return_1m_pct": 1.0}]}},
    ) as mocked, patch(
        "news_rag.tools.screen_hints_from_question",
        return_value={"sector_name": "", "category": "", "amc": "HDFC", "stock_name": ""},
    ):
        _fill_fund_ranking_gap(
            "give me any name of the funds provided by HDFC",
            plan,
            bundle,
            [{"entities_found": ["Banks"]}],
            date_from=None,
            date_to=None,
            min_impact=None,
            source=None,
            direction=None,
            query_log=None,
        )
    assert mocked.call_args.kwargs["amc"] == "HDFC"
    assert mocked.call_args.kwargs["sector_name"] == ""
    assert any(key.startswith("screen_funds") for key in bundle.tool_results)


def test_fund_gap_skips_when_universe_search_already_named_funds():
    from news_rag.ask_agent import _fill_fund_ranking_gap

    bundle = ExecutionBundle(names=ResolvedNames())
    bundle.tool_results["fund_universe_search_0_1"] = {
        "ok": True,
        "data": {"funds": [{"fund_name": "HDFC Large Cap", "isin": "INFH"}]},
    }
    plan = AskPlan()
    with patch("news_rag.tools.run_screen_funds") as mocked:
        _fill_fund_ranking_gap(
            "name any two hdfc large cap fund?",
            plan,
            bundle,
            [],
            date_from=None,
            date_to=None,
            min_impact=None,
            source=None,
            direction=None,
            query_log=None,
        )
    mocked.assert_not_called()


def test_fund_name_question_is_detected_and_sectors_are_capped():
    from news_rag.ask_agent import _sectors_from_observations, question_wants_fund_names

    assert question_wants_fund_names(
        "whats happening in the market and what are the funds which are most benefited now?"
    )
    assert not question_wants_fund_names("whats happening in the market right now?")
    sectors = _sectors_from_observations(
        [{"entities_found": ["Banks", "Infrastructure", "Textiles", "Pharma", "Power"]}]
    )
    assert sectors == ["Banks", "Infrastructure", "Textiles", "Pharma"]


def test_ui_keeps_narrative_when_bullets_exist():
    text = Path("news_rag/static/index.html").read_text(encoding="utf-8")
    assert "narrative !== headline && !bullets.length" not in text
    assert 'appendProse(container, narrative, "insight-body")' in text
