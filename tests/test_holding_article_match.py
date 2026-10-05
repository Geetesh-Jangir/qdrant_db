from news_rag.holdings_market import _article_mentions_holding


def test_icici_bank_rejects_prudential_amc_article():
    art = {
        "title": "ICICI Prudential AMC gets approval to acquire stake in AU Small Finance Bank",
        "snippet": "Approval includes ICICI Prudential Mutual Fund schemes",
        "entity_names": ["ICICI Prudential AMC"],
    }
    assert not _article_mentions_holding("ICICI Bank Limited", art)


def test_icici_bank_accepts_bank_article():
    art = {
        "title": "ICICI Bank Q3 results",
        "snippet": "ICICI Bank reported earnings",
        "entity_names": ["ICICI Bank"],
    }
    assert _article_mentions_holding("ICICI Bank Limited", art)
