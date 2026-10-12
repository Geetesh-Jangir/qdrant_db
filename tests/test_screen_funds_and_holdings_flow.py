"""Tests for screen_funds extraction, fund_top_stocks fallback resolution, and agent flow."""

from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest

from news_rag.ask_plan import AskPlan, PlannedTool
from news_rag.ask_execution import (
    ExecutionBundle,
    ToolRunResult,
    _run_one_tool,
    _run_tools_parallel,
    _resolve_fund_detail_fallback,
)
from news_rag.ask_composer import (
    _extract_ranked_funds_from_bundle,
    _sector_fund_payload,
)
from news_rag.affected_sectors import question_needs_affected_sectors
from news_rag.ask_agent import (
    _question_wants_holdings,
    _obs_has_holdings,
    _batch_already_answers,
)
from news_rag.name_resolution import ResolvedNames


def test_extract_ranked_funds_from_bundle_with_screen_funds():
    bundle = ExecutionBundle(names=ResolvedNames())
    bundle.tool_results["screen_funds_1"] = {
        "ok": True,
        "data": {
            "rankings": [
                {
                    "fund_name": "Invesco India Consumption Fund",
                    "isin": "INF205K01CQ0",
                    "return_1m_pct": 2.5,
                }
            ],
            "direction": "positive",
        },
    }
    ranked = _extract_ranked_funds_from_bundle(bundle)
    assert len(ranked) == 1
    assert ranked[0]["fund_name"] == "Invesco India Consumption Fund"
    assert ranked[0]["return_1m_pct"] == 2.5


def test_extract_ranked_funds_from_bundle_with_affected_sectors():
    bundle = ExecutionBundle(names=ResolvedNames())
    bundle.tool_results["affected_sectors_0"] = {
        "ok": True,
        "data": {
            "funds": [
                {
                    "fund_name": "Nippon India Auto Fund",
                    "isin": "INF123456789",
                    "return_1m_pct": 5.0,
                }
            ],
            "direction": "positive",
        },
    }
    ranked = _extract_ranked_funds_from_bundle(bundle)
    assert len(ranked) == 1
    assert ranked[0]["fund_name"] == "Nippon India Auto Fund"


def test_sector_fund_payload_with_screen_funds():
    bundle = ExecutionBundle(names=ResolvedNames())
    bundle.tool_results["screen_funds_2"] = {
        "ok": True,
        "data": {
            "direction": "positive",
            "ranking_note": "Screened positive funds",
            "rankings": [{"fund_name": "Fund A", "isin": "INFA"}],
        },
    }
    direction, note, funds = _sector_fund_payload(bundle)
    assert direction == "positive"
    assert note == "Screened positive funds"
    assert len(funds) == 1
    assert funds[0]["fund_name"] == "Fund A"


def test_run_one_tool_fund_top_stocks_missing_detail_returns_clean_error():
    plan = AskPlan()
    names = ResolvedNames()
    tool = PlannedTool(tool="fund_top_stocks")
    res = _run_one_tool(
        tool,
        0,
        plan,
        names,
        "how automobile sector is working?",
        date_from=None,
        date_to=None,
        min_impact=None,
        source=None,
        direction=None,
        query_log=None,
    )
    assert res.result.get("ok") is False
    assert "Fund detail required for fund_top_stocks" in res.result.get("error", "")
    assert "unknown tool" not in res.result.get("error", "")


