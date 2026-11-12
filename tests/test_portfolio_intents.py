"""Planner portfolio_intent maps to a fixed bundle. No question matching."""

from news_rag.insight.contracts import AnswerMode, ExecutionPlan
from news_rag.insight.plan import PLAN_SCHEMA, _PLAN_PROMPT
from news_rag.insight.portfolio_intents import (
    apply_portfolio_intent,
    data_need_for,
    modules_for,
    normalize_portfolio_intent,
    portfolio_intent_from_question,
    shape_for,
    should_attach_news,
)


def test_question_infers_fy_summary_intent():
    assert portfolio_intent_from_question("FY summary of my portfolio") == "fy_summary"
    plan = ExecutionPlan(portfolio_intent="none", portfolio_scope="none")
    apply_portfolio_intent(plan, "FY summary of my portfolio")
    assert plan.portfolio_intent == "fy_summary"
    assert plan.portfolio_scope == "investor"


def test_unknown_intent_is_none():
    assert normalize_portfolio_intent("not-a-real-intent") == "none"
    assert normalize_portfolio_intent("") == "none"
    assert shape_for("nope") == "none"


def test_fact_bundle_and_shape():
    assert shape_for("aum") == "fact"
    assert modules_for("aum") == ["summary"]
    assert data_need_for("aum") == "investor_summary"
    assert shape_for("portfolio_overview") == "brief"
    assert "allocation" in modules_for("health_check")
    assert "profile_risk" in modules_for("health_check")


def test_schema_lists_portfolio_intent():
    props = PLAN_SCHEMA["properties"]["understanding"]["properties"]
    assert "aum" in props["portfolio_intent"]["enum"]
    assert "none" in props["portfolio_intent"]["enum"]


def test_apply_fact_skips_news_and_composer():
    plan = ExecutionPlan(
        portfolio_intent="aum",
        portfolio_scope="none",
        data_need="none",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        requires_compose=True,
        tool_calls=[],
    )
    from news_rag.insight.contracts import ToolCall

    plan.tool_calls = [ToolCall(tool="search_financial_news", arguments={}, wave=2)]
    apply_portfolio_intent(plan)
    assert plan.portfolio_scope == "investor"
    assert plan.data_need == "investor_summary"
    assert plan.answer_mode == AnswerMode.DATA_ONLY
    assert plan.requires_compose is False
    assert plan.tool_calls == []
    assert should_attach_news("aum") is False
    assert should_attach_news("portfolio_overview") is True
    assert should_attach_news("where_losing") is True
    assert should_attach_news("scheme_performance") is False


def test_prompt_mentions_portfolio_intent():
    assert "portfolio_intent" in _PLAN_PROMPT
    assert "portfolio_overview" in _PLAN_PROMPT


def test_xirr_fact_reads_xirr_module_slice():
    from news_rag.insight.fact_answer import render_portfolio_fact

    data = {
        "meta": {"as_of_date": "2026-11-11"},
        "xirr": {"portfolio_xirr_pct": 12.98},
    }
    text = render_portfolio_fact("xirr", data)
    assert "12.98" in text
    assert "not available" not in text.lower()


def test_st_vs_lt_gains_from_pnl_summary():
    from news_rag.insight.fact_answer import render_portfolio_fact

    book = {
        "meta": {"as_of_date": "2026-11-11"},
        "pnl_summary": {"short_term_gain_inr": 4000.5, "long_term_gain_inr": 802.6},
    }
    text = render_portfolio_fact("st_vs_lt_gains", book)
    assert "4,000.5" in text or "4000.5" in text
    assert "802.6" in text
    assert "not available" not in text.lower()


def test_next_sip_uses_normalized_next_due_date():
    from news_rag.insight.fact_answer import render_portfolio_fact

    book = {
        "sip": {
            "plans": [
                {"scheme_name": "Later Fund", "next_due_date": "2026-11-15"},
                {"scheme_name": "Soon Fund", "next_due_date": "2026-11-12"},
            ]
        }
    }
    text = render_portfolio_fact("next_sip", book)
    assert "2026-11-12" in text
    assert "Soon Fund" in text
    assert "don't have" not in text.lower()


