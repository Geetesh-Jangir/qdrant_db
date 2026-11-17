from ai_insight.holding_insights.price import _consecutive_down_days


def test_consecutive_down_days():
    assert _consecutive_down_days([10, 9, 8, 7]) == 3
    assert _consecutive_down_days([10, 11, 12]) == 0