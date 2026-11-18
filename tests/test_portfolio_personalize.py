"""Portfolio headline personalization."""

from __future__ import annotations

from unittest.mock import patch

from ai_insight.common.sector_headline import sector_headline_phrase
from ai_insight.portfolio_insights.personalize import (
    append_personal_tail,
    fund_isins_from_row,
    format_fund_tail,
    personalize_card_headline,
    resolve_fund_display,
)


def test_sector_headline_phrase_banks():
    assert sector_headline_phrase("Banks") == "banking sector"


def test_sector_headline_pharma_default():
    phrase = sector_headline_phrase("Some Novel Sector")
    assert phrase.endswith(" sector")
    assert "some novel sector" in phrase


def test_fund_isins_from_row_list_only():
    assert fund_isins_from_row({"fund_isins": ["INF111", "INF222"]}) == ["INF111", "INF222"]
    assert fund_isins_from_row({"isin": ["INF111"]}) == ["INF111"]
    assert fund_isins_from_row({"fund_isins": None, "isin": None}) == []
    assert fund_isins_from_row({"isin": "INF0"}) == []


def test_append_personal_tail_one_fund(monkeypatch):
    monkeypatch.setattr(
        "ai_insight.portfolio_insights.personalize.resolve_fund_display",
        lambda isin: {"INF1": "hdfc large cap", "INF2": "kotak contra"}.get(isin, isin),
    )
    full, meta = append_personal_tail(
        "banking sector gained 5% week — credit, a tailwind for your", ["INF1"], seed="a"
    )
    assert full.startswith("banking sector gained 5% week")
    assert "hdfc large cap" in full
    assert " others" not in full
    assert " and one" not in full
    assert meta["other_count"] == 0


def test_append_personal_tail_three_funds(monkeypatch):
    monkeypatch.setattr(
        "ai_insight.portfolio_insights.personalize.resolve_fund_display",
        lambda isin: f"fund-{isin[-1]}",
    )
    full, meta = append_personal_tail("base headline in your", ["INF1", "INF2", "INF3"], seed="crn:Banks")
    assert meta["other_count"] == 2
    assert " others" in full


def test_format_fund_tail_counts():
    assert format_fund_tail("alpha fund", 0) == " alpha fund"
    assert "2 others" in format_fund_tail("alpha fund", 2)


def test_resolve_fund_display_uses_index(monkeypatch):
    monkeypatch.setattr("ai_insight.portfolio_insights.personalize._fetch_fund_short_name", lambda _isin: "")

    class Index:
        def fetch_fund_detail_from_api(self, isin: str, timeout: float = 12.0):
            if isin == "INF123":
                return {"identity": {"fund_short_name": "Parag Parikh Flexi Cap - Growth"}}
            return None

    monkeypatch.setattr("news_rag.fund_search.get_fund_index", lambda: Index())
    name = resolve_fund_display("INF123")
    assert name == "parag parikh flexi cap"


def test_personalize_sector_card():
    raw = {
        "sector_allocation": [
            {"sector": "Banks", "percentage": 10, "fund_isins": ["INF1", "INF2", "INF3", "INF4"]},
        ],
    }
    card = {
        "insight_id": "sector_index_insights",
        "headline": "banking sector gained 5% week — credit, a tailwind for your",
        "match_meta": {"sector": "Banks", "weight_pct": 10},
    }
    with patch("ai_insight.portfolio_insights.personalize.resolve_fund_display", return_value="hdfc large cap"):
        out = personalize_card_headline(card, raw, crn="CRN-x", match_key="Banks")
    assert out["headline_base"] == card["headline"]
    assert "hdfc large cap" in out["headline"]
    assert out["match_meta"]["personalization"]["other_count"] == 3


def test_personalize_skips_without_isins():
    card = {
        "insight_id": "holding_insights",
        "headline": "HDFC Bank gained 2% week — NPA",
        "match_meta": {"instrument_name": "HDFC Bank Ltd", "weight_pct": 1},
    }
    raw = {"top_holdings": [{"instrument_name": "HDFC Bank Ltd", "percentage": 1, "isin": None}]}
    out = personalize_card_headline(card, raw, crn="CRN-x", match_key="HDFC Bank Ltd")
    assert out["headline"] == card["headline"]