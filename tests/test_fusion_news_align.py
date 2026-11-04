from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall, Wave2Policy
from news_rag.insight.planner_policy import align_planned_news_execution


def test_wave2_news_moves_to_wave1_when_trigger_none():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="overview",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        funds=["HDFC Large Cap Fund - Growth"],
        window_days=1825,
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["risk", "rating", "snapshot"]}, wave=1),
            ToolCall(tool="get_portfolio_data", arguments={"sections": ["holdings", "sectors"], "top_n": 5}, wave=1),
            ToolCall(
                tool="search_financial_news",
                arguments={"scope": "fund", "top_n": 8, "window_days": 30},
                wave=2,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
    )
    align_planned_news_execution(plan)
    news = next(c for c in plan.tool_calls if c.tool == "search_financial_news")
    assert news.wave == 1
    assert news.arguments["scope"] == "all"
    assert len(plan.wave2_calls) == 0


def test_data_only_drops_news():
    plan = ExecutionPlan(
        answer_mode=AnswerMode.DATA_ONLY,
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
            ToolCall(
                tool="search_financial_news",
                arguments={"scope": "market", "top_n": 8, "window_days": 7},
                wave=1,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="always"),
    )
    align_planned_news_execution(plan)
    assert [call.tool for call in plan.tool_calls] == ["get_fund_data"]
    assert plan.wave_2_policy.trigger == "none"


def test_wave2_news_kept_when_trigger_always():
    plan = ExecutionPlan(
        answer_mode=AnswerMode.INSIGHT_FUSION,
        tool_calls=[
            ToolCall(
                tool="search_financial_news",
                arguments={"scope": "all", "top_n": 8, "window_days": 30},
                wave=2,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="always", max_calls=1),
    )
    align_planned_news_execution(plan)
    news = next(c for c in plan.tool_calls if c.tool == "search_financial_news")
    assert news.wave == 2
