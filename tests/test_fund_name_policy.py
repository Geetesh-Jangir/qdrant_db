"""Fund authorization must not treat clarification examples as named schemes."""

from __future__ import annotations

from news_rag.insight.fund_name_gate import _FUND_NAME_PROMPT
from news_rag.insight.fund_name_policy import fund_authorized_for_question
from news_rag.insight.memory.fund_context import compare_side_in_chat


def test_clarification_example_does_not_authorize_wrong_fund() -> None:
    memory = {
        "chat_turns": [
            {
                "user": "tell me about hdfc large and mid cap fund",
                "assistant": _FUND_NAME_PROMPT,
            }
        ]
    }
    q = "tell me about hdfc large and mid cap fund"
    wrong = "HDFC Large Cap Fund - Growth"
    assert not fund_authorized_for_question(wrong, q, memory)
    assert not compare_side_in_chat(wrong, memory, q)


def test_catalog_resolve_authorizes_correct_fund() -> None:
    q = "tell me about hdfc large and mid cap fund"
    right = "HDFC Large & Mid Cap Fund - Regular Plan - Growth"
    assert fund_authorized_for_question(right, q, None)