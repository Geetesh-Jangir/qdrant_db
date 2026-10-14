from news_rag.insight.holding_attribution import (
    arithmetic_ok,
    attribute_rows,
    contribution_pct,
    news_is_about_company,
    render_investor_answer,
)


def test_bank_sleeve_is_not_the_drag_when_holdings_offset():
    # weight × return / 100 for the three banks in the failed answer
    assert contribution_pct(8, -1.25) == round(8 * -1.25 / 100, 2)
    holdings = [
        {"name": "HDFC Bank", "industry": "Banks", "percentage": 9.0, "return_pct": -1.11},
        {"name": "ICICI Bank", "industry": "Banks", "percentage": 6.0, "return_pct": -0.67},
        {"name": "Axis Bank", "industry": "Banks", "percentage": 6.0, "return_pct": 2.83},
        {"name": "Avenue Supermarts", "industry": "Retailing", "percentage": 4.0, "return_pct": -7.74},
    ]
    # Use the user's illustrative contributions directly via return that yields those pp
    holdings = [
        {"name": "HDFC Bank", "industry": "Banks", "weight_pct": 8.0, "return_pct": -1.25},
        {"name": "ICICI Bank", "industry": "Banks", "weight_pct": 5.0, "return_pct": -0.80},
        {"name": "Axis Bank", "industry": "Banks", "weight_pct": 8.0, "return_pct": 2.125},
        {"name": "Avenue Supermarts", "industry": "Retailing", "weight_pct": 3.0, "return_pct": -7.74},
    ]
    attr = attribute_rows(holdings, fund_return_pct=-2.59)
    bank_net = round(
        sum(r["contribution_pct"] for r in attr["all_priced"] if r["sector"] == "Banks"),
        2,
    )
    assert bank_net == round(-0.10 + -0.04 + 0.17, 2)
    assert attr["detractors"][0]["name"] == "Avenue Supermarts"
    assert arithmetic_ok(attr)
    assert abs(attr["explained_pct"] + attr["unexplained_pct"] - attr["fund_return_pct"]) < 0.02


def test_investor_answer_keeps_the_sum_and_drops_unrelated_news():
    holdings = [
        {"name": "Larsen & Toubro Limited", "industry": "Construction", "weight_pct": 3.63, "return_pct": -6.18},
        {"name": "Avenue Supermarts Limited", "industry": "Retailing", "weight_pct": 2.46, "return_pct": -7.58},
        {"name": "Mahindra & Mahindra Limited", "industry": "Automobiles", "weight_pct": 2.49, "return_pct": -7.21},
        {"name": "Axis Bank Limited", "industry": "Banks", "weight_pct": 5.26, "return_pct": 3.45},
    ]
    attr = attribute_rows(holdings, fund_return_pct=-2.59)
    attr["detractors"][0]["news"] = "Persistent Systems bought a stake in Nagarro SE."
    text = render_investor_answer(
        fund_name="Nippon Large Cap Fund",
        window_label="1 month",
        attr=attr,
        benchmark_name="BSE 100 - TRI",
        benchmark_return_pct=None,
    )
    assert "-0.59" in text
    assert "percentage points" in text
    assert "```" not in text
    assert "Persistent" not in text
    assert "window_pct" not in text
    assert "Return window dates" not in text
    assert "no company-specific news found" not in text
    assert news_is_about_company("Axis Bank reported deposit growth of 8.8%.", "Axis Bank Limited")
    assert not news_is_about_company(
        "Stocks to watch: Trent, Vedanta, Axis Bank, Adani Power and Marico.",
        "Trent Limited",
    )
