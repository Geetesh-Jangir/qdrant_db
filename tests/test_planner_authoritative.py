from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall, Wave2Policy
from news_rag.insight.planner_policy import finalize_planner_plan, horizon_code
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


def test_planner_overview_is_not_rewritten_into_a_news_call():
    q = "tell me about hdfc large cap fund"
    plan = ExecutionPlan(
        routed_by="planner",
        intent="overview",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund"],
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
    )
    out = finalize_planner_plan(q, plan)
    assert out.answer_mode == AnswerMode.DATA_ONLY
    assert out.tool_names == ["get_fund_data"]
    assert "search_financial_news" not in out.tool_names


def test_right_now_and_currently_use_one_week():
    q = "whats happening in the market right now?"
    plan = ExecutionPlan(
        routed_by="planner",
        intent="overview",
        answer_mode=AnswerMode.NEWS_ONLY,
        window_days=30,
        window_label="1 month",
        tool_calls=[
            ToolCall(
                tool="get_market_snapshot",
                arguments={"modules": ["index_return", "macro_series"], "window_days": 30},
                wave=1,
            ),
            ToolCall(
                tool="search_financial_news",
                arguments={"scope": "market", "top_n": 8, "window_days": 14},
                wave=2,
            ),
        ],
    )
    out = finalize_planner_plan(q, plan)
    assert out.window_days == 7
    assert out.window_label == "1W"
    assert all(c.arguments["window_days"] == 7 for c in out.tool_calls)

    current = finalize_planner_plan(
        "how is crude currently?",
        ExecutionPlan(
            routed_by="planner",
            answer_mode=AnswerMode.NEWS_ONLY,
            window_days=30,
            tool_calls=[
                ToolCall(
                    tool="get_market_snapshot",
                    arguments={"modules": ["macro_series"], "series": ["crude"], "window_days": 30},
                    wave=1,
                ),
            ],
        ),
    )
    assert current.window_days == 7
    assert current.tool_calls[0].arguments["window_days"] == 7


def test_named_period_is_not_replaced_by_right_now():
    q = "what is happening right now versus last month?"
    plan = ExecutionPlan(
        routed_by="planner",
        answer_mode=AnswerMode.NEWS_ONLY,
        window_days=30,
        window_label="1 month",
        tool_calls=[
            ToolCall(
                tool="get_market_snapshot",
                arguments={"modules": ["index_return"], "window_days": 30},
                wave=1,
            ),
        ],
    )
    out = finalize_planner_plan(q, plan)
    assert out.window_days == 30
    assert out.tool_calls[0].arguments["window_days"] == 30


def test_horizon_code_labels():
    assert horizon_code(1) == "1D"
    assert horizon_code(7) == "1W"
    assert horizon_code(30) == "1M"
    assert horizon_code(14) == "14D"


def test_plan_system_prompt_planner_authority():
    from news_rag.insight.plan import _invalidate_plan_system_cache, plan_system_prompt

    _invalidate_plan_system_cache()
    prompt = plan_system_prompt()
    assert "PLANNER AUTHORITY" in prompt
    assert "crude_oil" in prompt
    assert "There is no high_weight_holding" in prompt
    assert "macro_impact module" in prompt
    assert "DETERMINISTIC INTENT HINT" not in prompt
