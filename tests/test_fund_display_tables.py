from news_rag.insight.fund_display import (
    assemble_fund_overview_answer,
    build_fund_display_tables,
    format_display_tables_markdown,
    normalize_user_facing_text,
    stitch_display_tables_into_answer,
    strip_composer_display_sections,
)


def _comparison_pack(periods: dict) -> dict:
    return {"fund:x": {"fund_insights": {"comparison_periods": periods, "benchmark_name": "Nifty 50"}}}


def test_comparison_omits_missing_benchmark_and_category():
    tables = build_fund_display_tables(
        _comparison_pack({"1Y": {"fund_return": -4.0}}),
    )
    assert "vs_benchmark_table" not in tables
    assert "short_horizon_vs_category_table" not in tables


def test_comparison_keeps_only_category_when_benchmark_missing():
    tables = build_fund_display_tables(
        _comparison_pack({
            "1Y": {"fund_return": -4.0, "category_average_return": -1.5, "vs_category": -2.5},
        }),
    )
    body = tables["vs_benchmark_table"]
    assert "Category avg" in body
    assert "Benchmark" not in body
    assert tables["_heading_vs_benchmark_table"] == "### Returns vs category"


def test_comparison_keeps_only_benchmark_when_category_missing():
    tables = build_fund_display_tables(
        _comparison_pack({
            "1Y": {"fund_return": -4.0, "benchmark_return": -1.0, "vs_benchmark": -3.0},
        }),
    )
    body = tables["vs_benchmark_table"]
    assert "Benchmark" in body
    assert "Category avg" not in body
    assert tables["_heading_vs_benchmark_table"] == "### Returns vs benchmark"


def test_short_comparison_requires_category_average():
    tables = build_fund_display_tables(
        {
            "fund:x": {
                "snapshot": {"returns": {"1M": -2.0}},
                "fund_insights": {"fund_returns_short_horizon_pct": {"1M": -2.0}},
            }
        }
    )
    assert "short_horizon_vs_category_table" not in tables


def test_snapshot_shows_regular_expense_exit_load_and_aum():
    tables = build_fund_display_tables(
        {
            "fund:x": {
                "snapshot": {
                    "fund_name": "HDFC ELSS",
                    "nav": 100,
                    "expense_ratio": {"regular": 1.58, "plan": "regular", "as_on_date": "2026-09-30"},
                    "exit_load_summary": "Exit load is 1% if you leave within 1 year, and nothing after 1 year.",
                    "aum": 37293.95,
                }
            }
        }
    )
    body = tables["snapshot_table"]
    assert "Expense ratio (regular)" in body
    assert "1.58%" in body
    assert "Direct" not in body
    assert "nothing after 1 year" in body
    assert "37,293.95" in body


def test_expense_ratio_hides_direct_unless_asked():
    from news_rag.fund_rupeestop_metrics import expense_ratio_for_question, parse_fund_costs, summarize_exit_load

    costs = parse_fund_costs(
        {
            "ter_expense_ratio": {"regular": 1.58, "direct": 0.74, "as_on_date": "2026-09-30"},
            "exit_load_slabs": [
                {"remarks": "1% on or before 1Y, Nil after 1Y", "exitLoad": 1},
            ],
            "aum": 37293.95,
        }
    )
    regular = expense_ratio_for_question(costs["expense_ratio"], "tell me about this fund")
    direct = expense_ratio_for_question(costs["expense_ratio"], "what is the direct plan expense ratio")
    assert regular.get("plan") == "regular"
    assert "direct" not in regular
    assert direct.get("plan") == "direct"
    assert direct.get("direct") == 0.74
    assert "nothing after 1 year" in summarize_exit_load(costs["exit_load_remarks"])


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
    assert "Opening" in out
    assert "| Period |" in out
    assert "not investment advice" not in out


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

    from news_rag.insight.fund_display import strip_news_roundup

    stripped = strip_news_roundup(answer + "\n\n### What the news says\n\n- Banks fell.")
    assert "Recent news" not in stripped
    assert "What the news says" not in stripped
    assert "Bank raises guidance" not in stripped


def test_zero_placeholder_benchmark_is_omitted():
    tables = build_fund_display_tables(
        _comparison_pack({
            "1Y": {"benchmark_return": 0.0, "vs_benchmark": 0.0},
            "3Y": {"benchmark_return": 0.0, "vs_benchmark": 0.0},
            "5Y": {"benchmark_return": 0.0, "vs_benchmark": 0.0},
        }),
    )
    assert "vs_benchmark_table" not in tables


def test_returns_render_as_a_period_table():
    tables = build_fund_display_tables(
        {
            "fund:x": {
                "fund_insights": {
                    "fund_returns_pct": {
                        "1W": -4.95,
                        "1M": -8.92,
                        "3M": -6.04,
                        "6M": 0.63,
                        "YTD": -1.41,
                    }
                }
            }
        }
    )
    body = tables["fund_returns_table"]
    assert "| Period | Return |" in body
    assert "| 1W | -4.95% |" in body
    assert "| 1M | -8.92% |" in body
    assert "| YTD | -1.41% |" in body
    rendered = format_display_tables_markdown(tables)
    assert "### Returns" in rendered
    assert "Returns (horizon labelled)" not in rendered


def test_caveats_about_missing_comparison_are_removed():
    prose = (
        "DSP Nifty Smallcap is down over the past month.\n\n"
        "The data attributes only about -0.2% of the -8.92% move to named holdings, "
        "leaving most of the fall unexplained by the holdings provided.\n\n"
        "The fund does not show a benchmark or category comparison for 1M, "
        "so the gap to the index cannot be stated from the data provided.\n\n"
        "### Returns (horizon labelled)\n\n"
        "- 1W: -4.95%\n"
        "- 1M: -8.92%\n"
    )
    out = stitch_display_tables_into_answer(prose, {})
    assert "unexplained" not in out.lower()
    assert "cannot be stated" not in out.lower()
    assert "Returns (horizon labelled)" not in out
    assert "DSP Nifty Smallcap is down" in out


def test_normalize_inserts_blank_line_before_markdown_table():
    raw = "Here are five funds:\n| Fund | Score |\n|---|---|\n| A | 1 |"
    out = normalize_user_facing_text(raw)
    assert ":\n\n|" in out


def test_overview_puts_rating_and_tables_before_news():
    tables = {
        "_title": "HDFC Large Cap Fund - Growth",
        "fund_facts_table": "| Metric | Value |\n| --- | --- |\n| NAV | ₹1 |\n",
        "_heading_fund_facts_table": "### The fund",
    }
    prose = (
        "### What stands out\n\n**ICICI Bank · 9% · Banks**\n\n- Tariff news.\n\n"
        "## HDFC Large Cap Fund - Growth: overview\n\n"
        "**Asset mix:** Equity 98%.\n\n"
        "**RupeeStop rating:** Good Choice.\n"
    )
    lead = "**RupeeStop rating:** 64.55 out of 100, Good Choice."
    out = assemble_fund_overview_answer(prose, tables, rating_lead_text=lead)
    assert out.index("## HDFC Large Cap Fund") < out.index("### What stands out")
    assert "64.55 out of 100" in out.split("### What stands out")[0]
    assert "Asset mix" not in out
    assert ": overview" not in out
