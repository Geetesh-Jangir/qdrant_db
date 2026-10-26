from news_rag.insight.evidence_pack import _fund_performance_digest
from news_rag.insight.question_intent import prefers_planner_over_slot


def test_performance_digest_from_snapshot():
    digest = _fund_performance_digest(
        {
            "fund:HDFC Large Cap": {
                "snapshot": {
                    "fund_name": "HDFC Large Cap Fund",
                    "nav": 1020.5,
                    "day_change_pct": -0.42,
                    "returns": {"1M": 2.1, "3M": 5.5, "1Y": 18.2},
                    "benchmark": "NIFTY 100 TRI",
                    "category": "Large Cap",
                },
                "attribution": {
                    "fund_return": -1.2,
                    "detractors": [{"stock": "Reliance", "contribution_pct": -0.3}],
                },
            },
            "market": {
                "index_return": {
                    "scheme_benchmark_name": "NIFTY 100 TRI",
                    "nifty50_reference": {"returns_pct": {"1M": -2.09}},
                }
            },
        }
    )
    assert digest["nav"] == 1020.5
    assert digest["returns_pct"]["1Y"] == 18.2
    assert digest["scheme_benchmark_name"] == "NIFTY 100 TRI"
    assert digest["nifty50_returns_pct"]["1M"] == -2.09


def test_fund_news_does_not_force_planner():
    q = "tell me about the news related to the hdfc large cap fund?"
    assert prefers_planner_over_slot(q) is False
