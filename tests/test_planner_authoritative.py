from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall, Wave2Policy
from news_rag.insight.planner_policy import finalize_planner_plan
from news_rag.insight.portfolio_plan import normalize_portfolio_plan_from_question
from news_rag.insight.question_intent import planner_supplement_for_question


def test_planner_supplement_does_not_classify_intent():
    q = "what are the top 5 holdigns of Axis ELSS - Tax Saver Fund"
    text = planner_supplement_for_question(q)
    assert "DETERMINISTIC INTENT" not in text
    assert "fund_overview" not in text
    assert "primary_tool" not in text


def test_normalize_portfolio_skips_planner_routed_plans():
    q = "top 5 stocks of Axis ELSS - Tax Saver Fund"
    plan = ExecutionPlan(
        routed_by="planner",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
    )
    out = normalize_portfolio_plan_from_question(q, plan)
    assert out.tool_names == ["get_fund_data"]
    assert out.answer_mode == AnswerMode.INSIGHT_FUSION


def test_finalize_planner_plan_fills_funds_from_question():
    q = "what are the top 5 holdigns of Axis ELSS - Tax Saver Fund"
    plan = ExecutionPlan(
        routed_by="planner",
        answer_mode=AnswerMode.DATA_ONLY,
        tool_calls=[
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": ["holdings"], "top_n": 5},
                wave=1,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
    )
    out = finalize_planner_plan(q, plan)
    assert out.funds
    assert "axis" in out.funds[0].lower()
    assert "search_financial_news" not in out.tool_names


def test_fund_overview_gets_news_even_if_planner_said_data_only():
    q = "tell me about hdfc large cap fund"
    plan = ExecutionPlan(
        routed_by="planner",
        intent="overview",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": ["holdings", "sectors"], "top_n": 5},
                wave=1,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
    )
    out = finalize_planner_plan(q, plan)
    assert out.answer_mode == AnswerMode.INSIGHT_FUSION
    assert out.wave_2_policy.trigger == "always"
    assert "search_financial_news" in out.tool_names
    news = next(c for c in out.tool_calls if c.tool == "search_financial_news")
    assert news.wave == 2
    assert news.arguments["scope"] == "all"


def test_plan_system_prompt_planner_authority():
    from news_rag.insight.plan import _invalidate_plan_system_cache, plan_system_prompt

    _invalidate_plan_system_cache()
    prompt = plan_system_prompt()
    assert "PLANNER AUTHORITY" in prompt
    assert "crude_oil" in prompt
    assert "There is no high_weight_holding" in prompt
    assert "macro_impact module" in prompt
    assert "DETERMINISTIC INTENT HINT" not in prompt
