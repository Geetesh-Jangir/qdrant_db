from news_rag.insight.contracts import AnswerMode
from news_rag.insight.question_intent import plan_matches_intent, resolve_question_intent
from news_rag.insight.slot_router import slot_route
from news_rag.tools import asks_fund_portfolio_holdings


def test_asks_portfolio_without_fund_word():
    q = "what are the top 5 sectors of axis largecap"
    assert asks_fund_portfolio_holdings(q)


def test_slot_route_top_sectors_data_only():
    q = "what are the top 5 sectors of axis largecap"
    plan = slot_route(q, confidence_threshold=0.88)
    assert plan is not None
    assert plan.answer_mode == AnswerMode.DATA_ONLY
    assert plan.tool_names == ["get_portfolio_data"]
    args = plan.tool_calls[0].arguments
    assert args.get("sections") == ["sectors"]
    assert args.get("top_n") == 5


def test_slot_route_top_sector_singular():
    q = "top sector of axis largecap"
    plan = slot_route(q, confidence_threshold=0.88)
    assert plan is not None
    assert plan.tool_calls[0].arguments.get("top_n") == 1
    assert plan.tool_calls[0].arguments.get("sections") == ["sectors"]


def test_intent_matches_slot_plan():
    q = "what are the top 5 sectors of axis largecap"
    intent = resolve_question_intent(q)
    plan = slot_route(q, confidence_threshold=0.88)
    assert intent.kind == "fund_portfolio"
    assert plan is not None
    assert plan_matches_intent(plan, intent)
