from news_pipeline.config import Settings
from news_pipeline.sources.universe import load_holdings


def test_load_holdings_uses_xlsx_multi_query():
    settings = Settings(holdings_limit=3)
    entities = load_holdings(settings)
    assert len(entities) == 3
    assert entities[0]["name"] == "State Bank of India"
    assert entities[0]["query"] == '"State Bank of India"'
    assert entities[0]["industry"] == "Banks"
    icici = next(e for e in entities if "ICICI Bank" in e["name"])
    assert " OR " in icici["query"] and "ICICI Bank" in icici["query"]


def test_holdings_limit_capped_at_500():
    settings = Settings(holdings_limit=500)
    entities = load_holdings(settings)
    assert len(entities) == 500
    assert entities[-1]["type"] == "holding"