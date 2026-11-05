"""Startup portfolio snapshot: derived views, stale reads, preload failure."""

from __future__ import annotations

import time

from news_rag.insight.contracts import ExecutionPlan, ToolCall


def _doc() -> dict:
    return {
        "summary": {"aum_inr": 1000, "portfolio_xirr_pct": 8.2},
        "allocation": {},
        "holdings": [
            {
                "scheme_name": "Axis Large Cap Fund - Regular Plan - Growth",
                "scheme_category": "large cap",
                "scheme_type": "Equity",
                "aum_inr": 800,
                "isin": "INF846K01164",
                "xirr_pct": 6.91,
                "rs_label": "Average",
            },
            {
                "scheme_name": "A Debt Fund",
                "scheme_category": "liquid",
                "scheme_type": "Debt",
                "aum_inr": 200,
                "isin": "INF000000001",
                "xirr_pct": 4.0,
                "rs_label": "",
            },
        ],
    }


def test_derived_views_split_assets_and_categories():
    from news_rag.portfolio.views import balance_verdicts, build_derived_views

    derived = build_derived_views(_doc())
    assert derived["asset_split"]["equity"]["aum_pct"] == 80.0
    assert derived["asset_split"]["debt"]["aum_pct"] == 20.0
    assert derived["by_category"]["large cap"]["holdings"][0]["isin"] == "INF846K01164"
    assert derived["xirr_pct"] == 8.2
    assert derived["ratings"][0]["rs_label"] == "Average"
    lines = balance_verdicts(derived)
    assert any("balances that" in line for line in lines)


def test_equity_only_and_concentration_verdicts():
    from news_rag.portfolio.views import balance_verdicts

    tilted = balance_verdicts({
        "asset_split": {"equity": {"aum_pct": 95}, "debt": {"aum_pct": 0}},
        "top_categories": [{"name": "small cap", "aum_pct": 60}],
        "largest_holdings": [{"scheme_name": "One Fund", "aum_pct": 70}],
    })
    text = " ".join(tilted)
    assert "growth-leaning" in text
    assert "main theme" in text
    assert "carries most of the result" in text
    assert "risk" not in text.lower()


def test_stale_snapshot_does_not_wait_on_fetch(monkeypatch):
    from news_rag.portfolio.cache import (
        clear_cache_for_tests,
        get_normalized_portfolio,
        seed_portfolio_cache_for_tests,
    )
    from news_rag.portfolio.errors import PortfolioError

    clear_cache_for_tests()
    seed_portfolio_cache_for_tests("CRN-stale", _doc(), expired=True)
    calls = {"n": 0}

    def slow(_crn: str) -> dict:
        calls["n"] += 1
        time.sleep(1.5)
        raise PortfolioError("upstream down", code="upstream_error")

    monkeypatch.setattr("news_rag.portfolio.cache.fetch_workspace_raw", slow)
    started = time.perf_counter()
    doc, stats = get_normalized_portfolio("CRN-stale")
    elapsed = time.perf_counter() - started
    assert elapsed < 0.5
    assert stats["stale"] is True
    assert doc["holdings"][0]["isin"] == "INF846K01164"
    clear_cache_for_tests()


def test_preload_failure_returns_false(monkeypatch):
    from news_rag.portfolio.cache import clear_cache_for_tests, preload_configured_portfolio
    from news_rag.portfolio.errors import PortfolioError

    monkeypatch.setenv("CLIENT_REF_NO", "CRN-preload-fail")
    clear_cache_for_tests()

    def boom(_crn: str) -> dict:
        raise PortfolioError("nope", code="upstream_error")

    monkeypatch.setattr("news_rag.portfolio.cache.fetch_workspace_raw", boom)
    assert preload_configured_portfolio(timeout_sec=2) is False
    clear_cache_for_tests()


def test_compare_binds_cached_large_cap(monkeypatch):
    from news_rag.config import get_settings
    from news_rag.insight.portfolio_bind import bind_cached_portfolio
    from news_rag.portfolio.cache import clear_cache_for_tests, seed_portfolio_cache_for_tests

    monkeypatch.setenv("CLIENT_REF_NO", "CRN-bind")
    clear_cache_for_tests()
    seed_portfolio_cache_for_tests(get_settings().client_ref_no, _doc())
    plan = ExecutionPlan(
        intent="compare",
        routed_by="planner",
        funds=["Bandhan Large Cap Fund - Regular Plan - Growth"],
        portfolio_scope="none",
        data_need="investor_holding",
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
    )
    plan = bind_cached_portfolio(
        "compare this with the large cap that is in my portfolio",
        plan,
    )
    assert plan.funds == ["Bandhan Large Cap Fund - Regular Plan - Growth"]
    investor = next(call for call in plan.tool_calls if call.tool == "get_investor_portfolio")
    assert investor.arguments.get("scheme_filter") == "large cap"
    assert any(call.tool == "compare_funds" for call in plan.tool_calls)
    clear_cache_for_tests()


def test_catalog_fund_holdings_not_own_book():
    from news_rag.insight.portfolio_bind import bind_cached_portfolio, question_mentions_own_book
    from news_rag.insight.contracts import ExecutionPlan, ToolCall

    q = "tell me the one month return of top 3 holdings of absl quant fund"
    assert question_mentions_own_book(q) is False
    plan = ExecutionPlan(
        funds=["Aditya Birla Sun Life Quant Fund - Regular Plan - Growth"],
        tool_calls=[
            ToolCall(tool="get_portfolio_data", arguments={"sections": ["holdings"], "top_n": 3}),
            ToolCall(tool="get_market_snapshot", arguments={"modules": ["stock_quote"]}, wave=2),
        ],
    )
    plan = bind_cached_portfolio(q, plan)
    assert not any(call.tool == "get_investor_portfolio" for call in plan.tool_calls)


def test_one_fund_compare_drops_compare_tool(monkeypatch):
    from news_rag.insight.portfolio_bind import bind_cached_portfolio
    from news_rag.portfolio.cache import clear_cache_for_tests

    monkeypatch.setenv("CLIENT_REF_NO", "CRN-one")
    clear_cache_for_tests()
    plan = ExecutionPlan(
        intent="compare",
        funds=["Bandhan Large Cap Fund"],
        portfolio_scope="investor",
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1)],
    )
    plan = bind_cached_portfolio("compare this with the large cap in my portfolio", plan)
    assert any(call.tool == "compare_funds" for call in plan.tool_calls)
    investor = next(call for call in plan.tool_calls if call.tool == "get_investor_portfolio")
    assert investor.arguments.get("scheme_filter") == "large cap"
    clear_cache_for_tests()


def test_empty_tool_list_is_overridden_for_the_book(monkeypatch):
    from news_rag.insight.portfolio_bind import ensure_tools_for_data_question

    monkeypatch.setenv("CLIENT_REF_NO", "CRN-empty")
    plan = ExecutionPlan(intent="overview", data_need="investor_summary", portfolio_scope="investor", tool_calls=[])
    plan = ensure_tools_for_data_question("how is my portfolio", plan)
    assert any(call.tool == "get_investor_portfolio" for call in plan.tool_calls)


def test_concept_question_keeps_an_empty_tool_list():
    from news_rag.insight.portfolio_bind import ensure_tools_for_data_question

    plan = ExecutionPlan(
        intent="explain",
        data_need="none",
        concept_brief="A portfolio is the set of funds you hold.",
        tool_calls=[],
    )
    plan = ensure_tools_for_data_question("what is a portfolio", plan)
    assert plan.tool_calls == []
