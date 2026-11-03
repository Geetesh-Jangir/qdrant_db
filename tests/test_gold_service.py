"""Gold price series: 24K per 10g, daily windows, month-end history, silver stub."""

from historical_data.gold_service import (
    get_gold_snapshot,
    get_silver_snapshot,
    snapshot_from_payload,
)
from news_rag.insight.capabilities.catalog import validate_capability_args
from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.plan_validate import ensure_silver_news_only

SAMPLE = {
    "data": {
        "monthlyHistory": [
            {"date": "2023-09-30", "pricePer10g": 60000, "pricePerGram": 6000},
            {"date": "2025-09-30", "pricePer10g": 100000},
            {"date": "2026-09-30", "pricePer10g": 110000},
        ],
        "recentDays": [
            {"date": "2026-10-26", "pricePer10g": 120000},
            {"date": "2026-11-02", "pricePer10g": 121000},
        ],
        "latestEndOfDay": {"date": "2026-11-02", "pricePer10g": 121000},
        "todayPrice": {
            "dateText": "3 Nov 2026",
            "price24kPer10g": 122000,
            "price22kPer10g": 111000,
            "price24kPerGram": 12200,
        },
    }
}


def test_snapshot_is_24k_per_10g_and_windows():
    snap = snapshot_from_payload(SAMPLE, windows=["1D", "1W", "1Y", "3Y"], history_months=2)
    assert snap["unit"] == "INR per 10g (24K)"
    assert snap["latest"]["price_24k_10g"] == 122000
    assert snap["latest"]["as_of"] == "2026-11-03"
    assert snap["latest"]["source_basis"] == "live"
    assert set(snap["latest"]) == {"price_24k_10g", "as_of", "source_basis"}
    day = snap["returns"]["1D"]
    assert day["from_date"] == "2026-11-02"
    assert day["approx"] is False
    assert day["pct"] == round((122000 - 121000) / 121000 * 100, 2)
    year = snap["returns"]["1Y"]
    assert year["basis"] == "month_end"
    assert year["approx"] is True
    assert year["from_date"] == "2025-09-30"
    three = snap["returns"]["3Y"]
    assert three["from_date"] == "2023-09-30"
    assert three["approx"] is True
    assert [row["date"] for row in snap["monthly"]] == ["2025-09-30", "2026-09-30"]
    assert snap["daily"][-1]["date"] == "2026-11-03"


def test_short_window_omits_monthly_history():
    snap = snapshot_from_payload(SAMPLE, windows=["1W"])
    assert "monthly" not in snap
    assert snap["daily"]


def test_stale_cache_when_fetch_fails(monkeypatch):
    import historical_data.gold_service as svc

    svc._CACHE["payload"] = SAMPLE
    svc._CACHE["at"] = 0
    monkeypatch.setattr(svc, "_fetch", lambda: None)
    snap = get_gold_snapshot(windows=["1M"])
    assert snap["available"] is True
    assert snap["stale"] is True


def test_silver_stub_is_news_only():
    stub = get_silver_snapshot()
    assert stub["available"] is False
    assert stub["route"] == "news_only"


def test_market_snapshot_accepts_gold_windows():
    args = validate_capability_args(
        "get_market_snapshot",
        {
            "modules": ["metals_spot"],
            "metal": "gold",
            "windows": ["1Y"],
            "history_months": 18,
        },
    )
    assert args["metal"] == "gold"
    assert args["windows"] == ["1Y"]
    assert args["history_months"] == 18
    dropped = validate_capability_args(
        "get_market_snapshot",
        {"modules": ["macro_series"], "series": ["crude", "silver", "gold"]},
    )
    assert "silver" not in dropped["series"]
    assert "gold" in dropped["series"]


def test_silver_price_tool_becomes_news():
    plan = ExecutionPlan(
        answer_mode="DATA_ONLY",
        window_days=14,
        tool_calls=[
            ToolCall(
                tool="get_market_snapshot",
                arguments={"modules": ["metals_spot"], "metal": "silver"},
                wave=1,
            )
        ],
    )
    plan = ensure_silver_news_only(plan)
    tools = [call.tool for call in plan.tool_calls]
    assert "get_market_snapshot" not in tools
    news = next(call for call in plan.tool_calls if call.tool == "search_financial_news")
    assert news.arguments["topics"] == ["silver"]
    assert plan.answer_mode.value == "NEWS_ONLY"


def test_macro_series_gold_uses_india_series(monkeypatch):
    import historical_data.gold_service as svc

    monkeypatch.setattr(
        svc,
        "get_gold_snapshot",
        lambda windows=None, history_months=None: {
            "unit": "INR per 10g (24K)",
            "returns": {"1M": {"pct": 1.5, "approx": False}},
        },
    )
    from news_rag.insight.layer_tools import run_macro_series_tool

    out = run_macro_series_tool({"series": ["gold"], "window_days": 30})
    row = out["data"]["series"][0]
    assert row["series"] == "gold"
    assert row["change_pct"] == 1.5
    assert row["label"].startswith("24K")
