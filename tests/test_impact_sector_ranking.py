"""Impact intelligence: sector index loader, routing gate, ranking order."""

from __future__ import annotations

from unittest.mock import patch

from news_rag.impact_gating import (
    is_sector_fund_discovery_query,
    ranking_mode,
    should_use_sector_ranking_index,
    try_fast_fund_event_impact_route,
    try_fast_impact_funds_route,
)
from news_rag.query_router import route_query
from news_rag.query_router import RouterFund, RouterResult
from news_rag.impact_rationale import sector_impact_reasoning
from news_rag.sector_fund_ranking import SectorFundRankingIndex, get_sector_fund_ranking_index


def test_top_100_scheme_name_is_not_sector_discovery() -> None:
    q = "what is the impact of rbi repo rate changes on hdfc top 100 fund?"
    assert not is_sector_fund_discovery_query(q)
    r = try_fast_fund_event_impact_route(
        "What is the impact of RBI repo rate changes on HDFC Top 100 Fund?"
    )
    assert r is not None
    assert r.intent == "fund_event_impact"
    assert "top 100" in r.fund.name.lower()


def test_top_10_funds_rbi_is_discovery() -> None:
    q = "which are the top 10 funds worst hit by rbi repo rate hike news?"
    assert is_sector_fund_discovery_query(q)
    r = try_fast_impact_funds_route(q)
    assert r is not None
    assert r.intent == "impact_funds"


def test_route_hdfc_top_100_not_impact_funds() -> None:
    r = route_query("What is the impact of RBI repo rate changes on HDFC Top 100 Fund?")
    assert r.intent == "fund_event_impact"
    assert r.intent != "impact_funds"


def test_fast_route_fund_event_crude() -> None:
    r = try_fast_fund_event_impact_route(
        "How will a surge in crude oil prices affect Parag Parikh Flexi Cap Fund?"
    )
    assert r is not None
    assert r.intent == "fund_event_impact"
    assert "parag" in r.fund.name.lower() or "flexi" in r.fund.name.lower()
    assert "crude" in r.event_focus.lower() or "oil" in r.event_focus.lower()


def test_fast_route_top_funds_auto() -> None:
    r = try_fast_impact_funds_route("What are the top 5 funds affected by automotive sector news?")
    assert r is not None
    assert r.intent == "impact_funds"
    assert r.fund.is_empty()
    assert r.raw_json.get("impact_limit") == 5


def test_should_not_use_sector_index_when_fund_named() -> None:
    router = RouterResult(
        intent="fund_event_impact",
        fund=RouterFund(name="Parag Parikh Flexi Cap Fund"),
        companies=[],
        event_focus="crude oil",
        window_days=7,
        asked=[],
        raw_json={},
    )
    assert ranking_mode(router) == "single_fund"
    assert not should_use_sector_ranking_index(router)


def test_should_use_sector_index_discovery() -> None:
    router = RouterResult(
        intent="impact_funds",
        fund=RouterFund(),
        companies=[],
        event_focus="RBI repo",
        window_days=7,
        asked=[],
        raw_json={},
    )
    assert should_use_sector_ranking_index(router)


def test_top_funds_order_from_fixture() -> None:
    doc = {
        "_meta": {"version": 1},
        "sectors": {
            "Automobiles": {
                "fund_count": 3,
                "allocations": {
                    "INFAAA11111": 5.0,
                    "INFBBB22222": 12.0,
                    "INFCCC33333": 8.0,
                },
            }
        },
    }
    idx = SectorFundRankingIndex(doc)
    rows = idx.top_funds_for_sector("Automobiles", limit=3, isin_allowlist=None)
    assert [r[0] for r in rows] == ["INFBBB22222", "INFCCC33333", "INFAAA11111"]


def test_sector_impact_reasoning_mentions_mechanism() -> None:
    text = sector_impact_reasoning(
        "top 5 funds affected by automotive sector news",
        sector_keys=["Automobiles", "Auto Components"],
        event_focus="automotive sector",
        direction_filter="any",
        article_count=0,
    )
    assert "NAV" in text or "Automobiles" in text
    assert len(text) > 80


def test_resolve_automotive_alias() -> None:
    idx = get_sector_fund_ranking_index()
    keys = idx.resolve_from_question("top funds hurt by automotive news", "")
    assert "Automobiles" in keys or "Auto Components" in keys


def test_single_fund_crude_excludes_banks_from_sectors() -> None:
    from news_rag.impact_answer import build_single_fund_impact_packet
    from news_rag.parse import ParsedQuery

    router = RouterResult(
        intent="fund_event_impact",
        fund=RouterFund(name="PPFAS Flexi Cap Fund"),
        companies=[],
        event_focus="crude oil",
        window_days=7,
        asked=[],
        raw_json={},
    )
    parsed = ParsedQuery(
        question="How will a surge in crude oil prices affect Parag Parikh Flexi Cap Fund?",
        published_from="2026-01-01T00:00:00Z",
        published_to="2026-10-01T00:00:00Z",
        window_label="last 7 days",
        stock_hint="",
        entity_resolved=[],
        entity_match_note="",
        intent="fund_event_impact",
        fund_resolved={
            "isin": "INF879O01019",
            "fund_short_name": "PPFAS Flexi Cap Fund",
            "sectors": {
                "Banks": 20.91,
                "Automobiles": 6.71,
                "Petroleum Products": 0.35,
            },
            "holdings": {},
        },
        router_result=router,
    )
    articles = [
        {
            "title": "RBI holds rates",
            "url": "https://example.com/rbi",
            "entity_names": ["Banks", "HDFC Bank"],
            "industry_names": ["Banks"],
        },
        {
            "title": "Crude oil surges",
            "url": "https://example.com/oil",
            "entity_names": ["Crude Oil"],
            "industry_names": ["Petroleum Products"],
        },
    ]
    out = build_single_fund_impact_packet(parsed, articles, router=router)
    sectors = [x["sector"] for x in out["impact_breakdown"]["touched_sectors"]]
    assert "Banks" not in sectors
    assert "Automobiles" in sectors
    assert "moderate" in out["insight_summary"].lower() or "limited" in out["insight_summary"].lower()


def test_generate_answer_discovery_does_not_call_sector_rank_when_fund_set() -> None:
    from news_rag.impact_answer import try_impact_answer
    from news_rag.parse import ParsedQuery

    router = RouterResult(
        intent="fund_event_impact",
        fund=RouterFund(name="HDFC Large Cap Fund"),
        companies=[],
        event_focus="crude",
        window_days=7,
        asked=[],
        raw_json={},
    )
    parsed = ParsedQuery(
        question="How does crude oil affect HDFC Large Cap Fund?",
        published_from="2026-01-01T00:00:00Z",
        published_to="2026-10-01T00:00:00Z",
        window_label="7 days",
        stock_hint="",
        entity_resolved=[],
        entity_match_note="",
        intent="fund_event_impact",
        fund_resolved={
            "isin": "INF179K01BE2",
            "fund_short_name": "HDFC Large Cap Fund",
            "sectors": {"Banks": 20.0},
            "holdings": {},
        },
        router_result=router,
    )
    with patch("news_rag.impact_answer.rank_funds_by_sector_exposure") as mock_rank:
        result = try_impact_answer(
            parsed,
            [],
            router,
            question=parsed.question,
            published_from=parsed.published_from,
            published_to=parsed.published_to,
        )
        mock_rank.assert_not_called()
    assert result is not None
    assert result.get("insight_source") == "impact_single_fund"
