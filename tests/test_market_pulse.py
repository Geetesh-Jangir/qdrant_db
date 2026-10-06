from news_rag.ask_plan import AskPlan
from news_rag.market_pulse import (
    cluster_articles_by_theme,
    is_market_pulse_question,
    should_use_market_pulse,
)


def test_is_market_pulse_question():
    assert is_market_pulse_question("What's happening in the market right now?")
    assert not is_market_pulse_question("HDFC Large Cap NAV")


def test_should_use_market_pulse_no_fund():
    plan = AskPlan(tools=[], entities=[], answer_parts="market now")
    assert should_use_market_pulse("market update today", plan)


def test_cluster_prefers_larger_groups():
    articles = [
        {"title": "Nifty falls on RBI rate fears", "entity_names": ["Nifty 50"], "max_impact": 3, "url": "a1"},
        {"title": "Nifty drops as RBI signals tightening", "entity_names": ["Nifty 50"], "max_impact": 4, "url": "a2"},
        {"title": "Nifty slides RBI policy", "entity_names": ["Nifty"], "max_impact": 3, "url": "a3"},
        {"title": "Unrelated pharma FDA news", "entity_names": ["Sun Pharma"], "max_impact": 2, "url": "b1"},
    ]
    clusters = cluster_articles_by_theme(articles)
    assert clusters
    assert clusters[0].article_count >= 2
