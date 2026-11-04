from news_rag.insight.contracts import AnswerMode, ExecutionPlan
from news_rag.insight.fact_answer import (
    field_answer_needs_composer,
    is_pure_field_answer,
    render_fact_answer,
    render_investor_rs_ratings_table,
)


def _plan(*fields: str) -> ExecutionPlan:
    return ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        funds=["HDFC Large Cap Fund - Growth"],
        asked_fields=list(fields),
    )


def test_single_nav_is_one_sentence():
    pack = {
        "fund:HDFC Large Cap Fund - Growth": {
            "snapshot": {"fund_name": "HDFC Large Cap Fund - Growth", "nav": 1123.45, "nav_date": "3 Nov 2026", "aum": 99},
        }
    }
    text = render_fact_answer(_plan("nav"), pack)
    assert "1,123.45" in text
    assert "AUM" not in text
    assert text.count("\n") == 0


def test_aum_and_expense_both_appear():
    pack = {
        "fund:HDFC Large Cap Fund - Growth": {
            "snapshot": {
                "fund_name": "HDFC Large Cap Fund - Growth",
                "nav": 10,
                "aum": 25000.5,
                "expense_ratio": {"regular": 1.25},
            },
        }
    }
    text = render_fact_answer(_plan("aum", "expense_ratio"), pack)
    assert "25,000.50" in text
    assert "1.25%" in text
    assert "NAV" not in text


def test_missing_field_does_not_dump_the_snapshot():
    pack = {
        "fund:HDFC Large Cap Fund - Growth": {
            "snapshot": {"fund_name": "HDFC Large Cap Fund - Growth", "nav": 10},
        }
    }
    text = render_fact_answer(_plan("exit_load"), pack)
    assert "not available" in text
    assert "NAV" not in text


def test_identity_sentence():
    pack = {
        "fund:HDFC Large Cap Fund - Growth": {
            "snapshot": {
                "fund_name": "HDFC Large Cap Fund - Growth",
                "category": "Large Cap",
                "scheme_type": "Equity",
                "aum": 1000,
                "nav": 50,
                "nav_date": "1 Nov 2026",
            },
        }
    }
    text = render_fact_answer(_plan("identity"), pack)
    assert "Large Cap" in text
    assert "equity" in text.lower()
    assert "1,000.00" in text
    assert "50.00" in text


def test_definition_plus_figure_is_not_a_pure_template():
    plan = _plan("exit_load")
    assert not is_pure_field_answer(plan, "what is exit load and what is it for hdfc large cap")
    assert is_pure_field_answer(plan, "what is the exit load of hdfc large cap")


def test_benchmark_return_uses_vs_benchmark_period():
    pack = {
        "fund:HDFC Large Cap Fund - Growth": {
            "snapshot": {"benchmark": "NIFTY 100 - TRI", "returns": {"1Y": -5.67}},
            "vs_benchmark": {
                "benchmark_name": "NIFTY 100 - TRI",
                "periods": {"1Y": {"benchmark_return": -8.69, "fund_return": -5.67}},
            },
        }
    }
    text = render_fact_answer(_plan("benchmark_return"), pack, "what is the benchmark return in last 1 year")
    assert "-8.69%" in text
    assert "-5.67%" not in text


def test_comparison_table_from_pack():
    from news_rag.insight.contracts import EvidencePack
    from news_rag.insight.fact_answer import render_benchmark_comparison_table

    data = {
        "fund:HDFC Large Cap Fund - Growth": {
            "vs_benchmark": {
                "benchmark_name": "nifty 100 tri",
                "periods": {
                    "1Y": {"fund_return": -5.67, "benchmark_return": -8.69, "peer_return": -7.1},
                    "3Y": {"fund_return": 8.66, "benchmark_return": 9.08, "peer_return": 8.11},
                    "5Y": {"fund_return": 9.26, "benchmark_return": 7.21, "peer_return": 5.87},
                },
            },
            "fund_insights": {
                "comparison_periods": {
                    "1Y": {
                        "fund_return": -5.67,
                        "benchmark_return": -8.69,
                        "category_average_return": -4.11,
                        "vs_category": -1.56,
                    },
                    "3Y": {
                        "fund_return": 8.66,
                        "benchmark_return": 9.08,
                        "category_average_return": 10.29,
                        "vs_category": -1.63,
                    },
                    "5Y": {
                        "fund_return": 9.26,
                        "benchmark_return": 7.21,
                        "category_average_return": 7.97,
                        "vs_category": 1.29,
                    },
                }
            },
        }
    }
    plan = _plan("vs_benchmark", "category_avg")
    pack = EvidencePack(data_pack=data)
    table = render_benchmark_comparison_table(pack, plan, "do benchmark vs fund vs category average")
    assert "| 1Y |" in table
    assert "-8.69%" in table
    assert "-4.11%" in table
    assert "| 3Y |" in table
    assert "| 5Y |" in table


def test_three_way_compare_is_not_pure_field_template():
    from news_rag.insight.fields import wants_comparison_table

    plan = _plan("vs_benchmark", "category_avg")
    q = "do benchmark vs fund vs category average"
    assert wants_comparison_table(q, plan)
    assert not is_pure_field_answer(plan, q)


def test_all_holdings_rs_uses_composer_not_field_template():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        holding_scope="all_holdings",
        asked_fields=["holding_rs_labels"],
    )
    holdings = [{"scheme_name": f"Fund {i}", "rs_label": "Good", "rs_score": 60.0 + i} for i in range(8)]
    pack = {"investor_portfolio": {"holdings": holdings}}
    assert not is_pure_field_answer(plan, "rs rating of all my funds", pack)
    assert field_answer_needs_composer(plan, pack, "")


def test_investor_rs_table_includes_scores():
    plan = ExecutionPlan(
        holding_scope="all_holdings",
        asked_fields=["holding_rs_labels"],
    )
    pack = {
        "investor_portfolio": {
            "holdings": [
                {"scheme_name": "Alpha Fund", "rs_label": "Recommended", "rs_score": 79.0, "aum_inr": 100},
            ]
        }
    }
    table = render_investor_rs_ratings_table(plan, pack, "rs rating of all my funds")
    assert "| Alpha Fund | Recommended | 79.00 |" in table
    assert is_pure_field_answer(plan, "rs rating of all my funds", pack)


def test_investor_rs_metric_table_from_portfolio_only():
    from news_rag.insight.sector_exposure_tables import render_all_holdings_metric_table

    plan = ExecutionPlan(
        holding_scope="all_holdings",
        asked_fields=["holding_rs_labels"],
        funds=["Alpha Fund"],
    )
    memory = {"holdings_in_chat": [{"name": "Alpha Fund"}]}
    pack = {
        "investor_portfolio": {
            "holdings": [{"scheme_name": "Alpha Fund", "rs_label": "Recommended", "rs_score": 79.0}],
        }
    }
    table = render_all_holdings_metric_table(plan, [], memory, data_pack=pack)
    assert "Recommended" in table
    assert "79" in table


def test_book_value_sentence():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        asked_fields=["book_value", "invested"],
    )
    text = render_fact_answer(
        plan,
        {"investor_portfolio": {"summary": {"aum_inr": 500000, "invested_inr": 400000}}},
    )
    assert "5,00,000.00" in text or "500,000.00" in text
    assert "400,000.00" in text
