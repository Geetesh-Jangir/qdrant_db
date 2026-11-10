from news_rag.fund_rating_screen import fund_type_name_spec, parse_rating_screen


def test_name_me_debt_fund_gets_rating_spec():
    q = "can you name me a debt fund and show its sector information"
    spec = fund_type_name_spec(q)
    assert spec is not None
    assert spec.fund_type == "debt"
    assert spec.count == 1
    assert not spec.locked
    parsed = parse_rating_screen(q)
    assert parsed is not None
    assert parsed.fund_type == "debt"


def test_random_debt_not_equity_when_also_asks_debt_vs_equity():
    q = "name me any random debt fund and tell me whats the difference in debt and equity fund"
    spec = fund_type_name_spec(q)
    assert spec is not None
    assert spec.fund_type == "debt"
