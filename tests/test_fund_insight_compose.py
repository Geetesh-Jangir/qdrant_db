from __future__ import annotations

from news_rag.fund_insight_compose import _is_weak_news_line, compose_fund_insight_bullets


def test_rejects_mid_sentence_fragment() -> None:
    assert _is_weak_news_line("giants from Deutsche Bank AG and Citigroup Inc. Yet at home")


def test_compose_includes_labeled_news() -> None:
    articles = [
        {
            "title": "ICICI Bank posts steady loan growth in festive quarter",
            "snippet": "ICICI Bank Ltd reported steady loan growth as credit demand picked up ahead of the festive season.",
            "_news_layer": "holding",
            "_news_source_label": "ICICI Bank Ltd.",
        },
        {
            "title": "RBI keeps repo rate unchanged amid inflation watch",
            "snippet": "The Reserve Bank of India held the repo rate steady while monitoring inflation trends.",
            "_news_layer": "macro",
            "_news_source_label": "Banking & rates",
        },
    ]
    bullets = compose_fund_insight_bullets(
        nav={"fund_name": "HDFC Large Cap Fund", "nav": 100.0, "returns": {"1m": -2.0}},
        holdings=[{"name": "ICICI Bank Ltd.", "percentage": 10.0}],
        sectors=[{"sector": "Banks", "percentage": 30.0}],
        articles=articles,
        min_news=2,
        max_news=5,
    )
    assert any("Performance" in b for b in bullets)
    assert any("Holding" in b for b in bullets)
