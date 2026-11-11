"""Computed portfolio insights from a fixed book."""

from news_rag.portfolio.insights import build_insights, insights_for_brief


def _book():
    return {
        "meta": {"as_of_date": "10 Nov 2026"},
        "summary": {"aum_inr": 100, "portfolio_xirr_pct": 12.0, "absolute_return_pct": 18.0},
        "profile_risk": {"investment_style": "conservative"},
        "allocation": {},
        "holdings": [
            {
                "scheme_name": "Big Equity",
                "scheme_category": "large cap",
                "aum_inr": 80,
                "gain_loss_inr": 20,
                "absolute_return_pct": 25,
            },
            {
                "scheme_name": "Small Debt",
                "scheme_category": "debt",
                "aum_inr": 20,
                "gain_loss_inr": -2,
                "absolute_return_pct": -4,
            },
        ],
        "sip": {"plans": [{"scheme_name": "Big Equity", "amount": 5000, "is_live": True, "next_date": "2026-12-01"}]},
    }


def test_concentration_and_risk_flags():
    rows = build_insights(_book())
    by_kind = {}
    for row in rows:
        by_kind.setdefault(row.kind, row)
    assert by_kind["as_of"].text.startswith("Figures are as of")
    assert any(row.kind == "concentration" and row.severity == "review" for row in rows)
    assert by_kind["risk_alignment"].severity == "review"
    laggard = next(row for row in rows if row.kind == "laggards")
    assert "Small Debt" in laggard.text


def test_health_check_subset():
    kinds = {row.kind for row in insights_for_brief("health_check", _book())}
    assert "risk_alignment" in kinds
    assert kinds <= {"risk_alignment", "concentration", "sip", "laggards"}
