from news_rag.insight.question_intent import (
    plan_matches_intent,
    resolve_question_intent,
)
from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall, Wave2Policy


def test_intent_fund_portfolio_vs_sector_screen():
    q_hold = "top 5 stocks invested in hdfc large cap fund"
    q_sector = "5 funds invested in banking sector"
    ih = resolve_question_intent(q_hold)
    is_ = resolve_question_intent(q_sector)
    assert ih.kind == "fund_portfolio"
    assert ih.primary_tool == "get_portfolio_data"
    assert is_.kind == "screen_sector_exposure"
    assert is_.primary_tool == "screen_funds_by_exposure"


def test_plan_mismatch_triggers_planner_path_concept():
    intent = resolve_question_intent("top 5 stocks of hdfc large cap fund")
    wrong = ExecutionPlan(
        answer_mode=AnswerMode.DATA_ONLY,
        tool_calls=[
            ToolCall(tool="screen_funds_by_exposure", arguments={"top_n": 5}, wave=1),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
        routed_by="slot_router",
        confidence=0.92,
    )
    assert not plan_matches_intent(wrong, intent)
