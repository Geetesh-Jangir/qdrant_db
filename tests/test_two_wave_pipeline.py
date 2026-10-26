"""Unit tests for the new bounded two-wave ask pipeline."""

import pytest
from news_rag.insight.contracts import (
    AnswerMode,
    ExecutionPlan,
    QueryClass,
    ScopeKind,
    ToolCall,
    Wave2Policy,
)
from news_rag.insight.slot_router import slot_route
from news_rag.insight.capabilities import CAPABILITIES, execute_wave, get_capability_cache
from news_rag.insight.bridge import evaluate_wave2
from news_rag.insight.evidence_pack import build_evidence_pack, render_data_only_template
from news_rag.insight.grounding import cores_in_text, strip_ungrounded_numbers
from news_rag.insight.graph import GraphState, build_result, run_graph_pipeline


def test_slot_router_nav_lookup():
    """Simple NAV queries should route deterministically with high confidence as DATA_ONLY."""
    plan = slot_route("What is the current NAV of Parag Parikh Flexi Cap Fund?")
    assert plan is not None
    assert plan.confidence >= 0.8
    assert plan.answer_mode == AnswerMode.DATA_ONLY
    assert plan.query_class == QueryClass.SIMPLE
    assert "get_fund_data" in plan.tool_names
    assert plan.wave_2_policy.trigger == "none"
    assert len(plan.wave2_calls) == 0


def test_slot_router_holdings_lookup():
    """Top holdings query routes to get_portfolio_data."""
    plan = slot_route("top 10 holdings of HDFC Top 100")
    assert plan is not None
    assert plan.answer_mode == AnswerMode.DATA_ONLY
    assert "get_portfolio_data" in plan.tool_names
    call = next(c for c in plan.tool_calls if c.tool == "get_portfolio_data")
    assert call.arguments.get("top_n") == 10


def test_bridge_skips_wave2_for_data_only():
    """DATA_ONLY queries must strictly never run Wave 2."""
    plan = ExecutionPlan(
        answer_mode=AnswerMode.DATA_ONLY,
        wave_2_policy=Wave2Policy(trigger="always"),
    )
    calls = evaluate_wave2(plan, [])
    assert calls == []


def test_bridge_triggers_on_negative_return():
    """Negative returns in Wave 1 trigger Wave 2 news."""
    plan = ExecutionPlan(
        answer_mode=AnswerMode.INSIGHT_FUSION,
        wave_2_policy=Wave2Policy(trigger="negative_return", threshold=0.0),
        funds=["Test Fund"],
    )
    # Mock wave 1 result with negative return
    w1_res = [{
        "tool": "get_fund_data",
        "ok": True,
        "data": {"snapshot": {"returns": {"1M": -3.5}, "nav": 100.0}},
    }]
    calls = evaluate_wave2(plan, w1_res, deadline_remaining_ms=10000)
    assert len(calls) == 1
    assert calls[0].tool == "search_financial_news"
    assert calls[0].wave == 2


def test_bridge_skips_when_return_positive():
    """Positive returns should not fire negative_return trigger."""
    plan = ExecutionPlan(
        answer_mode=AnswerMode.INSIGHT_FUSION,
        wave_2_policy=Wave2Policy(trigger="negative_return", threshold=0.0),
        funds=["Test Fund"],
    )
    w1_res = [{
        "tool": "get_fund_data",
        "ok": True,
        "data": {"snapshot": {"returns": {"1M": 5.2}, "nav": 100.0}},
    }]
    calls = evaluate_wave2(plan, w1_res, deadline_remaining_ms=10000)
    assert calls == []


def test_data_only_template_renders_direct_markdown():
    """render_data_only_template formats snapshot without LLM."""
    plan = ExecutionPlan(
        funds=["HDFC Large Cap"],
        answer_mode=AnswerMode.DATA_ONLY,
    )
    w1_results = [{
        "tool": "get_fund_data",
        "ok": True,
        "fund": "HDFC Large Cap",
        "data": {
            "snapshot": {
                "fund_name": "HDFC Large Cap",
                "nav": 125.50,
                "day_change_pct": 0.45,
                "category": "Equity: Large Cap",
                "benchmark": "NIFTY 50 TRI",
                "returns": {"1M": 2.1, "1Y": 18.5},
            }
        },
    }]
    pack = build_evidence_pack(plan, w1_results, [])
    template = render_data_only_template(pack, plan)
    assert template is not None
    assert "₹125.50" in template
    assert "HDFC Large Cap" in template
    assert "+0.45%" in template


def test_screen_data_only_template_skips_duplicate_markdown_table():
    """Fund screen answers use fund_rankings in the UI; insight is heading + note only."""
    plan = ExecutionPlan(
        intent="rank",
        answer_mode=AnswerMode.DATA_ONLY,
    )
    w1_results = [
        {
            "tool": "screen_funds_by_exposure",
            "ok": True,
            "data": {
                "rankings": [
                    {
                        "fund_name": "Sample Fund",
                        "return_2y_pct": 12.5,
                        "latest_nav": 100.0,
                    }
                ],
                "return_window": "2Y",
                "ranking_note": "Funds with a positive 2Y NAV return.",
            },
        }
    ]
    pack = build_evidence_pack(plan, w1_results, [])
    template = render_data_only_template(pack, plan)
    assert template is not None
    assert "2 years" in template.lower() or "2Y" in template
    assert "| Fund |" not in template
    assert "Sample Fund" not in template
    assert "table below" in template.lower()


def test_grounding_strips_hallucinated_numbers():
    """strip_ungrounded_numbers removes numbers that are not in evidence."""
    evidence = "The NAV is 52.30 and 1-month return was -2.5%."
    allowed = cores_in_text(evidence)

    text = "The fund has a NAV of 52.30, an AUM of ₹85000, and returned -2.5%."
    grounded = strip_ungrounded_numbers(text, allowed)
    assert "52.30" in grounded
    assert "-2.5%" in grounded
    assert "85000" not in grounded



def test_capabilities_cache_stores_and_retrieves():
    """Capability cache stores results and respects TTL."""
    cache = get_capability_cache()
    cache.set("test_tool", {"a": 1}, {"data": "ok"}, ttl_seconds=60)
    cached = cache.get("test_tool", {"a": 1})
    assert cached == {"data": "ok"}


def test_out_of_scope_query_immediate_reply():
    """Out of scope queries return fast without tools."""
    res = run_graph_pipeline("What is the recipe for chicken biryani?")
    assert res.get("refused") is True
    assert "mutual fund" in res.get("insight", "").lower()
    assert res["research"]["tool_runs"] == []
