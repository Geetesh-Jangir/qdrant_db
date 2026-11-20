"""FII flow DATASETS loaders."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from types import SimpleNamespace

from ai_insight.common.config import load_config
from ai_insight.common.flows import FlowDay
from ai_insight.fii_dii_flow_narrative.flow_datasets import build_flow_datasets, _flow_with_market


def _ctx(tmp_path):
    cfg = replace(load_config(), data_dir=tmp_path / "ai_insights")
    (cfg.data_dir / "_data").mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(trading_date=date(2026, 11, 19), config=cfg)


def test_flow_with_market_joins_on_date():
    daily = [
        {"date": "2026-11-18", "fii_net_crore": 100.0, "dii_net_crore": -50.0},
        {"date": "2026-11-19", "fii_net_crore": 200.0, "dii_net_crore": -80.0},
    ]
    aligned = [
        {"date": "2026-11-18", "nifty_pct": 0.5, "nifty_close": 25000.0},
        {"date": "2026-11-19", "nifty_pct": -0.2, "nifty_close": 24950.0},
    ]
    rows = _flow_with_market(daily, aligned)
    assert rows[-1]["nifty_pct"] == -0.2
    assert rows[-1]["fii_net_crore"] == 200.0


def test_fii_dii_daily_uses_full_history_not_tail(tmp_path):
    ctx = _ctx(tmp_path)
    history = [FlowDay(f"2026-11-{10 + i:02d}", float(i), -float(i), {}, {}, "") for i in range(15)]
    pack = build_flow_datasets(ctx, history, {"aligned_market_flows": [], "flow_lagged": False})
    assert len(pack["fii_dii_net_history"]) == 15


def test_flow_index_date_context_pairs_dates(tmp_path):
    ctx = _ctx(tmp_path)
    history = [
        FlowDay("2026-11-18", 100.0, -50.0, {}, {}, ""),
        FlowDay("2026-11-19", 200.0, -80.0, {}, {}, ""),
    ]
    market = {
        "flow_trade_date": "2026-11-18",
        "flow_lagged": True,
        "trading_date": "2026-11-19",
        "nifty_change_pct": 0.87,
        "aligned_market_flows": [
            {"date": "2026-11-18", "nifty_pct": -0.63},
            {"date": "2026-11-19", "nifty_pct": 0.87},
        ],
    }
    pack = build_flow_datasets(ctx, history, market)
    dc = pack["flow_index_date_context"]
    assert dc["card_trading_date"] == "2026-11-19"
    assert dc["flow_trade_date"] == "2026-11-18"
    assert dc["nifty_on_flow_trade_date"]["nifty_change_pct"] == -0.63
    assert dc["nifty_on_card_trading_date"]["nifty_change_pct"] == 0.87


def test_build_flow_datasets_includes_daily_and_limitations(tmp_path):
    ctx = _ctx(tmp_path)
    history = [
        FlowDay("2026-11-18", 100.0, -50.0, {}, {}, ""),
        FlowDay("2026-11-19", 200.0, -80.0, {}, {}, ""),
    ]
    market = {
        "aligned_market_flows": [{"date": "2026-11-19", "nifty_pct": 0.1}],
        "flow_lagged": False,
    }
    pack = build_flow_datasets(ctx, history, market)
    assert len(pack["fii_dii_daily"]) == 2
    assert "flow_aggregates" in pack
    assert "flow_with_market" in pack
    assert pack["fii_dii_daily"][-1]["fii_net_crore"] == 200.0
    assert isinstance(pack["data_limitations"], list)
    assert "synthesis_hints" in pack
    assert pack["synthesis_hints"]["flow_history"]["sessions"] == 2
    tensions = pack["synthesis_hints"].get("suggested_tensions") or {}
    assert "fii_dii_offset" in tensions
    assert "net_5d_fii_crore" in tensions["fii_dii_offset"]


def test_flow_history_highlights_counts_sessions():
    from ai_insight.fii_dii_flow_narrative.flow_datasets import _flow_history_highlights

    daily = [
        {"date": "2026-11-01", "fii_net_crore": 100.0, "dii_net_crore": -10.0},
        {"date": "2026-11-02", "fii_net_crore": -50.0, "dii_net_crore": 20.0},
    ]
    highlights = _flow_history_highlights(daily, {"net_5d_fii": 50}, {"fii_streak_days": 1})
    assert highlights["fii_net_buy_sessions"] == 1
    assert highlights["fii_net_sell_sessions"] == 1
    assert highlights["sessions_dii_offset_fii"] == 2