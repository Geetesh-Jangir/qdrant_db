from news_rag.insight.capabilities.executor import _isin_for_fund_name
from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.memory.fund_context import merge_fund_isins_map
from news_rag.insight.sector_exposure_tables import (
    render_all_holdings_metric_table,
    render_all_holdings_return_table,
)


def test_merge_fund_isins_reads_holding_isins_map():
    memory = {
        "holding_isins": {"Quant Small Cap Fund - Growth": "INF966L01AA0"},
        "holdings_in_chat": [{"name": "Kotak Contra Fund - Growth", "isin": "INF174K01327"}],
    }
    mapping = merge_fund_isins_map(memory)
    assert mapping["quant small cap fund - growth"] == "INF966L01AA0"
    assert mapping["kotak contra fund - growth"] == "INF174K01327"


def test_isin_for_fund_name_prefers_fund_isins_over_ambiguous_name(monkeypatch):
    class Index:
        def lookup_extracted_fund(self, name="", isin=""):
            if isin == "INF966L01AA0":
                return {"isin": isin, "fund_name": name}, False, []
            if "quant" in (name or "").lower():
                return None, True, []
            return None, False, []

    monkeypatch.setattr("news_rag.fund_search.get_fund_index", lambda: Index())
    ctx = {"fund_isins": {"quant small cap fund - growth": "INF966L01AA0"}}
    assert _isin_for_fund_name("Quant Small Cap Fund - Growth", ctx) == "INF966L01AA0"


def test_all_holdings_rs_rating_table_skips_return_table():
    plan = ExecutionPlan(
        funds=["Alpha Fund - Growth", "Beta Fund - Growth"],
        holding_scope="all_holdings",
        asked_facts=["rs_rating"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["rating"]}, wave=1)],
    )
    memory = {
        "holdings_in_chat": [
            {"name": "Alpha Fund - Growth"},
            {"name": "Beta Fund - Growth"},
        ],
    }
    results = [
        {
            "ok": True,
            "tool": "get_fund_data",
            "fund": "Alpha Fund - Growth",
            "data": {"rs_rating": {"label": "Recommended", "final_score": 78.5}},
        },
        {"ok": True, "tool": "get_fund_data", "fund": "Beta Fund - Growth", "data": {}},
    ]
    table = render_all_holdings_metric_table(plan, results, memory)
    assert "Recommended" in table
    assert "78.5" in table
    assert "not available" in table
    assert render_all_holdings_return_table(plan, results, memory) == ""
