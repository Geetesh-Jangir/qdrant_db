from news_rag.insight.capabilities.executor import _detail_for_fund_tool, _run_get_fund_data


def test_detail_for_fund_tool_prefers_live_api_by_memory_isin(monkeypatch):
    stub = {"isin": "INF209K01LV0", "category": "Debt", "fund_name": "ABSL"}
    live = {
        "isin": "INF209K01LV0",
        "category": "banking and psu",
        "fund_name": "ABSL Banking Fund",
        "nav": 386.0,
        "returns": {"1y": 3.0},
    }

    class Index:
        def get_fund_detail(self, isin):
            assert isin == "INF209K01LV0"
            return live

    monkeypatch.setattr("news_rag.fund_search.get_fund_index", lambda: Index())
    monkeypatch.setattr(
        "news_rag.fund_search.resolve_fund_for_query",
        lambda *a, **k: (stub, False, []),
    )
    out = _detail_for_fund_tool("ABSL Banking Fund", {"fund_isin": "INF209K01LV0"})
    assert out is not None
    assert out.get("category") == "banking and psu"
    assert out.get("nav") == 386.0


def test_snapshot_only_attaches_fund_insights_from_catalog(monkeypatch):
    detail = {
        "isin": "INF209K01LV0",
        "fund_name": "ABSL Banking & PSU Debt",
        "category": "Banking and PSU",
        "returns": {"1y": 6.1, "3y": 7.2, "5y": 6.8},
        "category_average_returns": {"1Y": 5.9, "3Y": 7.0, "5Y": 6.5},
    }

    monkeypatch.setattr(
        "news_rag.fund_search.resolve_fund_for_query",
        lambda *args, **kwargs: (detail, None, []),
    )
    monkeypatch.setattr(
        "news_rag.insight.capabilities.executor._detail_for_fund_tool",
        lambda name, ctx: detail,
    )
    monkeypatch.setattr(
        "news_rag.insight.layer_tools.run_fund_snapshot",
        lambda ctx: {
            "ok": True,
            "data": {
                "fund_name": ctx["fund_name"],
                "category": "banking and psu",
                "returns": {"1M": -0.27},
            },
        },
    )
    monkeypatch.setattr("news_rag.fund_risk.fetch_public_rating", lambda isin: {"final_score": 63})

    payload = _run_get_fund_data("ABSL Banking Fund", {"modules": ["snapshot"], "windows": ["1M"]}, {})
    out = payload.get("data") or {}
    insights = out.get("fund_insights") or {}
    assert insights.get("category") == "Banking and PSU"
    assert insights.get("category_average_returns_pct") == {"1Y": 5.9, "3Y": 7.0, "5Y": 6.5}
    assert "vs_benchmark" not in out
