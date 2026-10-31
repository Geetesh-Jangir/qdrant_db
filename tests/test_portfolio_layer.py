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
    monkeypatch.setenv("CLIENT_REF_NO", "CRN-test")
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


def test_repair_empty_investor_tool_calls(monkeypatch):
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


def test_validate_capability_requires_modules():
    from news_rag.insight.capabilities.catalog import validate_capability_args

    out = validate_capability_args("get_investor_portfolio", {})
    assert out.get("modules") == []
