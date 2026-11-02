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


def test_investor_holdings_cache_does_not_cover_pnl_summary_request():
    holdings_only = {
        "meta": {"as_of_date": "2026-11-02"},
        "holdings": [{"scheme_name": "A", "aum_inr": 100, "invested_inr": 90, "gain_loss_inr": 10}],
    }
    assert _return_slice_covers(
        "get_investor_portfolio",
        {"modules": ["pnl_summary"]},
        holdings_only,
    ) is False
    assert _return_slice_covers(
        "get_investor_portfolio",
        {"modules": ["holdings"]},
        holdings_only,
    ) is True


def test_investor_slice_keys_differ_by_modules():
    from news_rag.insight.memory.evidence import slice_slot

    a = slice_slot("get_investor_portfolio", {"modules": ["holdings"]})
    b = slice_slot("get_investor_portfolio", {"modules": ["pnl_summary"]})
    assert a != b


def test_rollup_summary_from_holdings_survives_grounding():
    from news_rag.insight.grounding import cores_in_text, derived_cores, strip_ungrounded_numbers
    from news_rag.insight.pack_sanitize import sanitize_data_pack_for_composer

    pack, _ = sanitize_data_pack_for_composer(
        {
            "investor_portfolio": {
                "holdings": [
                    {"invested_inr": 10000, "aum_inr": 10500, "gain_loss_inr": 500},
                    {"invested_inr": 5000, "aum_inr": 5200, "gain_loss_inr": 200},
                ],
            },
        },
    )
    import json

    evidence = json.dumps({"DATA": pack}, ensure_ascii=False)
    allowed = cores_in_text(evidence) | derived_cores(cores_in_text(evidence))
    text = "**Total invested:** ₹15,000\n**Current value:** ₹15,700\n**Net gain:** ₹700"
    cleaned = strip_ungrounded_numbers(text, allowed)
    assert "15,000" in cleaned or "15000" in cleaned.replace(",", "")
    assert "15,700" in cleaned or "15700" in cleaned.replace(",", "")
