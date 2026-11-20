"""Unit tests for new/ equity fund week pipeline."""

from __future__ import annotations

from datetime import date

import pytest

from new.compose_llm import (
    _facts_payload,
    _sector_themes_for_facts,
    _stock_entries,
    compose_fund_narrative,
)
from new.fund_by_isin import (
    fund_row_from_detail,
    is_equity_scheme_type,
    load_equity_fund_by_isin,
)
from new.router import EquityFundWeekRequest
from new.run import run_equity_fund_week_by_isin
from new.sector_clusters import SectorCluster
from new.sector_news import fetch_sector_cluster_news
from new.week_window import (
    EQUITY_WEEK_DAYS,
    filter_articles_to_week,
    strip_portfolio_pct_prose,
)
from new.equity_week_llm import equity_week_llm_kwargs
from new.nav_settled import nav_daily_week_settled
from new.stock_explain import clamp_why_paragraph, polish_why, scrub_recap_voice
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


def test_nav_daily_week_from_records():
    records = [
        {"nav_date": "2026-03-01", "nav_value": 99.0},
        {"nav_date": "2026-03-10", "nav_value": 100.0},
        {"nav_date": "2026-03-11", "nav_value": 100.5},
        {"nav_date": "2026-03-19", "nav_value": 101.0},
    ]
    pts = nav_daily_week_settled(records, as_of=__import__("datetime").date(2026, 3, 20))
    assert pts and pts[-1]["date"] == "2026-03-19"


def test_equity_week_defaults_to_haiku():
    kw = equity_week_llm_kwargs()
    assert kw["model_override"] == "claude-haiku-5-5"


def test_scrub_recap_voice_drops_article_meta():
    raw = "This mattered for your fund. The article does not explain the weekly drop."
    assert "article" not in scrub_recap_voice(raw).lower()
    polished = polish_why(raw)
    assert "article" not in polished.lower()


def test_clamp_why_keeps_full_sentences():
    blob = " ".join(f"Sentence {i} has enough words to count." for i in range(12))
    out = clamp_why_paragraph(blob, max_words=25)
    assert len(out.split()) <= 30
    assert out.endswith(".")


def test_stock_entries_splits_by_move():
    news = [
        {"instrument_name": "A Ltd", "move": "up", "why": "Good week.", "why_skip": False, "usable_news": True, "articles": [{}]},
        {"instrument_name": "B Ltd", "move": "down", "why": "Weak week.", "why_skip": False, "usable_news": True, "articles": [{}]},
    ]
    g, l = _stock_entries(news)
    assert len(g) == 1 and len(l) == 1


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
                    "why": (
                        "ICICI Bank rose as a court ruling eased leadership-linked legal worries, "
                        "while firmer deposit rates helped the bank gather savings from customers "
                        "through the week despite minor fee changes on some accounts."
                    ),
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
        },
        dry_run=True,
    )
    assert "ICICI" in narr["gainers"][0]["why"]
    assert narr.get("fund_summary")
    assert narr["losers"] == []
    assert "ABC" not in narr["insight"]
    assert narr["narrative_source"] == "dry_run"


def test_compose_dry_run_uses_holding_movers():
    narr = compose_fund_narrative(
        {
            "scheme_name": "Test Fund",
            "nav_1w_pct": 0.42,
            "gainers": [
                {"instrument_name": "State Bank of India", "change_1w_pct": 6.4, "impact_1w_pct": 0.2},
            ],
            "losers": [
                {"instrument_name": "Tech Mahindra Limited", "change_1w_pct": -2.9, "impact_1w_pct": -0.08},
            ],
            "stock_news": [],
            "attribution": {"summary_line": "Fund NAV moved +0.42% over the last week."},
        },
        dry_run=True,
    )
    assert len(narr["gainers"]) == 1 and narr["gainers"][0]["name"] == "State Bank of India"
    assert len(narr["losers"]) == 1
    assert "dry run" in narr["fund_summary"].lower()


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


def test_sector_themes_for_facts_payload():
    sector_news = [
        {
            "sector_key": "Banks",
            "side": "up",
            "trigger": "pair",
            "holding_names": ["SBI", "PNB"],
            "usable_news": True,
            "articles": [{"title": "Credit growth picks up", "snippet": "Banks lend more.", "url": "https://x"}],
        }
    ]
    themes = _sector_themes_for_facts(sector_news)
    assert themes[0]["has_news"] is True
    assert themes[0]["sector"] == "Banks"
    assert "Credit" in themes[0]["article_titles"][0]


def test_cushion_logic():
    from new.fund_context import cushion_funds

    funds = [
        FundRow("A", "Fund A", "large cap", 100, 50),
        FundRow("B", "Fund B", "mid cap", 100, 50),
    ]
    nav = {"A": -1.2, "B": 2.5}
    cush = cushion_funds(funds[0], nav, funds, -1.2)
    assert cush and cush[0]["scheme_name"] == "Fund B"


