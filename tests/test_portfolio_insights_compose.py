"""Portfolio insight readiness and matching (fixtures only)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from ai_insight.common.schemas import Chip, Envelope, InsightBundle, Meta, Viz
from ai_insight.portfolio_insights.catalog import readiness
from ai_insight.portfolio_insights.compose import compose_portfolio_insights
from ai_insight.common.market_daily_store import save_market_daily
from ai_insight.portfolio_insights.match import match_holdings, match_sectors


def _envelope(insight_id: str, trading_date: str, **facts) -> Envelope:
    return Envelope(
        insight_id=insight_id,
        trading_date=trading_date,
        as_of_ist="2026-03-18T17:00:00+05:30",
        status="ok",
        headline="Headline",
        body="Body text.",
        chips=[Chip(label="X", value="1%", tone="neutral")],
        viz=Viz(type="none"),
        facts=facts,
        meta=Meta(),
    )


def test_readiness_missing_common(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTS_DATA_DIR", str(tmp_path))
    result = readiness("2026-03-18")
    assert result.ready is False
    assert any(m.startswith("common:") for m in result.missing)


def test_sector_match_order_and_cap():
    trading_date = "2026-03-18"
    banks = Envelope(
        insight_id="sector_index_insights",
        trading_date=trading_date,
        as_of_ist="2026-03-18T17:00:00+05:30",
        status="ok",
        headline="Banks week",
        body="Banks body",
        chips=[],
        viz=Viz(type="none"),
        facts={
            "kind": "sector_index",
            "catalog_sectors": ["Banks"],
            "sectors": ["Banks"],
            "index": "Nifty Bank",
        },
        meta=Meta(),
    )
    pharma = Envelope(
        insight_id="sector_index_insights",
        trading_date=trading_date,
        as_of_ist="2026-03-18T17:00:00+05:30",
        status="ok",
        headline="Pharma week",
        body="Pharma body",
        chips=[],
        viz=Viz(type="none"),
        facts={
            "kind": "sector_index",
            "catalog_sectors": ["Pharmaceuticals & Biotechnology"],
            "sectors": ["Pharmaceuticals & Biotechnology"],
            "index": "Nifty Pharma",
        },
        meta=Meta(),
    )
    rotation = _envelope("sector_index_insights", trading_date, kind="sector_rotation", rows=[])

    bundle = InsightBundle(
        insight_id="sector_index_insights",
        trading_date=trading_date,
        as_of_ist="2026-03-18T17:00:00+05:30",
        status="ok",
        items=[banks, pharma, rotation],
    )
    projected = [
        {"trading_date": trading_date, "headline": "Banks week", "body": "b", "status": "ok"},
        {"trading_date": trading_date, "headline": "Pharma week", "body": "p", "status": "ok"},
    ]

    portfolio = {
        "sector_allocation": [
            {"sector": "Auto", "percentage": 5.0},
            {"sector": "Banks", "percentage": 20.0},
            {"sector": "Pharmaceuticals & Biotechnology", "percentage": 10.0},
        ]
    }

    market_snap = {
        "trading_date": trading_date,
        "common": [],
        "sectors": [
            {
                "names": ["Banks", "Nifty Bank"],
                "status": "ok",
                "headline": "Banks week",
                "body": "Banks body",
                "input_tokens": 1,
                "output_tokens": 1,
                "articles": [],
            },
            {
                "names": ["Pharmaceuticals & Biotechnology", "Nifty Pharma"],
                "status": "ok",
                "headline": "Pharma week",
                "body": "Pharma body",
                "input_tokens": 1,
                "output_tokens": 1,
                "articles": [],
            },
        ],
    }
    portfolio_with_funds = {
        **portfolio,
        "sector_allocation": [
            {"sector": "Auto", "percentage": 5.0},
            {"sector": "Banks", "percentage": 20.0, "fund_isins": ["INF111", "INF222", "INF333"]},
            {"sector": "Pharmaceuticals & Biotechnology", "percentage": 10.0},
        ],
    }
    with patch("ai_insight.portfolio_insights.match.load_market_daily", return_value=market_snap):
        with patch(
            "ai_insight.portfolio_insights.personalize.resolve_fund_display",
            return_value="hdfc large cap",
        ):
            matched, unmatched = match_sectors(portfolio_with_funds, trading_date, crn="CRN-test", limit=3)

    assert len(matched) == 2
    assert matched[0].get("headline_base") == "Banks week"
    assert "hdfc large cap" in matched[0]["headline"]
    assert matched[0]["match_meta"]["sector"] == "Banks"
    assert matched[1]["match_meta"]["sector"] == "Pharmaceuticals & Biotechnology"
    assert "Auto" in unmatched


def test_holding_match_canonical():
    trading_date = "2026-03-18"
    daily = {
        "generated_on": trading_date,
        "insights": [
            {"stock_id": "HDFCBANK", "stock_name": "HDFC Bank", "headline": "HDFC", "insight_lines": ["Line one."]}
        ],
        "counts": {"ok": 1},
    }
    portfolio = {
        "top_holdings": [
            {
                "instrument_name": "HDFC Bank Ltd",
                "percentage": 4.5,
                "fund_isins": ["INF999"],
            }
        ]
    }

    with patch("ai_insight.portfolio_insights.match.load_holding_stock_insights", return_value=None):
        with patch("ai_insight.portfolio_insights.match.load_daily", return_value=daily):
            with patch(
                "ai_insight.portfolio_insights.personalize.resolve_fund_display",
                return_value="kotak flexi cap",
            ):
                matched, unmatched = match_holdings(portfolio, trading_date, crn="CRN-h", limit=3)

    assert len(matched) == 1
    assert matched[0]["headline_base"] == "HDFC"
    assert "kotak flexi cap" in matched[0]["headline"]
    assert matched[0]["match_meta"]["instrument_name"] == "HDFC Bank Ltd"
    assert not unmatched


def test_compose_fails_when_not_ready():
    with patch("ai_insight.portfolio_insights.compose.resolve_trading_date", return_value="2026-03-18"):
        with patch(
            "ai_insight.portfolio_insights.compose.readiness",
            return_value=type("R", (), {"ready": False, "missing": ["common:x"], "details": {}})(),
        ):
            out = compose_portfolio_insights("CRN-test123")
    assert out["status"] == "missing_insights"
    assert "common" not in out or not out.get("common")


def test_compose_bad_crn():
    ready = type("R", (), {"ready": True, "missing": [], "details": {}})()
    with patch("ai_insight.portfolio_insights.compose.resolve_trading_date", return_value="2026-03-18"):
        with patch("ai_insight.portfolio_insights.compose.readiness", return_value=ready):
            out = compose_portfolio_insights("!!")
    assert out["status"] == "bad_crn"