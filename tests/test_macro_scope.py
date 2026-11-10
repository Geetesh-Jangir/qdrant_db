from news_rag.insight.brief import question_is_standalone_macro
from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
from news_rag.insight.investor_subject import (
    ensure_catalog_tools_for_fund_news,
    question_refers_deictic_fund,
    reconcile_planner_invented_fund_name,
    resolve_answer_subject,
)
from news_rag.insight.macro_scope import apply_standalone_macro_scope


def test_us_election_rupee_is_standalone_macro():
    q = "whats happening in the US MID TERM ELECTION and how its affecting indian rupee"
    assert question_is_standalone_macro(q)


def test_how_its_affecting_rupee_is_not_deictic_fund_title():
    q = "whats happening in the US MID TERM ELECTION and how its affecting indian rupee"
    assert not question_refers_deictic_fund(q)
    plan = ExecutionPlan(funds=[], answer_mode=AnswerMode.NEWS_ONLY)
    memory = {"frame": {"last_fund_focus": "DSP India T.I.G.E.R. Fund - Regular Plan - Growth"}}
    assert resolve_answer_subject(q, plan, memory) == ""


def test_reconcile_does_not_bind_memory_fund_on_macro():
    plan = ExecutionPlan(
        funds=["Some Planner Hallucination Fund"],
        subject_ref="user_named",
        tool_calls=[ToolCall(tool="search_financial_news", arguments={"scope": "macro"}, wave=1)],
    )
    memory = {"frame": {"last_fund_focus": "DSP India T.I.G.E.R. Fund - Regular Plan - Growth"}}
    out = reconcile_planner_invented_fund_name(plan, memory, "whats happening in the US midterm and rupee")
    assert out.funds == []
    assert out.subject_ref == "none"


def test_macro_scope_injects_news_when_planner_sent_no_tools():
    plan = ExecutionPlan(
        intent="explain_cause",
        answer_mode=AnswerMode.NEWS_ONLY,
        window_days=30,
        tool_calls=[],
    )
    q = "whats happening in the US MID TERM ELECTION and how its affecting indian rupee"
    out = apply_standalone_macro_scope(q, plan)
    assert any(c.tool == "search_financial_news" for c in out.tool_calls)
    news = next(c for c in out.tool_calls if c.tool == "search_financial_news")
    assert "rupee" in (news.arguments or {}).get("topics", [])
    assert any(c.tool == "get_market_snapshot" for c in out.tool_calls)


def test_market_overview_does_not_invent_rupee_search():
    plan = ExecutionPlan(
        intent="overview",
        answer_mode=AnswerMode.NEWS_ONLY,
        window_days=7,
        tool_calls=[
            ToolCall(tool="get_market_snapshot", arguments={"modules": ["index_return"]}, wave=1),
            ToolCall(tool="get_macro_news", arguments={}, wave=1),
        ],
    )
    out = apply_standalone_macro_scope("whats happening in the market right now", plan)
    assert not any(c.tool == "search_financial_news" for c in out.tool_calls)


def test_macro_scope_strips_fund_tools():
    plan = ExecutionPlan(
        funds=["DSP India T.I.G.E.R. Fund - Regular Plan - Growth"],
        subject_ref="memory_primary",
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
            ToolCall(tool="get_portfolio_data", arguments={"sections": ["holdings"]}, wave=1),
            ToolCall(tool="search_financial_news", arguments={"scope": "macro"}, wave=1),
        ],
    )
    q = "whats happening in the US MID TERM ELECTION and how its affecting indian rupee"
    out = apply_standalone_macro_scope(q, plan)
    assert out.funds == []
    assert not any(c.tool == "get_fund_data" for c in out.tool_calls)
    ensure = ensure_catalog_tools_for_fund_news(out, q)
    assert not any(c.tool == "get_fund_data" for c in ensure.tool_calls)