def test_is_equity_scheme_type():
    assert is_equity_scheme_type({"scheme_type": "Equity"})
    assert is_equity_scheme_type({"scheme_type": "equity"})
    assert not is_equity_scheme_type({"scheme_type": "Debt"})


def test_fund_row_from_detail():
    row = fund_row_from_detail(
        {
            "isin": "INF123456789",
            "fund_name": "Test Growth",
            "category": "Large Cap",
            "scheme_type": "Equity",
        }
    )
    assert row.isin == "INF123456789"
    assert row.scheme_name == "Test Growth"
    assert row.portfolio_pct == 0.0


def test_compose_omit_portfolio_facts_payload():
    payload = _facts_payload(
        {"scheme_name": "X", "nav_1w_pct": 1.0, "portfolio_pct": 12.0},
        [],
        [],
        omit_portfolio_pct=True,
    )
    assert "portfolio_pct_of_book" not in payload


def test_strip_portfolio_pct_prose():
    raw = "ABC Fund, which makes up 12.5% of your portfolio, gained slightly this week."
    out = strip_portfolio_pct_prose(raw)
    assert "portfolio" not in out.lower()
    assert "ABC Fund" in out


def test_equity_week_request_validator():
    with pytest.raises(ValueError):
        EquityFundWeekRequest(crn="CRN-abc", isin="INF123456789")
    with pytest.raises(ValueError):
        EquityFundWeekRequest()
    ok = EquityFundWeekRequest(isin="INF123456789")
    assert ok.isin == "INF123456789"


def test_run_by_isin_not_equity(monkeypatch):
    def fake_detail(_isin: str):
        return {"isin": "INF123456789", "fund_name": "Liquid", "scheme_type": "Debt", "category": "Liquid"}

    monkeypatch.setattr("new.fund_by_isin.fetch_fund_detail_for_week", fake_detail)
    out = run_equity_fund_week_by_isin("INF123456789")
    assert out["status"] == "not_equity"


def test_load_equity_fund_by_isin_ok(monkeypatch):
    def fake_detail(_isin: str):
        return {
            "isin": "INF123456789",
            "fund_name": "Bluechip",
            "scheme_type": "Equity",
            "category": "Large Cap",
        }

    monkeypatch.setattr("new.fund_by_isin.fetch_fund_detail_for_week", fake_detail)
    fund, meta = load_equity_fund_by_isin("INF123456789")
    assert fund.scheme_name == "Bluechip"
    assert meta["mode"] == "isin"


def test_filter_articles_to_week():
    window = ("2026-11-10T00:00:00+05:30", "2026-11-17T23:59:59+05:30")
    inside = [{"published_at": "2026-11-15T10:00:00+05:30", "title": "ok"}]
    outside = [{"published_at": "2026-11-01T10:00:00+05:30", "title": "old"}]
    kept = filter_articles_to_week(inside + outside, window)
    assert len(kept) == 1
    assert kept[0]["title"] == "ok"


def test_sector_news_no_extended_window(monkeypatch):
    calls: list[int] = []

    def fake_layered(*, window_days: int, **kwargs):
        del kwargs
        calls.append(window_days)
        return {"ok": True, "data": {"articles": []}}

    monkeypatch.setattr("news_rag.tools.run_layered_news", fake_layered)
    cluster = SectorCluster(
        sector_key="Banks",
        side="up",
        holdings=[{"instrument_name": "HDFC Bank", "impact_1w_pct": 0.2}],
        trigger="pair",
    )
    out = fetch_sector_cluster_news(
        cluster,
        fund_name="Test Fund",
        window_days=EQUITY_WEEK_DAYS,
        allow_extended_window=False,
    )
    assert out["window_days_used"] == EQUITY_WEEK_DAYS
    assert calls == [EQUITY_WEEK_DAYS]


def test_fund_context_uses_week_window(monkeypatch):
    captured: dict[str, int] = {}

    def fake_movers(*args, **kwargs):
        captured["window_days"] = kwargs.get("window_days")
        return []

    def fake_sector(*args, **kwargs):
        captured["sector_window"] = kwargs.get("window_days")
        captured["allow_ext"] = kwargs.get("allow_extended_window")
        return []

    monkeypatch.setattr("new.fund_context.news_for_movers", fake_movers)
    monkeypatch.setattr("new.fund_context.news_for_sector_clusters", fake_sector)
    class _Idx:
        def fetch_fund_detail_from_api(self, _isin: str):
            return {}

    monkeypatch.setattr("new.fund_context.get_fund_index", lambda: _Idx())
    monkeypatch.setattr("new.fund_context.fetch_raw_nav_history", lambda _s: [])
    monkeypatch.setattr("new.fund_context.lookup_instrument", lambda _n: None)

    from new.fund_context import build_fund_facts

    fund = FundRow("INF1", "F", "large cap", 0, 0)
    build_fund_facts(fund, [fund], {"INF1": 0.1}, fetch_news=True, dry_run=False)
    assert captured["window_days"] == EQUITY_WEEK_DAYS
    assert captured["sector_window"] == EQUITY_WEEK_DAYS
    assert captured["allow_ext"] is False