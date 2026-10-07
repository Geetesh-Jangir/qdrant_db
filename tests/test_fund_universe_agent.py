"""Unit tests for FundUniverseAgent and FundUniverseCatalog."""

from __future__ import annotations

from unittest.mock import patch
from news_rag.fund_universe_agent import FundUniverseAgent, get_fund_universe_catalog


def test_catalog_loads_funds():
    catalog = get_fund_universe_catalog()
    assert catalog.total_funds > 2000
    assert len(catalog.amcs) >= 40
    assert "HDFC Mutual Fund" in catalog.amcs or any("HDFC" in a for a in catalog.amcs)


def test_query_large_cap_funds():
    catalog = get_fund_universe_catalog()
    funds = catalog.query(category="Large Cap", limit=3, enrich_nav=False)
    assert len(funds) == 3
    for f in funds:
        assert f["category"] == "Large Cap"
        assert f["isin"].startswith("INF")


def test_query_by_amc_and_category():
    catalog = get_fund_universe_catalog()
    funds = catalog.query(amc="SBI", category="Small Cap", limit=2, enrich_nav=False)
    assert len(funds) >= 1
    assert "SBI" in funds[0]["amc"] or "SBI" in funds[0]["fund_name"]


def test_agent_answer_large_cap_question():
    agent = FundUniverseAgent()
    answer = agent.answer_question("tell me the name of 3 large cap funds")
    assert "Large Cap" in answer
    assert "1." in answer
    assert "2." in answer
    assert "3." in answer
    assert "INF" in answer


def test_agent_answer_elss_question():
    agent = FundUniverseAgent()
    answer = agent.answer_question("What are 2 ELSS tax saver funds from HDFC?")
    assert "HDFC" in answer
    assert "1." in answer
    assert "INF" in answer


def test_agent_query_gold_etfs():
    agent = FundUniverseAgent()
    answer = agent.answer_question("Show me 3 gold etfs")
    assert "Gold" in answer
    assert "INF" in answer
