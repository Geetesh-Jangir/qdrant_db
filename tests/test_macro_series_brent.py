"""Macro series uses Brent (BZ=F) for default crude."""

from news_rag.insight.layer_tools import run_macro_series_tool
from news_rag.insight.slot_router import _macro_series_for_driver


def test_default_crude_series_is_brent_ticker():
    res = run_macro_series_tool({"series": ["crude"], "window_days": 30})
    assert res["ok"]
    row = res["data"]["series"][0]
    assert row["yfinance_ticker"] == "BZ=F"
    assert "Brent" in row["label"]
    assert isinstance(row["change_pct"], (int, float))


def test_wti_series_uses_cl():
    res = run_macro_series_tool({"series": ["wti"], "window_days": 7})
    assert res["ok"]
    assert res["data"]["series"][0]["yfinance_ticker"] == "CL=F"


def test_slot_router_wti_in_question():
    assert _macro_series_for_driver("crude_oil", "why is WTI rising?") == ["wti"]
