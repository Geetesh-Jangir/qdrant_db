"""Fund payload returns, limits, and headline rating. NAV history only for gaps."""

from news_rag.fund_risk import headline_rating, rating_for_request, rating_lead
from news_rag.fund_search import parse_holding_summary, parse_investment_limits, parse_rupeestop_rating
from news_rag.insight.capabilities.catalog import validate_capability_args


_RAW = {
    "nav": {"value": 1311.1569, "day_change_pct": 0.269},
    "returns": {
        "1m": {"value": 0.23},
        "1y": {"value": -8.53},
        "3y": {"value": 8},
        "5y": {"value": 8.93},
        "extra": {"1w": {"value": 2.74}},
    },
    "rupeestop_rating": {
        "score": 64.32,
        "label": "Good Choice",
        "computed_at": "2026-10-31T22:00:00.693Z",
    },
    "investment_limits": {
        "min_sip": 100,
        "min_lumpsum": 100,
        "min_additional": 100,
        "systematic": True,
        "transaction_modes": [{"scheme_transaction_mode_demat_physical_allowed": "Demat"}],
        "redemption_settlement": "3",
        "sip_frequencies": {"Monthly": {"allowed": True, "min_invest": 100, "additional": 1}},
    },
    "portfolio": {"holding_count": 49, "top_5_pct": 34.76, "top_10_pct": 53},
    "sebi_riskometer": "Very High",
}


def test_parse_limits_rating_and_holding_summary():
    limits = parse_investment_limits(_RAW)
    assert limits["min_sip"] == 100
    assert limits["transaction_modes"] == ["Demat"]
    assert limits["sip_frequencies"]["Monthly"]["min_invest"] == 100
    rating = parse_rupeestop_rating(_RAW)
    assert rating["score"] == 64.32
    assert rating["label"] == "Good Choice"
    summary = parse_holding_summary(_RAW, _RAW["portfolio"])
    assert summary == {"holding_count": 49, "top_5_pct": 34.76, "top_10_pct": 53.0}


def test_default_windows_are_one_three_and_five_years():
    args = validate_capability_args("get_fund_data", {"modules": ["snapshot"]})
    assert args["windows"] == ["1Y", "3Y", "5Y"]


def test_named_window_is_not_expanded():
    args = validate_capability_args("get_fund_data", {"modules": ["snapshot"], "windows": ["1W"]})
    assert args["windows"] == ["1W"]


def test_snapshot_uses_payload_returns_and_history_only_for_gaps(monkeypatch):
    from news_rag.insight.layer_tools import run_fund_snapshot

    calls = []

    def _nav(ctx):
        return {
            "ok": True,
            "data": {
                "isin": "INF179K01BE2",
                "fund_name": "HDFC Top 100",
                "nav": 1311.1569,
                "day_change_pct": 0.269,
                "returns": {"1w": 2.74, "1y": -8.53, "3y": 8, "5y": 8.93},
            },
        }

    def _history(isin, windows, inception_date=""):
        calls.append(list(windows))
        return {"2M": 1.5}, []

    monkeypatch.setattr("news_rag.insight.tool_runners.run_fund_nav_adapter", _nav)
    monkeypatch.setattr("news_rag.insight.return_windows.returns_for_windows", _history)

    default = run_fund_snapshot({})
    assert default["data"]["returns"] == {"1Y": -8.53, "3Y": 8.0, "5Y": 8.93}
    assert calls == []

    week = run_fund_snapshot({"windows": ["1W"]})
    assert week["data"]["returns"] == {"1W": 2.74}
    assert calls == []

    two_months = run_fund_snapshot({"windows": ["2M"]})
    assert calls == [["2M"]]
    assert two_months["data"]["returns"]["2M"] == 1.5


def test_headline_rating_has_no_date_and_skips_admin(monkeypatch):
    detail = {"isin": "INF179K01BE2", "rupeestop_rating": _RAW["rupeestop_rating"]}
    called = []
    monkeypatch.setattr(
        "news_rag.fund_risk.fetch_public_rating",
        lambda isin: called.append(isin) or {"final_score": 1, "label": "Other", "pillars": {"risk": {}}},
    )
    headline = rating_for_request(detail, {"modules": ["rating"]})
    assert called == []
    assert headline["final_score"] == 64.32
    assert headline["label"] == "Good Choice"
    assert "computed_at" not in headline
    lead = rating_lead({**headline, "computed_at": "2026-10-31T22:00:00.693Z"})
    assert "2026" not in lead
    assert "Good Choice" in lead

    full = rating_for_request(detail, {"modules": ["rating"], "pillars": True})
    assert called == ["INF179K01BE2"]
    assert "pillars" in full
    from news_rag.fund_risk import rating_needs_pillars

    assert rating_needs_pillars({"modules": ["risk", "drawdown", "rating"]}) is True
    assert rating_needs_pillars({"modules": ["rating"]}) is False


def test_headline_helper_drops_computed_at():
    out = headline_rating({"rupeestop_rating": _RAW["rupeestop_rating"]})
    assert "computed_at" not in out
