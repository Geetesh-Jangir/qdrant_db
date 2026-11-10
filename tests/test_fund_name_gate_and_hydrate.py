"""Fund name gate and memory hydration after server restart."""

from news_rag.insight.contracts import ExecutionPlan, ScopeKind, ToolCall
from news_rag.insight.fund_name_gate import clarify_plan_if_fund_unknown
from news_rag.insight.graph import GraphState, _load_planner_memory
from news_rag.insight.memory.hydrate import hydrate_memory_from_prior_turns, normalize_prior_turns
from news_rag.insight.memory.prompt import chat_history_view
from news_rag.insight.memory.store import get_memory, reset_memory


def test_clarify_generic_limits_without_fund_name():
    plan = ExecutionPlan(
        funds=["SBI Children's Fund"],
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["limits"]},
            )
        ],
    )
    out = clarify_plan_if_fund_unknown(plan, None, "What is the monthly investment limit?")
    assert out.scope_kind == ScopeKind.NEEDS_CLARIFICATION
    assert not out.tool_calls
    assert not out.funds
    assert "Which mutual fund" in (out.direct_reply or "")


def test_planner_needs_clarification_cleared_when_icici_fund_bound_from_chat():
    q = "TELL ME ABOUT THE ICICI FUND AND WHAT IS ITS OVERALL PERFORMANCE AND ITS FUND MANAGERS"
    assistant = (
        "Four debt funds:\n"
        "- **ICICI Prudential Liquid Fund - Growth**\n"
        "- Axis Liquid Fund - Regular Plan - Growth"
    )
    memory = {"chat_turns": [{"user": "name debt funds", "assistant": assistant}]}
    plan = ExecutionPlan(
        scope_kind=ScopeKind.NEEDS_CLARIFICATION,
        direct_reply="Which ICICI scheme?",
        funds=["ICICI Prudential Liquid Fund - Growth"],
        subject_ref="user_named",
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]})],
    )
    out = clarify_plan_if_fund_unknown(plan, memory, q)
    assert out.scope_kind == ScopeKind.IN_SCOPE
    assert out.tool_calls
    assert out.funds == ["ICICI Prudential Liquid Fund - Growth"]
    assert not (out.direct_reply or "").strip()


def test_clarify_allows_explicit_fund_in_question():
    plan = ExecutionPlan(
        funds=["HDFC Large Cap Fund"],
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["limits"]})],
    )
    out = clarify_plan_if_fund_unknown(
        plan,
        None,
        "What is the weekly SIP minimum for HDFC Large Cap Fund?",
    )
    assert out.scope_kind == ScopeKind.IN_SCOPE
    assert out.tool_calls


def test_normalize_prior_turns_skips_incomplete_assistant():
    rows = normalize_prior_turns(
        [
            {"user": "macro question", "assistant": ""},
            {
                "user": "What is the risk of HDFC Large Cap Fund?",
                "assistant": "HDFC Large Cap Fund is a large-cap equity scheme.",
            },
        ]
    )
    assert len(rows) == 1
    assert "HDFC" in rows[0]["user"]


def test_hydrate_memory_from_ui_prior_turns():
    reset_memory("conv-hydrate-ui")
    prior = [
        {
            "user": "What is the risk of HDFC Large Cap Fund?",
            "assistant": "HDFC Large Cap Fund is a large-cap equity scheme.",
        }
    ]
    state, did = hydrate_memory_from_prior_turns("conv-hydrate-ui", prior)
    assert did is True
    assert state is not None
    view = chat_history_view(state)
    assert len(view["turns"]) == 1
    frame = state.get("frame") or {}
    assert not str(frame.get("last_fund_focus") or "").strip()
    assert "HDFC Large Cap Fund" in view["turns"][0]["user"]


def test_load_planner_memory_hydrates_from_prior_context():
    reset_memory("conv-load-hydrate")
    gs = GraphState(
        question="What is the weekly limit?",
        prior_context={
            "conversation_id": "conv-load-hydrate",
            "turns": [
                {
                    "user": "HDFC Large Cap Fund expense ratio?",
                    "assistant": "The expense ratio is 1.05%.",
                }
            ],
        },
    )
    ctx = _load_planner_memory(gs)
    assert gs.memory_resynced is True
    assert ctx is not None
    assert get_memory("conv-load-hydrate") is not None


def test_load_planner_memory_ignores_incomplete_prior_turn():
    reset_memory("conv-incomplete-prior")
    gs = GraphState(
        question="whats happening in the US midterm and rupee",
        prior_context={
            "conversation_id": "conv-incomplete-prior",
            "turns": [{"user": "same question", "assistant": ""}],
        },
    )
    ctx = _load_planner_memory(gs)
    assert ctx is None
    assert get_memory("conv-incomplete-prior") is None
