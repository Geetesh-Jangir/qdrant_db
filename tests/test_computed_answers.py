from news_rag.insight.computed_answers import asks_computed_illustration


def test_fire_sip_plan_is_a_computed_illustration():
    q = (
        "plan me a fire project of 2cr in which i annually increase the sip by 10% "
        "and my goal is to reach it there in 20 year"
    )
    assert asks_computed_illustration(q)


def test_sip_definition_is_not_a_calculator():
    assert not asks_computed_illustration("what is the full form of sip")
