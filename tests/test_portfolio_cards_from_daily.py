"""Portfolio cards load from market / holding daily JSON."""

from ai_insight.common.market_daily_store import save_market_daily
from ai_insight.holding_insights.holding_stock_insights_store import save_holding_stock_insights
from ai_insight.portfolio_insights.cards import load_common_cards
from ai_insight.portfolio_insights.catalog import readiness
from ai_insight.portfolio_insights.compose import compose_portfolio_insights


def test_load_common_cards_from_market_daily(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTS_DATA_DIR", str(tmp_path))
    day = "2026-11-18"
    save_market_daily(
        day,
        {
            "trading_date": day,
            "generated_at": "2026-11-18T12:00:00+05:30",
            "common": [
                {
                    "insight_id": "market_driver_digest",
                    "status": "ok",
                    "headline": "Market",
                    "body": "Body",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "articles": [],
                }
            ],
            "sectors": [{"names": ["Banks"], "status": "ok", "headline": "h", "body": "b", "articles": []}],
        },
    )
    cards = load_common_cards(day, 3)
    assert cards[0]["section"] == "market_driver_digest"
    assert cards[0]["headline"] == "Market"


def test_compose_uses_daily_stores(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTS_DATA_DIR", str(tmp_path))
    day = "2026-11-18"
    from ai_insight.common.schemas import Chip, Envelope, InsightBundle, Meta, Viz
    from ai_insight.common.store import save, save_bundle

    for name in ("market_driver_digest", "fii_dii_flow_narrative", "sector_leaderboard"):
        save(
            Envelope(
                insight_id=name,
                trading_date=day,
                as_of_ist="2026-11-18T12:00:00+05:30",
                status="ok",
                headline=name,
                body="b",
                chips=[Chip(label="X", value="1", tone="neutral")],
                viz=Viz(type="none"),
                meta=Meta(),
            ),
            root=tmp_path,
        )
    item = Envelope(
        insight_id="sector_index_insights",
        trading_date=day,
        as_of_ist="2026-11-18T12:00:00+05:30",
        status="ok",
        headline="Banks",
        body="bank body",
        chips=[],
        viz=Viz(type="none"),
        facts={"kind": "sector_index", "catalog_sectors": ["Banks"], "sectors": ["Banks"]},
        meta=Meta(),
    )
    save_bundle(
        InsightBundle(insight_id="sector_index_insights", trading_date=day, as_of_ist="2026-11-18T12:00:00+05:30", status="ok", items=[item]),
        root=tmp_path,
    )
    from ai_insight.common.market_daily_store import build_market_daily_snapshot

    save_market_daily(day, build_market_daily_snapshot(day))
    save_holding_stock_insights(
        day,
        {
            "trading_date": day,
            "holdings": [
                {
                    "stock_id": "HDFCBANK",
                    "stock_name": "HDFC Bank",
                    "status": "ok",
                    "headline": "HDFC headline",
                    "insight": "Line one.",
                }
            ],
            "counts": {"ok": 1},
        },
    )

    portfolio = {
        "top_holdings": [{"instrument_name": "HDFC Bank Ltd", "percentage": 5.0}],
        "sector_allocation": [{"sector": "Banks", "percentage": 10.0}],
    }

    import ai_insight.portfolio_insights.compose as compose_mod

    monkeypatch.setattr(compose_mod, "fetch_portfolio", lambda _crn: portfolio)
    out = compose_portfolio_insights("CRN-test", day)
    assert out["status"] == "ok"
    assert out["common"]
    assert out["sectors"]
    assert out["holdings"]