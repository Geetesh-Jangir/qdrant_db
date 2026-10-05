"""Holdings + live price + news linkage for fund ask queries."""

from unittest.mock import patch

from news_rag.holdings_market import (
    build_holdings_market_snapshots,
    question_wants_holdings_performance,
    should_fetch_holdings_market,
)


def test_question_wants_holdings_performance():
    assert question_wants_holdings_performance(
        "How are Parag Parikh Large Cap top 3 holdings working?"
    )
    assert not question_wants_holdings_performance("What is the NAV of HDFC Flexi Cap?")


def test_should_fetch_when_holdings_news():
    assert should_fetch_holdings_market(
        "tell me about a fund",
        {"fund_top_stocks", "holdings_news"},
        True,
    )


@patch("news_rag.holdings_market.get_stock_profile")
def test_build_snapshots_links_news(mock_profile):
    mock_profile.return_value = {
        "ticker": "INFY.NS",
        "cmp": 1500.0,
        "return_1d": 0.5,
        "return_1w": 2.0,
        "return_1m": -1.0,
        "range_30d": (1400.0, 1550.0),
        "range_52w": None,
    }
    rows = [{"name": "Infosys Limited", "percentage": 8.5}]
    articles = [
        {
            "title": "Infosys wins deal",
            "snippet": "Infosys Limited",
            "direction": "positive",
            "entity_names": ["Infosys Limited"],
        }
    ]
    snaps = build_holdings_market_snapshots(
        rows, articles, top_n=1, window_days=30, dedicated_news=False
    )
    assert len(snaps) == 1
    assert snaps[0]["price"]["return_1w"] == 2.0
    assert snaps[0]["news"]["positive"] == 1
    assert len(snaps[0]["news"]["linked_articles"]) == 1