def test_run_one_tool_fund_top_stocks_fallback_resolution_from_screen_funds():
    plan = AskPlan()
    names = ResolvedNames()
    bundle = ExecutionBundle(names=names)
    bundle.tool_results["screen_funds_1"] = {
        "ok": True,
        "data": {
            "rankings": [
                {
                    "scheme_name": "Test Growth Fund",
                    "isin": "INFTEST001",
                }
            ]
        },
    }

    mock_detail = {
        "fund_name": "Test Growth Fund",
        "fund_short_name": "Test Growth",
        "isin": "INFTEST001",
        "holdings": [
            {"name": "Maruti Suzuki India Ltd", "percentage": 9.5},
            {"name": "Tata Motors Ltd", "percentage": 8.0},
        ],
    }

    mock_index = MagicMock()
    mock_index.lookup_extracted_fund.return_value = mock_detail

    with patch("news_rag.fund_search.get_fund_index", return_value=mock_index):
        tool = PlannedTool(tool="fund_top_stocks", top_n=2)
        res = _run_one_tool(
            tool,
            2,
            plan,
            names,
            "give me two holdings of auto funds",
            date_from=None,
            date_to=None,
            min_impact=None,
            source=None,
            direction=None,
            query_log=None,
            bundle=bundle,
        )
        assert res.result.get("ok") is True
        rows = res.result.get("data", {}).get("rows", [])
        assert len(rows) == 2
        assert rows[0]["name"] == "Maruti Suzuki India Ltd"
        assert rows[1]["name"] == "Tata Motors Ltd"


def test_run_tools_parallel_waves_screen_and_holdings():
    plan = AskPlan()
    names = ResolvedNames()
    bundle = ExecutionBundle(names=names)

    mock_screen_res = {
        "ok": True,
        "data": {
            "rankings": [{"scheme_name": "Auto Fund", "isin": "INFAUTO1"}],
            "funds": [{"scheme_name": "Auto Fund", "isin": "INFAUTO1"}],
        },
    }
    mock_detail = {
        "fund_name": "Auto Fund",
        "fund_short_name": "Auto Fund",
        "isin": "INFAUTO1",
        "holdings": [{"name": "Mahindra & Mahindra", "percentage": 7.5}],
    }
    mock_index = MagicMock()
    mock_index.lookup_extracted_fund.return_value = mock_detail

    with patch("news_rag.ask_execution.run_screen_funds", return_value=mock_screen_res):
        with patch("news_rag.fund_search.get_fund_index", return_value=mock_index):
            tools = [
                PlannedTool(tool="screen_funds", sector_name="automobile"),
                PlannedTool(tool="fund_top_stocks", top_n=1),
            ]
            results = _run_tools_parallel(
                tools,
                plan,
                bundle,
                "automobile sector holdings",
                date_from=None,
                date_to=None,
                min_impact=None,
                source=None,
                direction=None,
                query_log=None,
            )
            assert len(results) == 2
            assert results[0].tool == "screen_funds"
            assert results[0].result.get("ok") is True
            assert results[1].tool == "fund_top_stocks"
            assert results[1].result.get("ok") is True
            assert len(bundle.holdings_rows) == 1
            assert bundle.holdings_rows[0]["name"] == "Mahindra & Mahindra"


def test_question_needs_affected_sectors_with_drivers():
    q1 = "what are the funds affected by rising crude oil prices?"
    assert question_needs_affected_sectors(q1) is True

    q2 = "which funds are impacted due to interest rate cuts?"
    assert question_needs_affected_sectors(q2) is True


def test_batch_already_answers_with_holdings_requirement():
    q = "how automobile sector is working and can you give me name of any two holdings and two funds that are in automobile sector?"
    assert _question_wants_holdings(q) is True

    obs_only_funds = [
        {"tool": "screen_funds", "ok": True, "counts": {"rows": 2}, "rows": [{"fund_name": "Fund 1"}]}
    ]
    assert _obs_has_holdings(obs_only_funds) is False
    assert _batch_already_answers(q, obs_only_funds) is False

    obs_with_holdings = [
        {"tool": "screen_funds", "ok": True, "counts": {"rows": 2}, "rows": [{"fund_name": "Fund 1"}]},
        {"tool": "fund_top_stocks", "ok": True, "counts": {"rows": 2}, "rows": [{"name": "Stock 1"}]},
    ]
    assert _obs_has_holdings(obs_with_holdings) is True
    assert _batch_already_answers(q, obs_with_holdings) is True
