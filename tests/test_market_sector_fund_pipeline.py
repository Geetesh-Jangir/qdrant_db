"""Sector fund ranking + NAV enrichment (insight pipeline building blocks)."""

from __future__ import annotations

from unittest.mock import patch

from news_rag.ask_plan import AskPlan, PlannedTool
from news_rag.plan_enrich import enrich_ask_plan
from news_rag.tools import enrich_rankings_with_nav


def _mock_nav_history(isin: str):
    if isin == "INF1":
        return {
            "success": True,
            "latest_nav": 150.0,
            "latest_date": "2026-03-30",
            "stats": {"1W": {"change_pct": 1.25}, "1M": {"change_pct": 4.50}},
        }
    if isin == "INF2":
        return {
            "success": True,
            "latest_nav": 80.0,
            "latest_date": "2026-03-30",
            "stats": {"1W": {"change_pct": -2.10}, "1M": {"change_pct": -6.30}},
        }
    return {"success": False}


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
def test_enrich_rankings_with_nav_positive(mock_nav):
    candidates = [
        {"isin": "INF2", "fund_name": "Fund Negative", "sector_weight_pct": 40.0, "matched_sectors": ["IT"]},
        {"isin": "INF1", "fund_name": "Fund Positive", "sector_weight_pct": 20.0, "matched_sectors": ["IT"]},
    ]
    res = enrich_rankings_with_nav(candidates, direction="positive", top_n=2)
    assert len(res) == 1
    assert res[0]["isin"] == "INF1"


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
def test_enrich_rankings_with_nav_any(mock_nav):
    candidates = [
        {"isin": "INF1", "fund_name": "Fund Positive", "sector_weight_pct": 20.0, "matched_sectors": ["IT"]},
        {"isin": "INF2", "fund_name": "Fund Negative", "sector_weight_pct": 40.0, "matched_sectors": ["IT"]},
    ]
    res = enrich_rankings_with_nav(candidates, direction="any", top_n=2, sort_by="performance")
    assert res[0]["isin"] == "INF1"


def test_plan_enrich_keeps_market_tools():
    plan = AskPlan(
        tools=[PlannedTool(tool="common_market_news"), PlannedTool(tool="sector_news")],
        affected_funds="none",
    )
    q = "market sectors and mutual funds working well"
    enriched = enrich_ask_plan(q, plan)
    assert enriched.affected_funds == "none"
