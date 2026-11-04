from news_rag.insight.pack_sanitize import (
    investor_holdings_for_display,
    scheme_gain_loss_pct,
    sort_holdings_weakest_first,
)


def test_scheme_gain_loss_pct_omits_redeemed_sentinel():
    row = {
        "invested_inr": 34998.25,
        "aum_inr": 0,
        "gain_loss_inr": -34998.25,
        "absolute_return_pct": -100.0,
    }
    assert scheme_gain_loss_pct(row) is None


def test_scheme_gain_loss_pct_when_still_invested():
    row = {
        "invested_inr": 100000,
        "aum_inr": 85000,
        "gain_loss_inr": -15000,
        "absolute_return_pct": -15.0,
    }
    assert scheme_gain_loss_pct(row) == -15.0


def test_weakest_by_gain_not_xirr():
    holdings = [
        {"scheme_name": "A", "xirr_pct": 3.0, "gain_loss_inr": -1000},
        {"scheme_name": "B", "xirr_pct": -5.0, "gain_loss_inr": -500},
    ]
    ordered = sort_holdings_weakest_first(holdings)
    assert ordered[0]["scheme_name"] == "A"


def test_display_caps_at_eight_unless_whole_book():
    holdings = [{"scheme_name": f"F{i}", "aum_inr": i} for i in range(12)]
    rows, total, truncated = investor_holdings_for_display(
        holdings, "what is the biggest drawback in my portfolio", None
    )
    assert total == 12
    assert len(rows) == 8
    assert truncated is True
