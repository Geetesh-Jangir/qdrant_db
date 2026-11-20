"""Unit tests for new/ equity fund week pipeline."""

from __future__ import annotations

from datetime import date

import pytest

from new.compose_llm import compose_fund_narrative
from new.stock_explain import clamp_why_paragraph
from new.fund_context import attribution_summary, holding_impact_1w, select_drivers, split_gainers_losers
from new.news_filter import filter_usable_articles, score_article
from new.news_filter import merge_article_pool
from new.nav_settled import nav_change_1w_settled, settled_nav_records
from new.portfolio_equity import FundRow, load_equity_holdings
from new.security_master import load_master_index, lookup_master, normalize_name


def test_settled_nav_drops_today():
    today = date(2026, 3, 20)
    records = [
        {"nav_date": "2026-03-01", "nav_value": 99.0},
        {"nav_date": "2026-03-10", "nav_value": 100.0},
        {"nav_date": "2026-03-19", "nav_value": 101.0},
        {"nav_date": "2026-03-20", "nav_value": 102.0},
    ]
    trimmed = settled_nav_records(records, as_of=today)
    assert trimmed[-1]["nav_date"] == "2026-03-19"
    stats = nav_change_1w_settled(records, as_of=today)
    assert stats is not None
    assert stats["end_date"] == "2026-03-19"


def test_filter_rejects_breadcrumb_and_roundup():
    breadcrumb = {
        "title": "Max Healthcare rises on expansion",
        "scraped_text": "Home / Markets / News Listen to this article. Max Healthcare expanded beds.",
        "max_impact": 3,
        "direction": "positive",
    }
    assert score_article(breadcrumb, "Max Healthcare Institute Limited", "up") < 0

    roundup = {
        "title": "Hospital stocks in focus: Max, Aster, Fortis at new highs",
        "scraped_text": "Several hospital names traded higher as " + ("demand rose " * 35),
        "max_impact": 3,
        "direction": "positive",
    }
    assert score_article(roundup, "Max Healthcare Institute Limited", "up") < 0

    nse_list = {
        "title": "NSE 500 movers: Infosys and more NSE stocks",
        "scraped_text": "Infosys led gainers while " + ("markets moved " * 35),
        "max_impact": 2,
        "direction": "positive",
    }
    assert score_article(nse_list, "Infosys Limited", "up") < 0


def test_clamp_why_keeps_full_sentences():
    blob = " ".join(f"Sentence {i} has enough words to count." for i in range(12))
    out = clamp_why_paragraph(blob, max_words=25)
    assert len(out.split()) <= 30
    assert out.endswith(".")


def test_compose_structured_narrative():
    narr = compose_fund_narrative(
        {
            "scheme_name": "Test Fund",
            "nav_1w_pct": 0.42,
            "portfolio_pct": 12.5,
            "stock_news": [
                {
                    "instrument_name": "ICICI Bank Limited",
                    "move": "up",
                    "change_1w_pct": 1.5,
                    "why": "Strong quarterly profit growth from retail and corporate lending.",
                    "why_skip": False,
                    "usable_news": True,
                    "articles": [{"title": "ICICI results"}],
                },
                {
                    "instrument_name": "ABC Ltd",
                    "move": "down",
                    "change_1w_pct": -2.1,
                    "why_skip": True,
                    "usable_news": False,
                    "articles": [],
                },
            ],
            "cushioned_by": [],
        }
    )
    assert narr["gainers"][0]["why"].startswith("Strong quarterly")
    assert narr["losers"] == []
    assert "also weighed" not in narr["insight"]
    assert "ABC" not in narr["insight"]
    assert "Home / Markets" not in narr["insight"]
    assert "What held the fund back" not in narr["insight"]
    assert narr["narrative_source"] == "stitched"


def test_news_filter_drops_weak():
    row = {
        "title": "Market wrap",
        "scraped_text": "Nifty ended flat.",
        "max_impact": 0,
        "direction": "neutral",
    }
    assert score_article(row, "HDFC Bank Limited", "up") < 0
    good = {
        "title": "HDFC Bank profit rises on strong loan growth",
        "scraped_text": "HDFC Bank reported " + ("strong earnings " * 40),
        "max_impact": 2,
        "direction": "positive",
        "_rrf_score": 0.02,
    }
    picked = filter_usable_articles("HDFC Bank Limited", "up", [row, good], limit=1)
    assert len(picked) == 1 and picked[0]["title"] == good["title"]


