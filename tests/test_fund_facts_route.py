from news_rag.query_router import try_fast_fund_fact_route


def test_fast_route_hdfc_sectors():
    r = try_fast_fund_fact_route(
        "what are the top 5 sectors in hdfc large and mid cap fund?"
    )
    assert r is not None
    assert r.intent == "fund_sectors"
    assert "hdfc" in r.fund.name.lower()
    assert "fund" in r.fund.name.lower()
