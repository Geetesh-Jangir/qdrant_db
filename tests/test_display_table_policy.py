from news_rag.insight.contracts import AnswerMode, ExecutionPlan
from news_rag.insight.display_table_policy import (
    TABLE_LONG,
    TABLE_SHORT,
    TABLE_HOLDINGS,
    resolve_display_table_policy,
)


def test_fund_news_no_comparison_tables():
    q = "tell me about the news related to the hdfc large cap fund?"
    plan = ExecutionPlan(intent="overview", answer_mode=AnswerMode.INSIGHT_FUSION, window_days=30)
    pol = resolve_display_table_policy(q, plan)
    assert TABLE_LONG not in pol.include
    assert TABLE_SHORT not in pol.include


def test_fund_news_one_month_short_anchor_only():
    q = "news related to hdfc large cap fund in last one month"
    plan = ExecutionPlan(intent="overview", answer_mode=AnswerMode.INSIGHT_FUSION, window_days=30)
    pol = resolve_display_table_policy(q, plan)
    assert TABLE_SHORT in pol.include
    assert TABLE_LONG not in pol.include


def test_performance_question_gets_comparison():
    q = "how did hdfc large cap perform vs category last year?"
    plan = ExecutionPlan(intent="overview", answer_mode=AnswerMode.INSIGHT_FUSION, window_days=365)
    pol = resolve_display_table_policy(q, plan)
    assert TABLE_LONG in pol.include or TABLE_SHORT in pol.include


def test_why_moved_gets_holdings():
    q = "why did hdfc large cap fall last month?"
    plan = ExecutionPlan(intent="explain_cause", answer_mode=AnswerMode.INSIGHT_FUSION, window_days=30)
    pol = resolve_display_table_policy(q, plan)
    assert TABLE_HOLDINGS in pol.include


def test_tell_me_about_fund_keeps_the_snapshot_and_skips_unasked_lists():
    from news_rag.insight.display_table_policy import (
        TABLE_HOLDINGS,
        TABLE_PORTFOLIO,
        TABLE_RETURNS,
        TABLE_SECTORS,
        TABLE_SNAPSHOT,
    )

    q = "tell me about hdfc large cap fund"
    plan = ExecutionPlan(
        intent="overview",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        funds=["HDFC Large Cap Fund"],
        window_days=30,
    )
    pol = resolve_display_table_policy(q, plan)
    assert TABLE_SNAPSHOT in pol.include
    assert TABLE_RETURNS not in pol.include
    assert TABLE_PORTFOLIO not in pol.include
    assert TABLE_SECTORS not in pol.include
    assert TABLE_HOLDINGS not in pol.include
    asked = resolve_display_table_policy(
        "tell me the top holdings and sectors and 1 year return of hdfc large cap",
        plan,
    )
    assert TABLE_PORTFOLIO in asked.include
    assert TABLE_SECTORS in asked.include
    assert TABLE_RETURNS in asked.include
