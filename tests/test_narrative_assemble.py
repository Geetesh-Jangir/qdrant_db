"""assemble_body, compact_facts, sector hints."""

from ai_insight.common.narrative import (
    assemble_body,
    compact_facts,
    enrich_flow_gross,
    repetition_score,
    sector_tilt_hint,
)
from ai_insight.common.flows import FlowDay


def test_assemble_body_joins_beats():
    body = assemble_body(
        {
            "what_happened": "Nifty slipped a little today.",
            "why": "Oil prices stayed high earlier this week.",
            "impacted": "Energy names saw more headlines.",
            "investor_meaning": "Volatility may stay elevated near term.",
        }
    )
    assert body.count("\n\n") == 3
    assert "Nifty" in body


def test_assemble_body_falls_back_to_legacy():
    body = assemble_body({"body": "Legacy single paragraph."})
    assert body == "Legacy single paragraph."


def test_compact_facts_trims_market_payload():
    huge = {
        "trading_date": "2026-03-18",
        "nifty_change_pct": -0.5,
        "nifty_history": {"daily": [{"date": "d", "close": 1}] * 20},
        "aligned_market_flows": [{"date": f"d{i}"} for i in range(12)],
    }
    slim = compact_facts("market_driver_digest", huge)
    assert "nifty_history" not in slim
    assert len(slim.get("aligned_market_flows") or []) <= 5


def test_sector_tilt_hint_from_news_map():
    news_map = [
        {
            "cluster_id": "c0",
            "entities": [
                {"name": "Banks", "direction": "positive", "count": 3},
                {"name": "Macro - Crude Oil", "direction": "negative", "count": 2},
            ],
        }
    ]
    hints = sector_tilt_hint(news_map, None)
    assert hints[0]["name"] == "Banks"


def test_enrich_flow_gross():
    facts = {"flow_trade_date": "2026-03-18"}
    history = [
        FlowDay(
            "2026-03-18",
            100,
            -50,
            {"buy": 500, "sell": 400},
            {"buy": 200, "sell": 250},
            "",
        )
    ]
    enrich_flow_gross(facts, history)
    assert facts["fii_gross_buy_crore"] == 500.0


def test_repetition_score_low_for_distinct_beats():
    beats = {
        "what_happened": "FII bought today.",
        "why": "Crude eased globally.",
        "impacted": "IT indices led gains.",
        "investor_meaning": "Risk appetite may improve.",
    }
    assert repetition_score(beats) < 0.4