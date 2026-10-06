"""Sector-fund ranking purity (sectoral vs arbitrage/hybrid)."""

from news_rag.sector_fund_ranking import classify_sector_fund_purity


def test_arbitrage_is_defensive_not_sectoral():
    assert (
        classify_sector_fund_purity("HDFC Arbitrage Fund - Regular Plan - Growth")
        == "defensive_neutral"
    )


def test_banking_sectoral_fund_detected():
    assert (
        classify_sector_fund_purity("Nippon India Banking & Financial Services Fund")
        == "dedicated_sectoral"
    )


def test_large_cap_is_diversified_not_sectoral():
    assert (
        classify_sector_fund_purity("HDFC Large Cap Fund", category="Large Cap", scheme_type="Equity")
        == "diversified_equity"
    )
