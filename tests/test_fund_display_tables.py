from news_rag.insight.fund_display import (
    build_fund_display_tables,
    format_display_tables_markdown,
    normalize_user_facing_text,
    stitch_display_tables_into_answer,
    strip_composer_display_sections,
)


def test_vs_category_column_in_long_table():
    tables = build_fund_display_tables(
        {
            "fund:x": {
                "fund_insights": {
                    "comparison_periods": {
                        "1Y": {
                            "fund_return": -6.15,
                            "benchmark_return": -5.0,
                            "vs_benchmark": -1.15,
                            "category_average_return": -5.08,
                            "vs_category": -1.07,
                        }
                    },
                    "benchmark_name": "NIFTY 100 | TRI",
                }
            }
        },
        question="last one month",
    )
    body = tables["vs_benchmark_table"]
    assert "vs category (pp)" in body
    assert "-1.07 pp" in body


def test_stitch_puts_tables_before_disclaimer():
    prose = "Opening line.\n\n*For context only — not investment advice.*"
    tables = {"vs_benchmark_table": "| Period | Fund |\n| --- | --- |\n| 1Y | -1.00% |"}
    out = stitch_display_tables_into_answer(prose, tables)
    assert out.index("Opening") < out.index("| Period |") < out.index("not investment advice")


def test_normalize_na_to_hyphen():
    assert normalize_user_facing_text("foo N/A bar") == "foo - bar"


def test_stitch_drops_duplicate_composer_table():
    prose = (
        "Intro.\n\n### Recent returns vs category\n\n"
        "| Period | Fund | Category avg | vs category (pp) |\n"
        "| --- | --- | --- | --- |\n"
        "| 1M | -6.15% | -5.08% | -1.07 pp |\n"
    )
    tables = {
        "short_horizon_vs_category_table": (
            "| Period | Fund | Category avg | vs category (pp) |\n"
            "| --- | --- | --- | --- |\n"
            "| 1M | -6.15% | -5.08% | -1.07 pp |"
        )
    }
    out = stitch_display_tables_into_answer(prose, tables)
    assert out.count("| 1M | -6.15% | -5.08% | -1.07 pp |") == 1


def test_holdings_table_column_order():
    tables = build_fund_display_tables(
        {
            "fund:x": {
                "attribution": {
                    "detractors": [
                        {"name": "Titan Company", "percentage": 5.07, "return_pct": -10.77},
                    ],
                    "contributors": [],
                },
                "snapshot": {"fund_name": "HDFC Large Cap"},
            }
        },
    )
    row = [ln for ln in tables["holdings_move_table"].split("\n") if ln.startswith("| Titan")][0]
    parts = [p.strip() for p in row.strip("|").split("|")]
    assert parts[0] == "Titan Company"
    assert parts[1] == "5.07%"
    assert parts[2] == "-10.77%"


def test_strip_composer_sections():
    text = "### Snapshot\n\nSome text\n\n### News themes\n\n- item"
    out = strip_composer_display_sections(text)
    assert "Snapshot" not in out
    assert "News themes" in out


def test_portfolio_tables_and_news_section():
    from news_rag.insight.fund_display import append_news_section

    tables = build_fund_display_tables(
        {
            "portfolio:x": {
                "holdings": [{"name": "HDFC Bank", "percentage": 9.2}],
                "sectors": [{"sector": "Financial Services", "percentage": 32.1}],
            }
        }
    )
    assert "HDFC Bank" in tables["portfolio_holdings_table"]
    assert "Financial Services" in tables["portfolio_sectors_table"]
    answer = append_news_section(
        "The fund lagged its benchmark.\n\n### News themes\n\n- short teaser",
        {"holdings": [{"title": "Bank raises guidance", "summary": "HDFC Bank lifted its loan-growth outlook.", "date": "2026-10-20"}]},
    )
    assert "### Recent news" in answer
    assert "Bank raises guidance" in answer
    assert "News themes" not in answer
