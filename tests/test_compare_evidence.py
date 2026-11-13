from news_rag.insight.compare_evidence import resolve_compare_fund_pair
from news_rag.insight.contracts import ExecutionPlan, ToolCall


def test_resolve_pair_anchor_plus_screen_pick():
    plan = ExecutionPlan(
        funds=["Kotak Contra Fund - Regular Plan - Growth"],
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={
                    "pick_rating_better": True,
                    "exclude_names": ["Kotak Contra Fund - Regular Plan - Growth"],
                },
                wave=1,
            ),
        ],
    )
    wave1 = [
        {
            "tool": "screen_funds_by_exposure",
            "ok": True,
            "data": {
                "rankings": [{"fund_name": "DSP Value Fund - Regular Plan - Growth"}],
            },
        },
    ]
    pair = resolve_compare_fund_pair(plan, wave1)
    assert pair == [
        "Kotak Contra Fund - Regular Plan - Growth",
        "DSP Value Fund - Regular Plan - Growth",
    ]


def test_maybe_run_compare_retries_after_failed_compare(monkeypatch):
    from types import SimpleNamespace

    from news_rag.insight.compare_evidence import maybe_run_compare_funds_for_parties

    plan = ExecutionPlan(
        intent="compare",
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"compare_pair": True},
                wave=1,
            ),
        ],
    )
    state = SimpleNamespace(
        plan=plan,
        question="compare two random funds",
        wave1_results=[
            {"tool": "compare_funds", "ok": False, "error": "need_two_funds"},
            {
                "tool": "screen_funds_by_exposure",
                "ok": True,
                "data": {"rankings": [{"fund_name": "Fund A"}, {"fund_name": "Fund B"}]},
            },
        ],
        resolved_funds=[],
        telemetry=None,
        query_log=None,
        conversation_id=None,
        memory={},
    )

    def _fake_execute(calls, ctx, **kwargs):
        assert kwargs.get("fund_names") == ["Fund A", "Fund B"]
        return [{"tool": "compare_funds", "ok": True, "data": {"funds": []}}]

    monkeypatch.setattr(
        "news_rag.insight.capabilities.executor.execute_wave",
        _fake_execute,
    )
    maybe_run_compare_funds_for_parties(state)
    assert any(r.get("tool") == "compare_funds" and r.get("ok") for r in state.wave1_results)


def test_resolve_pair_two_screen_rankings():
    plan = ExecutionPlan(
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"compare_pair": True},
                wave=1,
            ),
        ],
    )
    wave1 = [
        {
            "ok": True,
            "tool": "screen_funds_by_exposure",
            "data": {
                "rankings": [
                    {"fund_name": "Fund A"},
                    {"fund_name": "Fund B"},
                ],
            },
        },
    ]
    assert resolve_compare_fund_pair(plan, wave1) == ["Fund A", "Fund B"]
