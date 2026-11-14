"""Ask market bridge wrappers (mocked upstream)."""

from ai_insight.data.ask_market_bridge import fetch_ask_market_records, fetch_gold_record, get_ask_market_snapshot


def test_fetch_gold_record_ok(monkeypatch):
    def fake_gold(**_kw):
        return {
            "available": True,
            "latest": {"price_24k_10g": 100_000, "as_of": "2026-11-14"},
            "returns": {"1M": {"pct": 2.5}},
        }

    monkeypatch.setattr("historical_data.gold_service.get_gold_snapshot", fake_gold)
    row = fetch_gold_record()
    assert row.entity == "Macro - Gold"
    assert row.status == "ok"
    assert row.value == 100_000
    assert row.change_pct == 2.5


def test_get_ask_market_snapshot_shape(monkeypatch):
    monkeypatch.setattr(
        "news_rag.insight.layer_tools.run_macro_series_tool",
        lambda _ctx: {"ok": True, "data": {"series": [{"series": "wti", "label": "WTI", "change_pct": 1.0}]}},
    )
    monkeypatch.setattr(
        "news_rag.insight.layer_tools.run_index_return_tool",
        lambda _ctx: {"ok": True, "data": {"return_pct": 3.0}},
    )
    monkeypatch.setattr(
        "historical_data.gold_service.get_gold_snapshot",
        lambda **_kw: {"available": True, "latest": {"price_24k_10g": 1}},
    )
    snap = get_ask_market_snapshot(window_days=14)
    assert snap["window_days"] == 14
    assert "wti" in snap["macro_series"]
    assert snap["index_returns"]["Nifty 50"]["return_pct"] == 3.0


def test_fetch_ask_market_records_includes_extras(monkeypatch):
    from ai_insight.data.base import NumericRecord

    monkeypatch.setattr(
        "ai_insight.data.ask_market_bridge.fetch_gold_record",
        lambda: NumericRecord("Macro - Gold", "d", 1.0, None, "x", "s", "ok"),
    )
    monkeypatch.setattr(
        "ai_insight.data.ask_market_bridge.get_ask_market_snapshot",
        lambda **_kw: {
            "macro_series": {
                "wti": {"change_pct": -0.5, "label": "WTI"},
                "us_10y_yield": {"change_pct": 0.2, "label": "US 10Y"},
            }
        },
    )
    names = [r.entity for r in fetch_ask_market_records()]
    assert "Macro - Gold" in names
    assert "Market - WTI Crude" in names