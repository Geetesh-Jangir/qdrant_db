from news_rag.ask_plan import AskPlan, PlannedTool
from news_rag.market_pulse import (
    cluster_articles_by_theme,
    common_market_news_from_plan,
    market_pulse_from_plan,
)


def test_common_market_news_from_plan():
    plan = AskPlan(tools=[PlannedTool(tool="common_market_news")])
    assert common_market_news_from_plan(plan)
    assert market_pulse_from_plan(plan)


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
