from news_rag.insight.capabilities.cache import CapabilityCache
from news_rag.insight.capabilities.executor import (
    _return_slice_covers,
    execute_capability,
)
from news_rag.insight.contracts import ToolCall


def test_partial_fund_payload_is_not_stored_in_capability_cache(monkeypatch):
    cache = CapabilityCache(default_ttl=60)
    monkeypatch.setattr("news_rag.insight.capabilities.executor.get_capability_cache", lambda: cache)

    def stub_runner(fund_name, args, ctx):
        return {
            "ok": True,
            "partial": True,
            "error": "incomplete_fund_modules",
            "data": {
                "fund_name": fund_name,
                "fund_insights": {"category": "Debt", "isin": "INF209K01LV0"},
            },
        }

    monkeypatch.setattr("news_rag.insight.capabilities.executor._RUNNERS", {"get_fund_data": stub_runner})
    args = {"modules": ["snapshot", "rating"], "windows": ["1M"]}
    rows = execute_capability(
        ToolCall(tool="get_fund_data", arguments=args, wave=1),
        fund_names=["ABSL Banking Fund"],
        ctx={"skip_tool_cache": False},
    )
    assert len(rows) == 1
    assert rows[0]["partial"] is True
    assert cache.get("get_fund_data", "ABSL Banking Fund|snapshot,rating|w=1M") is None


def test_complete_payload_is_stored_in_capability_cache(monkeypatch):
    cache = CapabilityCache(default_ttl=60)
    monkeypatch.setattr("news_rag.insight.capabilities.executor.get_capability_cache", lambda: cache)

    payload = {
        "fund_name": "ABSL Banking Fund",
        "snapshot": {"returns": {"1M": -0.2}},
        "rs_rating": {"final_score": 63, "label": "Good Choice"},
    }

    def stub_runner(fund_name, args, ctx):
        return {"ok": True, "partial": False, "data": payload}

    monkeypatch.setattr("news_rag.insight.capabilities.executor._RUNNERS", {"get_fund_data": stub_runner})
    args = {"modules": ["snapshot", "rating"], "windows": ["1M"]}
    execute_capability(
        ToolCall(tool="get_fund_data", arguments=args, wave=1),
        fund_names=["ABSL Banking Fund"],
    )
    stored = cache.get("get_fund_data", "ABSL Banking Fund|snapshot,rating|w=1M")
    assert stored == payload
    assert _return_slice_covers("get_fund_data", args, stored)
