"""News themes keep a weight and a sector, including a holding outside the top five."""

from news_rag.insight.fund_display import strip_missing_data_caveats
from news_rag.insight.insight_links import build_insight_links


def test_a_holding_outside_the_top_five_still_gets_weight_and_sector(monkeypatch):
    def fake_resolve(_name):
        return (
            {
                "holdings": {
                    "Reliance Industries Ltd.": {"percentage": 4.21, "industry": "Petroleum Products"},
                }
            },
            [],
            [],
        )

    monkeypatch.setattr("news_rag.fund_search.resolve_fund_for_query", fake_resolve)
    links = build_insight_links(
        {
            "portfolio:hdfc": {
                "fund_name": "HDFC Large Cap Fund - Growth",
                "holdings": [
                    {"name": "Titan Company Ltd.", "weight_pct": 5.06964416331026, "sector": "Consumer Durables"},
                ],
                "sectors": [
                    {"sector": "Pharmaceuticals & Biotechnology", "weight_pct": 8.45},
                ],
            }
        },
        {
            "holdings": [
                {"theme": "Titan Company Ltd.", "title": "Titan reports 25% revenue growth in Q2"},
                {"theme": "Reliance Industries Ltd.", "title": "Jio IPO may be valued at Rs 11 lakh crore"},
            ],
            "sectors": [
                {"theme": "Pharmaceuticals & Biotechnology", "title": "Sun Pharma plans a Rs 10,000 crore funding"},
            ],
            "macro": [
                {"theme": "crude oil", "title": "Average India oil prices hit a multi-year high"},
            ],
        },
    )
    by_name = {row["name"]: row for row in links}
    assert by_name["Titan Company Ltd."]["weight_pct"] == 5.07
    assert by_name["Titan Company Ltd."]["sector"] == "Consumer Durables"
    assert by_name["Reliance Industries Ltd."]["weight_pct"] == 4.21
    assert by_name["Reliance Industries Ltd."]["sector"] == "Petroleum Products"
    assert by_name["Pharmaceuticals & Biotechnology"]["kind"] == "sector"
    assert by_name["Pharmaceuticals & Biotechnology"]["weight_pct"] == 8.45
    assert by_name["crude oil"]["kind"] == "macro"


def test_each_holding_keeps_the_article_text_not_only_one_headline():
    links = build_insight_links(
        {
            "portfolio:hdfc": {
                "holdings": [
                    {"name": "Titan Company Ltd.", "weight_pct": 5.07, "sector": "Consumer Durables"},
                ],
            }
        },
        {
            "holdings": [
                {
                    "theme": "Titan Company Ltd.",
                    "title": "Titan reports 25% revenue growth",
                    "summary": "Titan reported 25% revenue growth in Q2FY27 and jewellery sales rose 21%.",
                },
                {
                    "theme": "Titan Company Ltd.",
                    "title": "Titan Q2 sales miss",
                    "summary": "Jewellery demand stayed firm even though the reported sales figure missed the street estimate.",
                },
                {
                    "theme": "Titan Company Ltd.",
                    "title": "Stocks to watch",
                    "summary": "Titan is among the stocks traders are watching after the quarterly update.",
                },
            ],
        },
    )
    points = links[0]["points"]
    assert len(points) == 3
    assert "jewellery sales rose 21%" in points[0]
    assert "missed the street estimate" in points[1]


def test_grouped_news_keeps_the_article_body():
    from news_rag.insight.capabilities.executor import _group_layered_articles

    grouped = _group_layered_articles([
        {
            "title": "Titan reports 25% revenue growth - Business Standard",
            "text": "",
            "summary": "",
            "scraped_text": "Titan reported 25% revenue growth in Q2FY27 and jewellery sales rose 21%.",
            "url": "https://example.com/titan",
            "_news_layer": "holding",
            "_news_source_label": "Titan Company Ltd.",
        }
    ])
    article = grouped["holdings"]["Titan Company Ltd."][0]
    assert "jewellery sales rose 21%" in article["summary"]
    assert article["text"] == article["summary"]


def test_a_top_five_apology_is_removed():
    prose = (
        "Reliance (not a top-five holding in the fund data): the fund's own data does not show a Reliance weight, "
        "so its direct effect on this fund cannot be measured here.\n"
        "**Titan · 5.07% · Consumer Durables**\n"
        "Q2 revenue rose 25%."
    )
    cleaned = strip_missing_data_caveats(prose)
    assert "top-five" not in cleaned
    assert "cannot be measured" not in cleaned
    assert "Titan" in cleaned


def test_overview_fund_facts_are_a_short_table():
    from news_rag.insight.fund_display import build_fund_display_tables

    tables = build_fund_display_tables({
        "fund:hdfc": {
            "snapshot": {
                "fund_name": "HDFC Large Cap Fund - Growth",
                "category": "large cap",
                "nav": 1292.0,
                "nav_date": "2026-10-28",
                "benchmark": "NIFTY 100 - TRI",
                "returns": {"1M": -1.94},
                "expense_ratio": {"regular": 1.58, "as_on_date": "2026-09-30"},
                "aum": 37293.95,
                "exit_load_summary": "Exit load is 1% if you leave within 1 year, and nothing after 1 year.",
                "high_52w": 1465.43,
                "low_52w": 1250.22,
            }
        }
    })
    facts = tables["fund_facts_table"]
    assert "Expense ratio" in facts
    assert "1.58%" in facts
    assert "37,293.95" in facts
    assert "52-week" not in facts