def test_merge_pool_prefers_stronger_vector():
    list_a = [{"url": "https://a/1", "title": "A", "max_impact": 2, "score": 0.3}]
    list_b = [{"url": "https://a/1", "title": "A", "max_impact": 2, "score": 0.8}, {"url": "https://b/2", "title": "B"}]
    merged = merge_article_pool(list_a, list_b)
    by_url = {r["url"]: r for r in merged}
    assert by_url["https://a/1"]["score"] == 0.8


def test_holding_impact_and_attribution():
    assert holding_impact_1w(5.0, 2.0) == 0.1
    rows = [
        {"instrument_name": "A", "percentage": 10, "change_1w_pct": 2.0, "impact_1w_pct": 0.2},
        {"instrument_name": "B", "percentage": 8, "change_1w_pct": -1.0, "impact_1w_pct": -0.08},
    ]
    attr = attribution_summary(rows, 0.12)
    assert attr["explained_1w_pct"] == 0.12
    assert attr["total_stock_impact_1w_pct"] == 0.12
    assert attr["justification_pct"] == 100.0
    assert "0.12%" in attr["summary_line"] or "0.12" in attr["summary_line"]
    g, l = split_gainers_losers(rows)
    assert g[0]["instrument_name"] == "A"
    assert l[0]["instrument_name"] == "B"


def test_select_drivers_sign():
    gainers = [
        {"instrument_name": "A", "percentage": 5, "change_1w_pct": 2.0, "impact_1w_pct": 0.1},
    ]
    losers = [
        {"instrument_name": "B", "percentage": 4, "change_1w_pct": -1.5, "impact_1w_pct": -0.06},
    ]
    pos = select_drivers(gainers, losers, "positive")
    assert len(pos) == 1 and pos[0]["instrument_name"] == "A"
    neg = select_drivers(gainers, losers, "negative")
    assert len(neg) == 1 and neg[0]["instrument_name"] == "B"


def test_top_five_cap():
    rows = [
        {"instrument_name": f"G{i}", "impact_1w_pct": 0.1 - i * 0.01}
        for i in range(8)
    ]
    rows += [{"instrument_name": f"L{i}", "impact_1w_pct": -0.1 + i * 0.01} for i in range(8)]
    g, l = split_gainers_losers(rows, limit=5)
    assert len(g) == 5 and len(l) == 5
    attr = attribution_summary(g + l, 1.0)
    assert attr["explained_1w_pct"] == round(sum(r["impact_1w_pct"] for r in g + l), 3)


def test_master_lookup():
    items = [
        {"companyName": "tata steel limited", "symbol": "TATASTEEL", "scripCode": "500470", "status": "active"},
    ]
    by_norm = load_master_index(items)
    row = lookup_master(by_norm, "Tata Steel Ltd")
    assert row is not None
    assert row["symbol"] == "TATASTEEL"


def test_equity_filter_from_workspace(monkeypatch):
    def fake_fetch(_crn: str):
        return {"data": {}}

    def fake_norm(_raw):
        return {
            "summary": {"aum_inr": 1000.0},
            "holdings": [
                {"isin": "INF111", "scheme_name": "Liquid", "scheme_category": "liquid", "aum_inr": 100},
                {"isin": "INF222", "scheme_name": "Bluechip", "scheme_category": "large cap", "aum_inr": 900},
            ],
        }

    monkeypatch.setattr("new.portfolio_equity.fetch_workspace_raw", fake_fetch)
    monkeypatch.setattr("new.portfolio_equity.normalize_workspace", fake_norm)
    rows, meta = load_equity_holdings("CRN-test123", top_n=5)
    assert len(rows) == 1
    assert rows[0].isin == "INF222"
    assert rows[0].portfolio_pct == 90.0
    assert meta["equity_fund_count"] == 1


def test_cushion_logic():
    from new.fund_context import cushion_funds

    funds = [
        FundRow("A", "Fund A", "large cap", 100, 50),
        FundRow("B", "Fund B", "mid cap", 100, 50),
    ]
    nav = {"A": -1.2, "B": 2.5}
    cush = cushion_funds(funds[0], nav, funds, -1.2)
    assert cush and cush[0]["scheme_name"] == "Fund B"