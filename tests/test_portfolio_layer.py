"""Investor portfolio normalize, project, scope enforcement, and executor."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "workspace_sample.json"


@pytest.fixture
def normalized_doc():
    from news_rag.portfolio.normalize import normalize_workspace

    raw = json.loads(SAMPLE.read_text(encoding="utf-8"))
    return normalize_workspace(raw)


def test_normalize_pnl_summary_includes_term_gains(normalized_doc):
    pnl = normalized_doc.get("pnl_summary") or {}
    assert pnl.get("short_term_gain_inr") is not None
    assert pnl.get("long_term_gain_inr") is not None


def test_project_pnl_scheme_without_filter_returns_schemes(normalized_doc):
    from news_rag.portfolio.project import project_modules

    out = project_modules(normalized_doc, {"modules": ["pnl_scheme"]})
    block = out["data"].get("pnl_scheme") or {}
    schemes = block.get("schemes") or []
    assert len(schemes) >= 1
    assert isinstance(schemes[0].get("transactions"), list)


def test_normalize_strips_pii(normalized_doc):
    blob = json.dumps(normalized_doc).lower()
    assert "pan" not in blob or '"pan"' not in blob
    assert "mobile" not in blob
    assert "email" not in blob
    assert normalized_doc.get("summary", {}).get("aum_inr") is not None
    assert len(normalized_doc.get("holdings") or []) >= 1


def test_project_summary_minimal(normalized_doc):
    from news_rag.portfolio.project import project_modules

    out = project_modules(normalized_doc, {"modules": ["summary"]})
    assert out["ok"]
    data = out["data"]
    assert "summary" in data
    assert "holdings" not in data
    assert "sip" not in data


def test_project_holdings_fields(normalized_doc):
    from news_rag.portfolio.project import project_modules

    out = project_modules(
        normalized_doc,
        {"modules": ["holdings"], "holdings_fields": "minimal", "top_n": 2},
    )
    rows = out["data"]["holdings"]
    assert len(rows) <= 2
    if rows:
        assert set(rows[0].keys()) <= {"scheme_name", "aum_inr", "gain_loss_inr", "xirr_pct"}


def test_enforce_portfolio_scope_strips_tool(monkeypatch):
    from news_rag.insight.contracts import ExecutionPlan, ToolCall
    from news_rag.insight.portfolio_scope import enforce_portfolio_scope
    from news_rag.portfolio.cache import set_active_crn

    set_active_crn("CRN-test")

    plan = ExecutionPlan(
        portfolio_scope="none",
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={"modules": ["summary"]}, wave=1),
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
        ],
    )
    monkeypatch.setenv("CLIENT_REF_NO", "CRN-test")

    plan = enforce_portfolio_scope(plan)
    assert all(c.tool != "get_investor_portfolio" for c in plan.tool_calls)
    assert any(c.tool == "get_fund_data" for c in plan.tool_calls)


def test_executor_with_fixture(monkeypatch):
    from news_rag.portfolio.cache import set_active_crn

    monkeypatch.setenv("CLIENT_REF_NO", "CRN-test")
    set_active_crn("CRN-test")
    monkeypatch.setenv("PORTFOLIO_FIXTURE_PATH", "data/workspace_sample.json")
    monkeypatch.delenv("RUPEESTOP_ADMIN_TOKEN", raising=False)

    from news_rag.portfolio.cache import clear_cache_for_tests

    clear_cache_for_tests()

    from news_rag.insight.capabilities.executor import execute_capability
    from news_rag.insight.contracts import ToolCall

    call = ToolCall(
        tool="get_investor_portfolio",
        arguments={"modules": ["summary", "meta"]},
        wave=1,
    )
    rows = execute_capability(call, ctx={"portfolio_enabled": True})
    assert len(rows) == 1
    assert rows[0]["ok"]
    assert rows[0]["data"].get("summary")


def test_unknown_crn_is_not_served_from_the_sample(monkeypatch):
    from news_rag.portfolio.cache import clear_cache_for_tests, set_active_crn
    from news_rag.portfolio.errors import InvalidCRN

    monkeypatch.delenv("PORTFOLIO_FIXTURE_PATH", raising=False)
    clear_cache_for_tests()
    set_active_crn("CRN-local-no-token")

    def reject(_crn: str) -> dict:
        raise InvalidCRN("wrong CRN")

    monkeypatch.setattr("news_rag.portfolio.cache.fetch_workspace_raw", reject)

    from news_rag.insight.capabilities.executor import execute_capability
    from news_rag.insight.contracts import ToolCall

    call = ToolCall(tool="get_investor_portfolio", arguments={"modules": ["summary"]}, wave=1)
    rows = execute_capability(call, ctx={})
    assert rows[0]["ok"] is False
    set_active_crn("")
    clear_cache_for_tests()


def test_repair_empty_investor_tool_calls(monkeypatch):
    from news_rag.portfolio.cache import set_active_crn

    set_active_crn("CRN-test")
    monkeypatch.setenv("CLIENT_REF_NO", "CRN-test")
    from news_rag.insight.contracts import ExecutionPlan
    from news_rag.insight.portfolio_scope import enforce_portfolio_scope

    plan = ExecutionPlan(
        intent="overview",
        data_need="investor_summary",
        portfolio_scope="none",
        tool_calls=[],
    )
    plan = enforce_portfolio_scope(plan)
    assert any(c.tool == "get_investor_portfolio" for c in plan.tool_calls)
    mods = plan.tool_calls[0].arguments.get("modules") or []
    assert "summary" in mods
    assert "holdings" in mods


def test_current_value_and_nonzero_xirr():
    from news_rag.portfolio.normalize import normalize_workspace

    raw = {
        "meta": {"asOfDate": "2026-11-02"},
        "sections": {
            "live": {
                "data": {
                    "liveSummary": {
                        "totalMarketValue": 13179,
                        "totalInvestedAmount": 12999.35,
                        "portfolioXirrPercent": 0,
                        "liveXirrPercent": 1.13,
                        "xirrPercent": 1.13,
                    },
                    "schemes": [{
                        "schemeName": "WhiteOak Capital Mid Cap Fund",
                        "folioScheme": "100#101G",
                        "investedAmount": 12999.35,
                        "availableUnits": 638.641,
                        "currentNav": 20.636,
                        "liveXirrPercent": 2.51,
                        "schemeCategory": "mid cap",
                    }],
                }
            },
            "xirr": {
                "data": {
                    "data": [{
                        "schemeName": "WhiteOak",
                        "folioScheme": "100#101G",
                        "xirr": 2.51,
                        "marketValueAtTo": 13178.99,
                        "investedAmountAtTo": 12999.35,
                    }]
                }
            },
            "book": {"data": {"books": {"total": {"allocation": {"aumByCategory": {"mid cap": 13179}}}}}},
        },
    }
    doc = normalize_workspace(raw)
    holding = doc["holdings"][0]
    assert holding["aum_inr"] == 13178.99
    assert holding["gain_loss_inr"] is not None
    assert doc["summary"]["portfolio_xirr_pct"] == 1.13
    assert doc["allocation"]["aumByCategory"]["mid cap"] == 13179


def test_portfolio_concentration_report_format():
    from news_rag.insight.evidence_pack import _portfolio_concentration_report

    investor = {
        "summary": {"aum_inr": 65405.0, "scheme_count": 4},
        "allocation": {
            "categoryShare": [
                {"name": "large & mid cap", "aum_inr": 26511, "aum_pct": 40.53},
                {"name": "small cap", "aum_inr": 13494, "aum_pct": 20.63},
            ],
        },
        "concentration": {
            "total_current_value": 65405.0,
            "aum_by_category": {
                "large & mid cap": 26511,
                "small cap": 13494,
                "mid cap": 13179,
                "contra": 12221,
            },
            "aum_by_scheme_type": {"equity": 65405},
            "top_holdings": [
                {"name": "Cash and Cash Equivalents", "weight_pct": 4.26, "fund_count": 4, "industry": "Cash"},
                {"name": "ICICI Bank", "weight_pct": 4.02, "fund_count": 2, "industry": "Banks"},
            ],
            "top_holdings_weight_pct": 8.28,
            "top_holdings_count": 2,
            "sectors": [{"sector": "Banks", "weight_pct": 12.71}],
        },
    }
    text = _portfolio_concentration_report(investor)
    assert text is not None
    assert "### Portfolio concentration" in text
    assert "### Fund categories" in text
    assert "40.53%" in text
    assert "| Holding | Weight | Value |" in text
    assert "approx" not in text.lower()
    assert "### Summary" not in text


def test_concentration_keeps_cash():
    from news_rag.portfolio.concentration import project_concentration

    raw = {
        "top_holdings": [
            {"instrument_name": "Cash and Cash Equivalents", "percentage": 4.26, "fund_count": 4, "industry": "Cash", "type": "Cash"},
            {"instrument_name": "HDFC Bank", "percentage": 3.1, "fund_count": 2, "industry": "Banks", "type": "Equity"},
        ],
        "sector_allocation": [{"sector": "Banks", "percentage": 12.7}],
    }
    out = project_concentration(raw, top_n=6)
    names = [row["name"] for row in out["top_holdings"]]
    assert "Cash and Cash Equivalents" in names
    assert out["top_holdings_weight_pct"] == 7.36


def test_holdings_table_uses_exact_value():
    from news_rag.insight.contracts import ExecutionPlan
    from news_rag.insight.evidence_pack import _render_investor_portfolio_markdown

    plan = ExecutionPlan(data_need="investor_holding", response_shape="table")
    text = _render_investor_portfolio_markdown(
        {"holdings": [{"scheme_name": "WhiteOak", "scheme_category": "mid cap", "aum_inr": 13178.99, "invested_inr": 12999.35, "gain_loss_inr": 179.64, "absolute_return_pct": 1.38, "xirr_pct": 2.51, "rs_label": "Recommended", "rs_score": 74}]},
        plan,
    )
    assert text is not None
    assert "13,179" in text or "13,178.99" in text
    assert "Absolute return" in text
    assert "approx" not in text.lower()


def test_returns_table_for_investor_pnl():
    from news_rag.insight.contracts import AnswerMode, ExecutionPlan
    from news_rag.insight.evidence_pack import render_data_only_template
    from news_rag.insight.contracts import EvidencePack

    plan = ExecutionPlan(
        answer_mode=AnswerMode.DATA_ONLY,
        data_need="investor_pnl",
        response_shape="table",
        requires_compose=False,
    )
    pack = EvidencePack(
        data_pack={
            "investor_portfolio": {
                "meta": {"as_of_date": "2026-11-02", "xirr_window": {"from": "2025-11-02", "to": "2026-11-02"}},
                "holdings": [
                    {
                        "scheme_name": "Quant Small Cap Fund - Growth",
                        "scheme_category": "small cap",
                        "aum_inr": 13494.3,
                        "invested_inr": 12999.35,
                        "gain_loss_inr": 494.95,
                        "absolute_return_pct": 3.81,
                        "xirr_pct": 6.96,
                        "rs_label": "Recommended",
                        "rs_score": 70.6,
                    },
                ],
            },
        },
    )
    text = render_data_only_template(pack, plan)
    assert text is not None
    assert "### Returns by scheme" in text
    assert "6.96%" in text
    assert "494.95" in text or "495" in text


def test_enforce_returns_questions_use_holdings_not_xirr_only(monkeypatch):
    from news_rag.portfolio.cache import set_active_crn

    set_active_crn("CRN-test")
    monkeypatch.setenv("CLIENT_REF_NO", "CRN-test")
    from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
    from news_rag.insight.portfolio_scope import enforce_portfolio_scope

    plan = ExecutionPlan(
        answer_mode=AnswerMode.DATA_ONLY,
        data_need="investor_xirr",
        portfolio_scope="investor",
        tool_calls=[
            ToolCall(
                tool="get_investor_portfolio",
                arguments={"modules": ["xirr"], "include_meta": True},
                wave=1,
            ),
        ],
        requires_compose=True,
    )
    plan = enforce_portfolio_scope(plan)
    modules = plan.tool_calls[0].arguments.get("modules") or []
    assert "holdings" in modules
    assert "summary" in modules
    assert plan.requires_compose is False


def test_concentration_question_loads_stock_and_sector_data(monkeypatch):
    from news_rag.portfolio.cache import set_active_crn

    set_active_crn("CRN-test")
    monkeypatch.setenv("CLIENT_REF_NO", "CRN-test")
    from news_rag.insight.contracts import ExecutionPlan
    from news_rag.insight.portfolio_scope import enforce_portfolio_scope

    plan = ExecutionPlan(
        intent="lookup",
        data_need="investor_holding",
        planner_reading="Concentration of the user's own portfolio: largest schemes and sectors",
        tool_calls=[],
    )
    plan = enforce_portfolio_scope(plan)
    modules = plan.tool_calls[0].arguments.get("modules") or []
    assert "concentration" in modules
    assert "allocation" in modules
    assert "summary" in modules


def test_validate_capability_requires_modules():
    from news_rag.insight.capabilities.catalog import validate_capability_args

    out = validate_capability_args("get_investor_portfolio", {})
    assert out.get("modules") == []


def test_investor_drawback_strips_hallucinated_catalog_fund(monkeypatch):
    from news_rag.portfolio.cache import set_active_crn

    set_active_crn("CRN-test")
    monkeypatch.setenv("CLIENT_REF_NO", "CRN-test")
    from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
    from news_rag.insight.portfolio_scope import enforce_portfolio_scope

    plan = ExecutionPlan(
        intent="overview",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        data_need="investor_hybrid",
        portfolio_scope="investor",
        planner_reading="Which weakness stands out most in the user's own holdings: concentration, underperformance",
        funds=["Baroda BNP Paribas Short Term Fund - Segregated Portfolio 1 - Growth"],
        tool_calls=[
            ToolCall(
                tool="get_investor_portfolio",
                arguments={"modules": ["summary", "allocation", "concentration"], "include_meta": True},
                wave=1,
            ),
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot", "risk", "rating"], "windows": ["1Y"]},
                wave=1,
            ),
        ],
    )
    plan = enforce_portfolio_scope(plan, memory={})
    assert plan.funds == []
    assert all(c.tool != "get_fund_data" for c in plan.tool_calls)
    modules = plan.tool_calls[0].arguments.get("modules") or []
    assert "holdings" in modules


def test_switch_evicts_the_previous_crn(monkeypatch):
    from fastapi.testclient import TestClient

    from news_rag.app import app
    from news_rag.config import get_settings
    from news_rag.portfolio.cache import clear_cache_for_tests, peek_portfolio, set_active_crn
    from news_rag.portfolio.errors import InvalidCRN

    clear_cache_for_tests()

    def fake(crn: str) -> dict:
        if str(crn).startswith("BAD"):
            raise InvalidCRN("wrong CRN")
        return {"sections": {"live": {"data": {"schemes": [{"schemeName": "Fund " + crn}]}}}}

    monkeypatch.setattr("news_rag.portfolio.cache.fetch_workspace_raw", fake)
    client = TestClient(app)

    first = client.post("/api/portfolio/select", json={"conversation_id": "conv-a", "crn": "CRN-aaaa"})
    assert first.status_code == 200
    assert peek_portfolio("CRN-aaaa") is not None

    bad = client.post(
        "/api/portfolio/select",
        json={"conversation_id": "conv-b", "previous_conversation_id": "conv-a", "crn": "BADCRN"},
    )
    assert bad.status_code == 404
    assert peek_portfolio("CRN-aaaa") is not None

    second = client.post(
        "/api/portfolio/select",
        json={"conversation_id": "conv-b", "previous_conversation_id": "conv-a", "crn": "CRN-bbbb"},
    )
    assert second.status_code == 200
    assert peek_portfolio("CRN-aaaa") is None
    assert peek_portfolio("CRN-bbbb")["holdings"][0]["scheme_name"] == "Fund CRN-bbbb"

    set_active_crn("")
    assert get_settings().portfolio_enabled is False
    clear_cache_for_tests()


def test_active_crn_reaches_a_worker_thread():
    import contextvars
    from concurrent.futures import ThreadPoolExecutor

    from news_rag.portfolio.cache import get_active_crn, set_active_crn

    set_active_crn("CRN-ctx")
    parent = contextvars.copy_context()
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(parent.run, get_active_crn).result() == "CRN-ctx"
    set_active_crn("")
