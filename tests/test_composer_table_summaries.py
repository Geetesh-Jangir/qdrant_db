from news_rag.insight.contracts import EvidencePack, ExecutionPlan
from news_rag.insight.display_table_policy import resolve_display_table_policy, TABLE_RETURNS
from news_rag.insight.fund_display import (
    build_fund_display_tables,
    filter_display_tables_by_decision,
    parse_tables_append_directive,
    strip_empty_bold_sections,
    summarize_tables_for_composer,
)


def test_summarize_tables_for_composer_extracts_mix_and_holdings():
    data_pack = {
        "fund:x": {
            "fund_name": "ICICI Flexi Cap",
            "risk": {
                "assets": [{"label": "Equity", "percentage": 97.16}],
                "market_cap": [
                    {"label": "Large Cap", "percentage": 61.1},
                    {"label": "Small Cap", "percentage": 23.02},
                ],
                "smaller_companies_pct": 35.65,
            },
        },
        "portfolio:x": {
            "as_on": "2026-09-30",
            "holdings": [
                {"name": "TVS Motor Company Ltd.", "weight_pct": 9.51},
                {"name": "ICICI Bank Ltd.", "weight_pct": 6.9},
            ],
            "sectors": [{"sector": "Automobiles", "weight_pct": 18.21}],
        },
    }
    tables = build_fund_display_tables(data_pack, question="what this flexi cap holds")
    summary = summarize_tables_for_composer(data_pack, tables)
    assert summary["asset_mix"][0]["weight_pct"] == 97.16
    assert summary["top_holdings"][0]["name"].startswith("TVS")
    assert summary["top_sectors"][0]["sector"] == "Automobiles"
    assert summary["top_holdings_weight_sum_pct"] == 16.41
    assert summary["table_quality"]["composition_table"] in ("complete", "partial")


def test_evidence_pack_compact_includes_table_summaries():
    data_pack = {
        "fund:x": {
            "risk": {"assets": [{"label": "Equity", "percentage": 99.0}]},
        },
        "portfolio:x": {"holdings": [{"name": "A", "weight_pct": 5.0}]},
    }
    tables = build_fund_display_tables(data_pack, question="holdings")
    pack = EvidencePack(data_pack=data_pack, display_tables=tables)
    compact = pack.compact()
    assert "TABLE_SUMMARIES" in compact
    assert compact["TABLE_SUMMARIES"]["top_holdings"][0]["name"] == "A"


def test_parse_tables_append_directive():
    text = "Hello.\n\n<!-- TABLES_APPEND: composition_table,portfolio_holdings_table -->"
    cleaned, keys = parse_tables_append_directive(text)
    assert "TABLES_APPEND" not in cleaned
    assert keys == frozenset({"composition_table", "portfolio_holdings_table"})

    cleaned2, keys2 = parse_tables_append_directive("Hi <!-- TABLES_APPEND: none -->")
    assert keys2 == frozenset()


def test_filter_display_tables_by_decision():
    tables = {
        "_title": "Fund",
        "composition_table": "| a |",
        "fund_returns_table": "| b |",
    }
    out = filter_display_tables_by_decision(tables, frozenset({"composition_table"}))
    assert "composition_table" in out
    assert "fund_returns_table" not in out


def test_strip_empty_bold_sections():
    prose = "Intro\n\n**Asset mix**\n\n**Market cap mix**\n\nMid cap **12%**."
    out = strip_empty_bold_sections(prose)
    assert "**Asset mix**" not in out
    assert "Mid cap" in out


def test_holdings_question_data_only_skips_returns_table():
    plan = ExecutionPlan(funds=["X"], answer_mode="DATA_ONLY", intent="lookup")
    policy = resolve_display_table_policy("what this flexi cap holds", plan)
    assert TABLE_RETURNS not in policy.include
