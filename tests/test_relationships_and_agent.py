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


def test_funds_holding_stock_does_not_invent_a_fund_list():
    payload = funds_holding_stock("Infosys Limited", limit=3)
    assert payload["fund_count"]
    assert payload["industry"]
    assert payload["funds"] == []
    assert payload["fund_list_available"] is False
    assert "unavailable" in payload["note"].lower()


def test_ui_keeps_narrative_when_bullets_exist():
    text = Path("news_rag/static/index.html").read_text(encoding="utf-8")
    assert "narrative !== headline && !bullets.length" not in text
    assert 'appendProse(container, narrative, "insight-body")' in text