def test_allocation_fact_uses_category_share_list():
    from news_rag.insight.fact_answer import render_portfolio_fact

    book = {
        "meta": {"as_of_date": "2026-11-11"},
        "allocation": {
            "categoryShare": [
                {"name": "large & mid cap", "aum_inr": 28760.0, "aum_pct": 41.2},
                {"name": "small cap", "aum_inr": 14075.0, "aum_pct": 20.16},
            ],
        },
    }
    text = render_portfolio_fact("allocation", book)
    assert "large & mid cap" in text
    assert "41.2" in text
    assert "not available" not in text.lower()


def test_nav_of_scheme_picks_planned_fund_not_first_holding():
    from news_rag.insight.contracts import ExecutionPlan
    from news_rag.insight.fact_answer import render_portfolio_fact

    book = {
        "meta": {"as_of_date": "2026-11-11"},
        "holdings": [
            {"scheme_name": "Invesco India Large & Mid Cap Fund - Regular Plan - Growth", "current_nav": 112.96, "nav_date": "2026-11-09"},
            {"scheme_name": "Quant Small Cap Fund - Growth", "current_nav": 282.7207, "nav_date": "2026-11-09"},
        ],
    }
    plan = ExecutionPlan(funds=["Quant Small Cap Fund - Growth"], portfolio_intent="nav_of_scheme")
    text = render_portfolio_fact("nav_of_scheme", book, plan=plan)
    assert "Quant Small Cap" in text
    assert "282.72" in text
    assert "Invesco" not in text


def test_compose_always_uses_composer_for_largest_holding(monkeypatch):
    from types import SimpleNamespace

    from news_rag.insight.contracts import EvidencePack
    from news_rag.insight.graph import GraphState, node_compose
    from news_rag.insight import graph as graph_mod
    from news_rag.insight.plan import parse_plan

    plan = parse_plan(
        {
            "scope": {"kind": "in_scope"},
            "understanding": {
                "goal": "Largest holding",
                "intent": "lookup",
                "answer_mode": "DATA_ONLY",
                "portfolio_intent": "top_holdings",
            },
            "tool_calls": [{"tool": "get_investor_portfolio", "arguments": {"modules": ["holdings"]}, "wave": 1}],
        }
    )
    seen: dict[str, int] = {"calls": 0}

    def fake_llm(**kwargs):
        seen["calls"] += 1
        seen["user"] = kwargs.get("user_content") or ""
        return SimpleNamespace(
            raw_text="Your largest holding is **Invesco India Large & Mid Cap Fund** at **Rs 29,175**.",
            provider="anthropic",
            model="test",
            input_tokens=1,
            output_tokens=20,
        )

    monkeypatch.setattr(graph_mod, "call_insight_llm", fake_llm)
    monkeypatch.setattr(graph_mod, "llm_api_key_configured", lambda *_a, **_k: True)
    monkeypatch.setattr(graph_mod, "composer_model", lambda *_a, **_k: "test")
    monkeypatch.setattr(
        graph_mod,
        "get_settings",
        lambda: SimpleNamespace(insight_compose_always=True, llm_provider="anthropic"),
    )

    state = GraphState(question="which is the largest holding", plan=plan)
    state.evidence_pack = EvidencePack(
        data_pack={
            "investor_portfolio": {
                "meta": {"as_of_date": "2026-11-12"},
                "holdings": [
                    {"scheme_name": "Invesco India Large & Mid Cap Fund - Regular Plan - Growth", "aum_inr": 29174.614},
                    {"scheme_name": "Quant Small Cap Fund - Growth", "aum_inr": 15226.4891},
                ],
            }
        }
    )
    node_compose(state)
    assert seen["calls"] == 1
    assert "largest holding" in (state.answer or "").lower()
    assert "Invesco" in (state.answer or "")
    assert "Quant Small Cap" not in (state.answer or "")
