from news_rag.insight.fund_news_scope import infer_fund_news_layers
from news_rag.tools import asks_fund_related_news


def test_overview_news_is_holdings_and_sectors():
    q = "tell me about quant small cap"
    assert infer_fund_news_layers(q) == frozenset({"holdings", "sectors"})


def test_infer_all_layers_when_unspecified():
    q = "news related to the hdfc large cap fund"
    assert infer_fund_news_layers(q) == frozenset({"holdings", "sectors", "macro"})


def test_infer_sector_only():
    q = "sector news for my fund HDFC Large Cap"
    assert infer_fund_news_layers(q) == frozenset({"sectors"})


def test_infer_macro_only():
    q = "market level macro news for HDFC Large Cap Fund"
    layers = infer_fund_news_layers(q)
    assert layers == frozenset({"macro"})


def test_asks_fund_related_news():
    assert asks_fund_related_news("news related to hdfc large cap fund")
    assert not asks_fund_related_news("latest RBI repo rate news")
