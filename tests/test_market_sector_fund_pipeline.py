"""Tests for compound market + sector + directional mutual fund pipeline."""

from __future__ import annotations

from unittest.mock import patch
from news_rag.ask_plan import AskPlan, PlannedTool
from news_rag.plan_enrich import enrich_ask_plan
from news_rag.tools import enrich_rankings_with_nav
from news_rag.ask_execution import ExecutionBundle
from news_rag.ask_composer import _finalize_compose, _build_ranked_fund_bullets


def _mock_nav_history(isin: str):
    if isin == "INF1":
        return {
            "success": True,
            "latest_nav": 150.0,
            "latest_date": "2026-03-30",
            "stats": {
                "1W": {"change_pct": 1.25},
                "1M": {"change_pct": 4.50},
            },
        }
    if isin == "INF2":
        return {
            "success": True,
            "latest_nav": 80.0,
            "latest_date": "2026-03-30",
            "stats": {
                "1W": {"change_pct": -2.10},
                "1M": {"change_pct": -6.30},
            },
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
    assert res[0]["return_1m_pct"] == 4.50
    assert res[0]["return_1w_pct"] == 1.25
    assert res[0]["nav_direction_match"] is True


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
def test_enrich_rankings_with_nav_negative(mock_nav):
    candidates = [
        {"isin": "INF1", "fund_name": "Fund Positive", "sector_weight_pct": 20.0, "matched_sectors": ["IT"]},
        {"isin": "INF2", "fund_name": "Fund Negative", "sector_weight_pct": 40.0, "matched_sectors": ["IT"]},
    ]
    res = enrich_rankings_with_nav(candidates, direction="negative", top_n=2)
    assert len(res) == 1
    assert res[0]["isin"] == "INF2"
    assert res[0]["return_1m_pct"] == -6.30
    assert res[0]["return_1w_pct"] == -2.10


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
def test_enrich_rankings_with_nav_any(mock_nav):
    candidates = [
        {"isin": "INF1", "fund_name": "Fund Positive", "sector_weight_pct": 20.0, "matched_sectors": ["IT"]},
        {"isin": "INF2", "fund_name": "Fund Negative", "sector_weight_pct": 40.0, "matched_sectors": ["IT"]},
    ]
    res = enrich_rankings_with_nav(candidates, direction="any", top_n=2, sort_by="performance")
    assert len(res) == 2
    assert res[0]["isin"] == "INF1"
    assert res[1]["isin"] == "INF2"


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
def test_enrich_rankings_performance_beats_exposure_weight(mock_nav):
    """Higher sector weight must not beat better 1M NAV when sort_by=performance."""
    candidates = [
        {"isin": "INF2", "fund_name": "Heavy loser", "sector_weight_pct": 80.0, "matched_sectors": ["Banks"]},
        {"isin": "INF1", "fund_name": "Lighter winner", "sector_weight_pct": 30.0, "matched_sectors": ["Banks"]},
    ]
    res = enrich_rankings_with_nav(candidates, direction="any", top_n=1, sort_by="performance")
    assert res[0]["isin"] == "INF1"


def test_plan_enrich_sets_affected_funds_when_question_asks_funds():
    plan = AskPlan(
        tools=[
            PlannedTool(tool="common_market_news"),
            PlannedTool(tool="sector_news"),
        ],
        affected_funds="none",
    )
    q = "tell me whats happening in the market right now and what are the sectors which are performing well and then which mutual funds are working well"
    enriched = enrich_ask_plan(q, plan)
    assert enriched.affected_funds == "after_news"
    assert enriched.affected_funds_top_n >= 6


def test_build_ranked_fund_bullets():
    funds = [
        {
            "fund_name": "ICICI Prudential Technology Fund",
            "sector_weight_pct": 34.5,
            "matched_sectors": ["Information Technology"],
            "return_1m_pct": 5.2,
            "return_1w_pct": 1.1,
        }
    ]
    bullets = _build_ranked_fund_bullets(funds)
    assert len(bullets) == 1
    b = bullets[0]
    assert "**ICICI Prudential Technology Fund**" in b
    assert "**34.5%**" in b
    assert "**Information Technology**" in b
    assert "**+5.2%**" in b
    assert "**+1.1%**" in b


def test_finalize_compose_includes_ranked_funds_for_fund_query():
    from news_rag.name_resolution import ResolvedNames
    bundle = ExecutionBundle(names=ResolvedNames())
    bundle.tool_results["affected_funds_post"] = {
        "ok": True,
        "data": {
            "rankings": [
                {
                    "fund_name": "Nippon India Power & Infra Fund",
                    "sector_weight_pct": 28.0,
                    "matched_sectors": ["Power"],
                    "return_1m_pct": 3.8,
                    "return_1w_pct": 0.9,
                }
            ]
        },
    }
    initial_bullets = [
        "**Market Backdrop** — Indices under pressure from global cues.",
        "**Information Technology** — Strong exports boost realization.",
    ]
    q = "what is happening in market and what sectors and mutual funds are performing well"
    _, _, bullets = _finalize_compose(
        "Headline",
        "",
        initial_bullets,
        bundle,
        digests=[],
        market_pulse_clusters=[{"label": "Theme 1", "article_count": 2}],
        question=q,
        answer_parts=q,
        sentiment="positive",
    )
    assert any("Nippon India Power & Infra Fund" in b for b in bullets)
    assert any("+3.8%" in b for b in bullets)


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
def test_enrich_rankings_performance_relative_best_when_all_negative(mock_nav):
    candidates = [
        {"isin": "INF2", "fund_name": "Fund Negative 1", "sector_weight_pct": 75.0, "matched_sectors": ["Healthcare"]},
    ]
    res = enrich_rankings_with_nav(candidates, direction="positive", top_n=2, sort_by="performance")
    assert res == []


def test_plan_enrich_adds_sector_funds_for_banking_best_query():
    plan = AskPlan(
        tools=[
            PlannedTool(tool="macro_news_enhanced", semantic_query="RBI repo rate India"),
            PlannedTool(tool="sector_news", semantic_query="banking credit India"),
        ],
        affected_funds="none",
    )
    q = (
        "What are the latest updates on RBI monetary policy, how does it affect banking and financials, "
        "and which banking mutual funds have performed best over the last month?"
    )
    enriched = enrich_ask_plan(q, plan)
    sector_tools = [t for t in enriched.tools if t.tool == "sector_funds"]
    assert len(sector_tools) == 1
    assert "banking" in (sector_tools[0].sector_name or "").lower()


def test_finalize_compose_does_not_duplicate_when_llm_wrote_fund_bullets():
    from news_rag.name_resolution import ResolvedNames
    bundle = ExecutionBundle(names=ResolvedNames())
    bundle.tool_results["affected_funds_post"] = {
        "ok": True,
        "data": {
            "rankings": [
                {
                    "fund_name": "Nippon India Power & Infra Fund",
                    "sector_weight_pct": 28.0,
                    "matched_sectors": ["Power"],
                    "return_1m_pct": 3.8,
                    "return_1w_pct": 0.9,
                }
            ]
        },
    }
    llm_bullets = [
        "**Market Backdrop** — Indices under pressure from global cues.",
        "**Information Technology** — Strong exports boost realization.",
        "**Top Fund: ICICI Prudential Technology Fund** — Holds **34.2%** in Information Technology with **+4.8%** return.",
    ]
    q = "what is happening in market and what sectors and mutual funds are performing well"
    _, _, bullets = _finalize_compose(
        "Headline",
        "",
        llm_bullets,
        bundle,
        digests=[],
        market_pulse_clusters=[{"label": "Theme 1", "article_count": 2}],
        question=q,
        answer_parts=q,
        sentiment="positive",
    )
    # Since LLM already provided a Top Fund bullet, it should not blindly append more
    assert not any("Nippon India Power & Infra Fund" in b for b in bullets)
    assert len(bullets) == 3
