"""Market quotes return a status instead of raising."""

import time
from types import SimpleNamespace

from ai_insight.common.config import load_config
from ai_insight.common.market_data import get_fii_dii_today, get_nifty, get_usdinr
from ai_insight.data.base import FiiDiiSnapshot, FlowLeg


def _cfg(tmp_path):
    return load_config({"INSIGHTS_DATA_DIR": str(tmp_path), "INSIGHTS_MARKET_TIMEOUT_SEC": "2"})


def _quote(day, change=-0.61):
    return SimpleNamespace(status="ok", value=24500.5, change_pct=change, date=day, source="yfinance:^NSEI", detail="")


def test_nifty_ok_and_stale(tmp_path):
    ok = get_nifty("2026-11-16", fetch=lambda: _quote("2026-11-16"), config=_cfg(tmp_path))
    assert ok.status == "ok"
    assert ok.data["close"] == 24500.5
    assert ok.data["change_pct"] == -0.61

    stale = get_nifty("2026-11-16", fetch=lambda: _quote("2026-11-13"), config=_cfg(tmp_path))
    assert stale.status == "stale"
    assert stale.data["date"] == "2026-11-13"


def test_nifty_timeout_and_exception(tmp_path):
    def slow():
        time.sleep(1)
        return _quote("2026-11-16")

    timed = get_nifty("2026-11-16", fetch=slow, timeout=0.2, config=_cfg(tmp_path))
    assert timed.status == "error"
    assert "timed out" in timed.detail

    broken = get_nifty("2026-11-16", fetch=lambda: (_ for _ in ()).throw(RuntimeError("down")), config=_cfg(tmp_path))
    assert broken.status == "error"
    assert "down" in broken.detail


def test_fii_dii_date_and_partial(tmp_path):
    leg = FlowLeg("FII", 1, 2, -500)
    dii = FlowLeg("DII", 3, 1, 800)
    snapshot = FiiDiiSnapshot("13-Nov-2026", leg, dii, "nse", "ok")
    stale = get_fii_dii_today("2026-11-16", fetch=lambda: snapshot, config=_cfg(tmp_path))
    assert stale.status == "stale"
    assert stale.data["trade_date"] == "2026-11-13"
    assert stale.data["fii"]["net_inr_crore"] == -500

    fresh = FiiDiiSnapshot("2026-11-16", leg, dii, "nse", "ok")
    ok = get_fii_dii_today("2026-11-16", fetch=lambda: fresh, config=_cfg(tmp_path))
    assert ok.status == "ok"

    partial = FiiDiiSnapshot("16-Nov-2026", leg, None, "nse", "partial", "missing DII row")
    missing = get_fii_dii_today("2026-11-16", fetch=lambda: partial, config=_cfg(tmp_path))
    assert missing.status == "unavailable"


def test_usdinr_must_be_dated_on_the_trading_day(tmp_path):
    ok = get_usdinr("2026-11-16", fetch=lambda: _quote("2026-11-16"), config=_cfg(tmp_path))
    assert ok.status == "ok"
    old = get_usdinr("2026-11-16", fetch=lambda: _quote("2026-11-13"), config=_cfg(tmp_path))
    assert old.status == "stale"
    empty = SimpleNamespace(status="unavailable", value=None, change_pct=None, date="", source="yfinance:INR=X", detail="empty")
    unavailable = get_usdinr("2026-11-16", fetch=lambda: empty, config=_cfg(tmp_path))
    assert unavailable.status == "unavailable"
