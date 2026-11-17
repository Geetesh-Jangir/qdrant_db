from ai_insight.holding_insights.universe import load_top_stocks


def test_load_top_stocks_limit():
    rows = load_top_stocks(3)
    assert len(rows) == 3
    assert rows[0].stock_id
    assert rows[0].yfinance_ticker.endswith(".NS")