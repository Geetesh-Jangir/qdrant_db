"""NAV-history returns for any period, including a fund that is too new."""

from datetime import datetime, timedelta

from news_rag.insight.capabilities.catalog import validate_capability_args
from news_rag.insight.capabilities.executor import _capability_cache_key, _return_slice_covers
from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
from news_rag.insight.planner_policy import finalize_planner_plan
from news_rag.insight.return_windows import returns_for_windows, window_to_days


def _history(start: str, days: int) -> list[dict]:
    base = datetime.strptime(start, "%Y-%m-%d")
    rows = []
    for offset in range(days):
        day = base + timedelta(days=offset)
        rows.append({"nav_date": day.strftime("%Y-%m-%d"), "nav_value": 100 + offset * 0.05})
    return rows


def test_any_period_code_is_kept():
    assert window_to_days("8M") == 240
    assert window_to_days("2M") == 60
    assert window_to_days("14D") == 14
    assert window_to_days("1Y") == 365
    args = validate_capability_args(
        "get_fund_data",
        {"modules": ["snapshot"], "windows": ["6M", "1Y", "8M", "YTD", "nope"]},
    )
    assert args["windows"] == ["6M", "1Y", "8M", "YTD"]


def test_one_year_is_not_served_from_the_one_month_cache():
    month = _capability_cache_key("get_fund_data", "Bandhan", {"modules": ["snapshot"], "windows": ["1M"]}, {})
    year = _capability_cache_key("get_fund_data", "Bandhan", {"modules": ["snapshot"], "windows": ["1Y"]}, {})
    assert month != year
    remembered = {"snapshot": {"returns": {"1M": -0.96}}}
    assert _return_slice_covers("get_fund_data", {"windows": ["1Y"]}, remembered) is False
    assert _return_slice_covers("get_fund_data", {"windows": ["1M"]}, remembered) is True


def test_nav_history_fills_one_year_and_six_months(monkeypatch):
    monkeypatch.setattr(
        "historical_data.nav_service.fetch_raw_nav_history",
        lambda isin, use_cache=True: _history("2024-01-01", 800),
    )
    found, limits = returns_for_windows("INF000", ["1Y", "6M", "8M"], inception_date="2015-01-01")
    assert "1Y" in found and "6M" in found and "8M" in found
    assert limits == []
    assert "1M" not in found


def test_a_young_fund_names_its_inception_instead_of_a_longer_return(monkeypatch):
    monkeypatch.setattr(
        "historical_data.nav_service.fetch_raw_nav_history",
        lambda isin, use_cache=True: _history("2026-08-01", 40),
    )
    found, limits = returns_for_windows("INF000", ["1Y"], inception_date="2026-08-01")
    assert found == {}
    assert len(limits) == 1
    note = limits[0]["note"]
    assert "1 August 2026" in note
    assert "not available" in note
    assert "inception" in note


def test_planner_default_month_follows_the_windows_it_named():
    plan = ExecutionPlan(
        routed_by="planner",
        answer_mode=AnswerMode.DATA_ONLY,
        window_days=30,
        window_label="1 month",
        funds=["Bandhan Large Cap Fund"],
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["6M", "1Y"]},
            )
        ],
    )
    out = finalize_planner_plan("show me the 1 year returns and 6 month returns", plan)
    assert out.window_label == "6 months and 1 year"
    assert out.window_days == 365


def test_a_risk_read_does_not_point_at_a_missing_returns_table():
    from news_rag.insight.fund_display import strip_empty_table_pointers

    args = validate_capability_args(
        "get_fund_data",
        {"modules": ["risk", "drawdown", "rating"], "windows": ["1M"], "periods": ["1y", "3y", "5y"]},
    )
    assert "windows" not in args
    prose = (
        "For the fund's returns over the past 1 month, see the table below.\n\n"
        "### Maximum drawdown across periods\n"
        "- **1Y:** worst fall **14.53%**."
    )
    cleaned = strip_empty_table_pointers(prose, {})
    assert "see the table below" not in cleaned
    assert "Maximum drawdown across periods" in cleaned


def test_a_narrow_cache_does_not_stand_in_for_a_wider_request():
    snapshot_only = {"snapshot": {"returns": {"1M": -0.96}}, "rs_rating": {"final_score": 79.85}}
    assert _return_slice_covers(
        "get_fund_data",
        {"modules": ["snapshot", "rating"], "windows": ["1M"]},
        snapshot_only,
    )
    assert not _return_slice_covers(
        "get_fund_data",
        {"modules": ["snapshot", "risk"], "windows": ["1M"]},
        snapshot_only,
    )
    holdings_only = {"holdings": [{"name": "Reliance Industries", "weight_pct": 8.2}], "sectors": []}
    assert not _return_slice_covers(
        "get_portfolio_data",
        {"sections": ["holdings", "sectors"]},
        holdings_only,
    )
    assert _return_slice_covers(
        "get_portfolio_data",
        {"sections": ["holdings"]},
        holdings_only,
    )


def test_a_gap_apology_is_removed_and_a_real_point_stays():
    from news_rag.insight.fund_display import strip_missing_data_caveats

    prose = (
        "### What stands out\n"
        "The data does not include a holdings weight table, so holding-level sizing is not available here, "
        "and the news is treated as context rather than a measured driver of the 1-month move.\n"
        "- **Reliance Industries (8.2%)** is in focus after reports on the Jio IPO.\n"
        "We can't get that data right now."
    )
    cleaned = strip_missing_data_caveats(prose)
    assert "holdings weight table" not in cleaned
    assert "treated as context" not in cleaned
    assert "Reliance Industries" in cleaned
    assert "We can't get that data right now." in cleaned
