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


def test_portfolio_overview_omits_scheme_names():
    from news_rag.insight.evidence_pack import append_investor_portfolio_overview_tables
    from news_rag.insight.investor_subject import question_wants_scheme_names

    assert question_wants_scheme_names("tell me about my portfolio") is False
    assert question_wants_scheme_names("show my holdings") is True

    class _Plan:
        funds = []
        data_need = "investor_summary"
        response_shape = "prose"

    prose = (
        "## Your portfolio\n"
        "Worth **₹100**.\n"
        "### Largest holdings\n\n"
        "| Scheme | Current value |\n|---|---|\n| Kotak Contra Fund | ₹10 |\n"
        "### Summary\n"
        "Most of it sits in mid cap."
    )
    data = {
        "holdings": [{"scheme_name": "Kotak Contra Fund", "scheme_category": "contra", "aum_inr": 10}],
        "allocation": {"categoryShare": []},
        "summary": {"aum_inr": 100, "invested_inr": 80},
    }
    out = append_investor_portfolio_overview_tables(prose, data, _Plan(), "tell me about my portfolio")
    assert "Kotak" not in out
    assert "Your holdings" not in out
    assert "Most of it sits in mid cap." in out


def test_display_caps_at_eight_unless_whole_book():
    holdings = [{"scheme_name": f"F{i}", "aum_inr": i} for i in range(12)]
    rows, total, truncated = investor_holdings_for_display(
        holdings, "what is the biggest drawback in my portfolio", None
    )
    assert total == 12
    assert len(rows) == 8
    assert truncated is True
