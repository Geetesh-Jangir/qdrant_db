"""Market daily JSON snapshot for portfolio insights."""

from ai_insight.common.market_daily_store import build_market_daily_snapshot, load_market_daily, save_market_daily
from ai_insight.common.schemas import Chip, Envelope, InsightBundle, Meta, Source, Viz
from ai_insight.common.store import save, save_bundle
from ai_insight.portfolio_insights.catalog import readiness


def _env(insight_id: str, trading_date: str, **facts) -> Envelope:
    return Envelope(
        insight_id=insight_id,
        trading_date=trading_date,
        as_of_ist="2026-11-18T12:00:00+05:30",
        status="ok",
        headline="Headline",
        body="Insight text.",
        chips=[Chip(label="X", value="1", tone="neutral")],
        viz=Viz(type="none"),
        sources=[Source(url="https://example.com/n", published_at="2026-11-17T04:00:00Z")],
        facts=facts,
        meta=Meta(usage={"input_tokens": 10, "output_tokens": 5}),
    )


def test_market_daily_snapshot_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTS_DATA_DIR", str(tmp_path))
    day = "2026-11-18"
    for name in ("market_driver_digest", "fii_dii_flow_narrative", "sector_leaderboard"):
        save(_env(name, day), root=tmp_path)
    sector = _env(
        "sector_index_insights",
        day,
        kind="sector_index",
        catalog_sectors=["Banks"],
        sectors=["Banks"],
        index="Nifty Bank",
    )
    bundle = InsightBundle(
        insight_id="sector_index_insights",
        trading_date=day,
        as_of_ist="2026-11-18T12:00:00+05:30",
        status="ok",
        items=[sector],
    )
    save_bundle(bundle, root=tmp_path)

    snap = build_market_daily_snapshot(day)
    assert len(snap["common"]) == 3
    assert snap["common"][0]["articles"][0]["url"] == "https://example.com/n"
    assert snap["sectors"][0]["names"] == ["Banks", "Nifty Bank"]
    save_market_daily(day, snap)
    loaded = load_market_daily(day)
    assert loaded is not None
    assert loaded["sectors"][0]["input_tokens"] == 10


def test_readiness_requires_market_daily(tmp_path, monkeypatch):
    monkeypatch.setenv("INSIGHTS_DATA_DIR", str(tmp_path))
    day = "2026-11-18"
    save(_env("market_driver_digest", day), root=tmp_path)
    result = readiness(day)
    assert "market:daily_snapshot" in result.missing