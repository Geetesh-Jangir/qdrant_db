"""compare_funds conversation cache must be keyed by fund pair, not one slot per chat."""

from unittest.mock import patch

from news_rag.insight.capabilities.executor import (
    _compare_cache_label,
    _compare_payload_matches_funds,
    execute_capability,
)
from news_rag.insight.contracts import ToolCall
from news_rag.insight.memory.evidence import remember_slice


def test_compare_payload_matches_funds():
    data = {
        "funds": [
            {"fund_name": "ICICI Prudential Aggressive Hybrid Fund"},
            {"fund_name": "SBI Aggressive Hybrid Fund"},
        ],
    }
    assert _compare_payload_matches_funds(
        ["ICICI Prudential Aggressive Hybrid Fund", "SBI Aggressive Hybrid Fund"],
        data,
    )
    assert not _compare_payload_matches_funds(
        ["ICICI Prudential Conservative Hybrid Fund", "ICICI Prudential Aggressive Hybrid Fund"],
        data,
    )


def test_compare_conversation_cache_does_not_reuse_different_pair():
    conv = "unit-test-compare-pair-cache"
    conservative_aggressive = {
        "funds": [
            {"fund_name": "ICICI Prudential Conservative Hybrid Fund"},
            {"fund_name": "ICICI Prudential Aggressive Hybrid Fund"},
        ],
        "holding_overlap": {
            "fund_names": [
                "ICICI Prudential Conservative Hybrid Fund",
                "ICICI Prudential Aggressive Hybrid Fund",
            ],
        },
    }
    old_label = "compare_funds"
    remember_slice(conv, old_label, "compare_funds", {"mode": "both"}, conservative_aggressive, turn=1)

    aggressive_pair = [
        "ICICI Prudential Aggressive Hybrid Fund",
        "SBI Aggressive Hybrid Fund",
    ]
    new_label = _compare_cache_label(aggressive_pair)
    assert new_label != old_label

    call = ToolCall(tool="compare_funds", wave=1, arguments={"mode": "both"})
    ctx = {"conversation_id": conv, "conversation_turn": 2}
    runs = {"n": 0}

    def fake_compare(fund_names, args, context):
        runs["n"] += 1
        return {
            "ok": True,
            "data": {"funds": [{"fund_name": n} for n in fund_names]},
        }

    with patch.dict(
        "news_rag.insight.capabilities.executor._RUNNERS",
        {"compare_funds": fake_compare},
    ):
        results = execute_capability(call, fund_names=aggressive_pair, ctx=ctx)

    assert runs["n"] == 1
    assert results[0].get("ok")
    assert not results[0].get("cached")
    names = [r["fund_name"] for r in (results[0].get("data") or {}).get("funds") or []]
    assert sorted(names) == sorted(aggressive_pair)


def test_compare_conversation_cache_hits_same_pair():
    conv = "unit-test-compare-pair-hit"
    pair = ["Alpha Test Fund", "Beta Test Fund"]
    label = _compare_cache_label(pair)
    payload = {"funds": [{"fund_name": n} for n in pair]}
    remember_slice(conv, label, "compare_funds", {"mode": "both"}, payload, turn=1)

    call = ToolCall(tool="compare_funds", wave=1, arguments={"mode": "both"})
    ctx = {"conversation_id": conv, "conversation_turn": 2}
    runs = {"n": 0}

    def fake_compare(fund_names, args, context):
        runs["n"] += 1
        return {"ok": True, "data": payload}

    with patch.dict(
        "news_rag.insight.capabilities.executor._RUNNERS",
        {"compare_funds": fake_compare},
    ):
        results = execute_capability(call, fund_names=pair, ctx=ctx)

    assert runs["n"] == 0
    assert results[0].get("cached")
