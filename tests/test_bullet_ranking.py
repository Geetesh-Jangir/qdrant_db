from news_rag.ask_composer import _is_nav_bullet, _rank_bullets_by_fund_impact


def test_nav_first_then_holdings_by_impact():
    nav = {"fund_name": "PPFAS Flexi Cap Fund", "nav": 80.0}
    nav_line = "**PPFAS Flexi Cap Fund** — **NAV** ₹80"
    holdings_market = [
        {"name": "HDFC Bank Limited", "weight_pct": 8.0, "price": {"return_1m": -1.0, "approx_nav_contribution_1m_pct": -0.08}, "news": {"total": 2}},
        {"name": "ICICI Bank Limited", "weight_pct": 5.0, "price": {"return_1m": -6.0, "approx_nav_contribution_1m_pct": -0.3}, "news": {"total": 1}},
    ]
    bullets = [
        "Macro liquidity debate affects banks broadly.",
        nav_line,
        "**ICICI Bank** (5% weight) fell **-6%** over the past month; news driver: FII selling.",
        "**HDFC Bank** (8% weight) fell **-1%** over the past month; news driver: CEO review.",
        "Banks sector is 20% of the fund allocation.",
    ]
    ordered = _rank_bullets_by_fund_impact(
        bullets,
        nav=nav,
        nav_line=nav_line,
        holdings_market=holdings_market,
        sector_rows=[{"sector": "Banks", "percentage": 20.0}],
        question="How is PPFAS flexi cap and top holdings?",
        answer_parts="PPFAS performance and holdings",
    )
    assert _is_nav_bullet(ordered[0], nav)
    assert "icici" in ordered[1].lower()
