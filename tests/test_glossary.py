from news_rag.insight.glossary import (
    asks_precise_definition,
    direct_glossary_reply,
    glossary_execution_plan,
)
from news_rag.insight.slot_router import slot_route


def test_nav_full_form_direct_reply():
    q = "what is the full form of nav?"
    assert asks_precise_definition(q)
    reply = direct_glossary_reply(q)
    assert reply
    assert "Net Asset Value" in reply
    plan = glossary_execution_plan(q)
    assert plan is not None
    assert plan.direct_reply
    assert not plan.tool_calls
    assert plan.max_words <= 40


def test_slot_router_glossary_no_tools():
    q = "what is the full form of nav?"
    plan = slot_route(q, confidence_threshold=0.97)
    assert plan is not None
    assert plan.direct_reply
    assert "Net Asset Value" in plan.direct_reply
    assert plan.tool_names == []


def test_fund_nav_not_glossary():
    q = "what is the nav of Axis ELSS Tax Saver Fund"
    assert not asks_precise_definition(q)
