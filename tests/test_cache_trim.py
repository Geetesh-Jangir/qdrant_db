from news_rag.insight.capabilities.executor import _return_slice_covers, _trim_cached_to_ask


def _wide():
    return {
        "fund_name": "X Fund",
        "snapshot": {"nav": 10, "returns": {"1M": 1.0, "1Y": 12.0, "3Y": 11.0}},
        "composition": {"equity": 90},
        "risk": {"label": "High"},
    }


def test_wider_cached_fund_payload_covers_and_trims_to_the_ask():
    args = {"modules": ["snapshot"], "windows": ["1M"]}
    data = _wide()
    assert _return_slice_covers("get_fund_data", args, data)
    out = _trim_cached_to_ask("get_fund_data", args, data)
    assert out["snapshot"]["returns"] == {"1M": 1.0}
    assert "composition" not in out and "risk" not in out
    assert out["fund_name"] == "X Fund"
    assert data["snapshot"]["returns"]["1Y"] == 12.0  # cache is not mutated


def test_missing_window_is_not_covered():
    assert not _return_slice_covers("get_fund_data", {"modules": ["snapshot"], "windows": ["6M"]}, _wide())
