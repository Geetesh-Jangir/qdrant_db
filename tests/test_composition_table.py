from news_rag.insight.display_table_policy import resolve_display_table_policy, TABLE_COMPOSITION
from news_rag.insight.fund_display import build_fund_display_tables, _composition_table_markdown
from news_rag.insight.contracts import ExecutionPlan


def test_composition_table_includes_asset_cap_and_holdings_sum():
    md = _composition_table_markdown(
        {
            "assets": [{"label": "Equity", "percentage": 99.93}, {"label": "Cash", "percentage": 0.07}],
            "market_cap": [
                {"label": "Large Cap", "percentage": 40.13},
                {"label": "Mid Cap", "percentage": 30.0},
                {"label": "Small Cap", "percentage": 29.8},
            ],
        },
        {
            "as_on": "2026-09-30",
            "holdings": [
                {"name": "A", "weight_pct": 3.44},
                {"name": "B", "weight_pct": 3.41},
                {"name": "C", "weight_pct": 3.40},
            ],
        },
        fund_name="Test Flexi Cap Fund",
        top_n=3,
    )
    assert "Equity" in md and "99.93%" in md
    assert "Large Cap" in md and "40.13%" in md
    assert "10.25%" in md or "10.24%" in md  # sum of three holdings


def test_holdings_question_includes_composition_display_table():
    plan = ExecutionPlan(funds=["Some Fund"])
    policy = resolve_display_table_policy("what this flexi cap holds", plan)
    assert TABLE_COMPOSITION in policy.include

    tables = build_fund_display_tables(
        {
            "fund:primary": {
                "fund_name": "Test Fund",
                "risk": {
                    "assets": [{"label": "Equity", "percentage": 98.0}],
                    "market_cap": [{"label": "Large Cap", "percentage": 60.0}],
                },
            },
            "portfolio:primary": {
                "holdings": [{"name": "Infosys", "weight_pct": 5.0}],
                "sectors": [{"sector": "IT", "weight_pct": 20.0}],
            },
        },
        question="what does the fund hold",
    )
    assert "composition_table" in tables
    assert "Equity" in tables["composition_table"]
