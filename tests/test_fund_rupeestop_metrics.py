from news_rag.fund_rupeestop_metrics import (
    asks_fund_category_average,
    build_comparison_periods,
    normalize_category_average_returns,
    normalize_vs_benchmark_payload,
    periods_requested_in_question,
    resolve_display_periods,
)


def test_vs_benchmark_skips_10y_and_inception():
    payload = {
        "data": {
            "benchmark_name": "nifty 100 tri",
            "periods": {
                "1y": {"fund_return": -10.77, "benchmark_return": -5.18, "vs_benchmark": -5.59, "peer_return": -1.64},
                "10y": {"fund_return": 1.0, "benchmark_return": 2.0, "vs_benchmark": -1.0},
                "inception": {"fund_return": 17.0},
            },
        }
    }
    out = normalize_vs_benchmark_payload(payload)
    assert out is not None
    assert set(out["periods"].keys()) == {"1Y"}


def test_category_averages_parsed():
    raw = {
        "returns": {
            "1m": -5.08,
            "3m": -5.1,
            "6m": -4.58,
            "1y": -8.99,
            "3y": 8.62,
            "5y": 6.79,
            "inception": 10.44,
            "as_of": "2026-10-23",
        }
    }
    out = normalize_category_average_returns(raw)
    assert "1M" in out
    assert "1Y" in out
    assert "inception".upper() not in out


def test_fund_return_from_detail_not_vs_api():
    detail = {"returns": {"1y": -10.77, "3y": 6.91, "5y": 7.78}}
    vs = normalize_vs_benchmark_payload(
        {
            "data": {
                "benchmark_name": "nifty 100 tri",
                "periods": {
                    "1y": {"fund_return": -99.0, "benchmark_return": -5.18, "vs_benchmark": -93.0},
                    "3y": {"benchmark_return": 7.8},
                    "5y": {"benchmark_return": 7.06},
                },
            }
        }
    )
    cat = {"1Y": -8.99, "3Y": 8.62, "5Y": 6.79}
    comp = build_comparison_periods(detail, vs, cat)
    assert comp["1Y"]["fund_return"] == -10.77
    assert comp["1Y"]["benchmark_return"] == -5.18
    assert comp["1Y"]["vs_benchmark"] == -5.59
    assert comp["1Y"]["category_average_return"] == -8.99
    assert comp["1Y"]["vs_category"] == round(-10.77 - (-8.99), 2)


def test_unknown_period_falls_back_to_135y():
    long_rows, short_rows = resolve_display_periods(periods_requested_in_question("returns for 2 years"))
    assert long_rows == ["1Y", "3Y", "5Y"]
    assert short_rows == []


def test_category_avg_question_detected():
    assert asks_fund_category_average("what is the category avg of hdfc large cap fund for 1,3,5 y")
