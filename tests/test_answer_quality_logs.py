"""Fixes from the 2026-11-12 ask logs: sparse columns, category money, gold table, fund names."""

from news_rag.insight.brief import question_is_bullion_metal_price_question
from news_rag.insight.bullion_plan import apply_bullion_metal_scope
from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ScopeKind, ToolCall
from news_rag.insight.display_table_policy import drop_sparse_table_columns, question_wants_gold_table
from news_rag.insight.fact_answer import render_category_money_draft, render_gold_exposure_draft
from news_rag.insight.fact_slots import facts_only_compose_allowed
from news_rag.insight.fund_name_gate import clarify_plan_if_fund_unknown, scrub_unknown_fund_mentions


_ALLOC = {
    "investedByCategory": {"gold": 128993.0, "liquid": 490849.0, "short term": 0.0, "debt oriented": -1.0},
    "aumByCategory": {"gold": 169413.0, "liquid": 531573.0, "short term": 0.0, "debt oriented": 0.0},
}


def test_sparse_share_column_is_dropped():
    table = "\n".join([
        "| Category | Invested (Rs) | Share of invested |",
        "| --- | --- | --- |",
        "| Liquid | 4,90,849 |  |",
        "| Small cap | 4,51,172 | **17.68%** |",
        "| Value | 4,08,251 |  |",
        "| Large cap | 4,08,247 |  |",
        "| Gold | 1,28,993 |  |",
    ])
    out = drop_sparse_table_columns(table)
    assert "Share of invested" not in out
    assert "Liquid" in out
    assert "4,90,849" in out


def test_category_draft_has_invested_and_value_and_drops_zeros():
    text = render_category_money_draft(_ALLOC)
    assert "Invested" in text and "Current value" in text
    assert "Gold" in text and "Liquid" in text
    assert "short term" not in text.lower()
    assert "debt oriented" not in text.lower()
    one = render_category_money_draft(_ALLOC, only="gold")
    assert "Gold" in one
    assert "Liquid" not in one


def test_zero_gold_category_draft():
    alloc = {
        "investedByCategory": {"equity": 100.0, "large cap": 100.0},
        "aumByCategory": {"large cap": 110.0},
    }
    text = render_category_money_draft(alloc, only="gold")
    assert "not invested in gold" in text.lower()
    assert render_gold_exposure_draft(alloc)


def test_invested_in_gold_is_not_a_spot_price_ask():
    q = "how much i have invested in gold"
    assert not question_is_bullion_metal_price_question(q)
    assert not question_wants_gold_table(q)
    plan = ExecutionPlan(
        tool_calls=[ToolCall(tool="get_investor_portfolio", arguments={"modules": ["summary"]}, wave=1)],
    )
    out = apply_bullion_metal_scope(q, plan)
    assert not any(c.tool == "get_market_snapshot" for c in out.tool_calls)
    assert any(c.tool == "get_investor_portfolio" for c in out.tool_calls)


def test_gold_price_still_wants_a_draft_table():
    assert question_wants_gold_table("what is the gold price today")
    assert question_is_bullion_metal_price_question("is gold going up or down")


def test_gold_exposure_draft_labels_the_estimate():
    text = render_gold_exposure_draft(_ALLOC, {"returns": {"1W": {"pct": -3.39}}})
    assert "169" in text or "1,69" in text
    assert "estimate" in text.lower()
    assert "not a measured" in text.lower()


def test_facts_only_skipped_when_slots_missing_or_market_tools_present():
    assert facts_only_compose_allowed(
        fact_brief="| Fact | Value |",
        answer_mode=AnswerMode.DATA_ONLY.value,
        missing=[],
        tool_names=["get_investor_portfolio"],
    )
    assert not facts_only_compose_allowed(
        fact_brief="| Fact | Value |",
        answer_mode=AnswerMode.DATA_ONLY.value,
        missing=["holdings"],
        tool_names=["get_investor_portfolio"],
    )
    assert not facts_only_compose_allowed(
        fact_brief="| Fact | Value |",
        answer_mode=AnswerMode.DATA_ONLY.value,
        missing=[],
        tool_names=["get_market_snapshot"],
    )


def test_this_fund_with_many_names_clarifies_and_drops_invented_reading():
    memory = {
        "chat_turns": [
            {
                "user": "show me the name of the large caps that i hold",
                "assistant": "Axis Large Cap Fund and HDFC Small Cap Fund are both in the book.",
            }
        ],
        "frame": {
            "investor_subjects": [
                {"name": "Axis Large Cap Fund"},
                {"name": "HDFC Small Cap Fund"},
            ]
        },
    }
    plan = ExecutionPlan(
        planner_reading="How much the user has invested in DSP India T.I.G.E.R. Fund",
        tool_calls=[ToolCall(tool="get_investor_portfolio", arguments={"modules": ["summary"]}, wave=1)],
    )
    out = clarify_plan_if_fund_unknown(plan, memory, "how much did i have invested in this fund")
    assert out.scope_kind == ScopeKind.NEEDS_CLARIFICATION
    assert not out.tool_calls
    assert "DSP" not in (out.planner_reading or "")
    assert "Which fund" in (out.direct_reply or "")


def test_this_fund_uses_the_only_fund_in_the_last_answer():
    memory = {
        "chat_turns": [
            {
                "user": "show me the large cap",
                "assistant": "You hold Axis Large Cap Fund.",
            }
        ],
        "frame": {"investor_subjects": [{"name": "Axis Large Cap Fund"}, {"name": "HDFC Small Cap Fund"}]},
    }
    plan = ExecutionPlan(
        planner_reading="DSP India T.I.G.E.R. Fund",
        tool_calls=[ToolCall(tool="get_investor_portfolio", arguments={"modules": ["summary"]}, wave=1)],
    )
    out = clarify_plan_if_fund_unknown(plan, memory, "how much did i have invested in this fund")
    assert out.funds == ["Axis Large Cap Fund"]
    assert out.scope_kind != ScopeKind.NEEDS_CLARIFICATION
    inv = out.tool_calls[0]
    assert inv.arguments.get("scheme_filter") == "Axis Large Cap Fund"
    assert "DSP" not in (out.planner_reading or "")


def test_scrub_replaces_reading_when_no_deictic():
    plan = ExecutionPlan(planner_reading="The user means DSP India T.I.G.E.R. Fund")
    out = scrub_unknown_fund_mentions(plan, {"frame": {"investor_subjects": [{"name": "Axis Large Cap Fund"}]}}, "what is my xirr")
    assert out.planner_reading == "what is my xirr"
