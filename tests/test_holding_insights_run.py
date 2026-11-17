from ai_insight.holding_insights.run import _process_stock
from ai_insight.holding_insights.universe import StockRow
from datetime import date


def test_no_news_skips_llm(monkeypatch):
    stock = StockRow("T", "Test Co", "Banks", "T", "T.NS", "Test Co")
    monkeypatch.setattr(
        "ai_insight.holding_insights.run.get_price_snapshot",
        lambda *a, **k: {"bars": [], "latest_price": 1, "pattern_hints": {}},
    )

    class EmptyNews:
        articles = []
        scanned = 5
        after_gate = 0

    monkeypatch.setattr("ai_insight.holding_insights.run.get_top_news", lambda *a, **k: EmptyNews())

    called = {"llm": False}

    def fake_llm(*a, **k):
        called["llm"] = True
        return {}

    monkeypatch.setattr("ai_insight.holding_insights.run.call_holding_llm", fake_llm)
    insight, insuff = _process_stock(stock, date(2025, 1, 15), dry_run=False)
    assert insight is None
    assert insuff["reason"] == "no_news_after_filter"
    assert called["llm"] is False