from datetime import date

from ai_insight.holding_insights.config import HOLDING_LOOKBACK_DAYS
from ai_insight.holding_insights.news import news_window


def test_news_window_is_seven_days():
    w = news_window(date(2026, 11, 17))
    assert w[0] < w[1]
    assert HOLDING_LOOKBACK_DAYS == 7