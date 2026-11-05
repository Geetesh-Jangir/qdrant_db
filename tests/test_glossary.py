from news_rag.insight.glossary import (
    asks_precise_definition,
    direct_glossary_reply,
    glossary_execution_plan,
)
from news_rag.insight.slot_router import slot_route


def test_expense_ratio_meaning_and_judgment_uses_composer(monkeypatch):
    from types import SimpleNamespace

    from news_rag.insight.contracts import EvidencePack
    from news_rag.insight.graph import COMPOSE_SYSTEM, GraphState, node_compose
    from news_rag.insight.plan import parse_plan
    from news_rag.insight import graph as graph_mod

    question = (
        "what is the expense ratio of the hdfc large cap fund and what it means "
        "and is having low or high ratio is good or not?"
    )
    plan = parse_plan(
        {
            "scope": {"kind": "in_scope"},
            "understanding": {"goal": "Expense ratio", "intent": "lookup", "answer_mode": "DATA_ONLY"},
            "entities": {"funds": ["HDFC Large Cap Fund"]},
            "tool_calls": [{"tool": "get_fund_data", "arguments": {"modules": ["snapshot"]}, "wave": 1}],
            "presentation": {"response_shape": "short_answer", "max_words": 50},
        }
    )
    assert plan.requires_compose is True

    seen: dict[str, str] = {}

    def fake_llm(**kwargs):
        seen["system"] = kwargs.get("system_prompt") or ""
        seen["user"] = kwargs.get("user_content") or ""
        return SimpleNamespace(
            raw_text=(
                "HDFC Large Cap Fund's regular expense ratio is **1.58%**. "
                "That is the annual fee taken from the fund's assets. "
                "A lower ratio is generally better for the investor."
            ),
            provider="anthropic",
            model="test",
            input_tokens=1,
            output_tokens=20,
        )

    monkeypatch.setattr(graph_mod, "call_insight_llm", fake_llm)
    monkeypatch.setattr(graph_mod, "llm_api_key_configured", lambda *_a, **_k: True)
    monkeypatch.setattr(graph_mod, "composer_model", lambda *_a, **_k: "test")

    state = GraphState(question=question, plan=plan)
    state.evidence_pack = EvidencePack(
        data_pack={
            "fund:hdfc": {
                "fund_name": "HDFC Large Cap Fund - Growth",
                "snapshot": {
                    "fund_name": "HDFC Large Cap Fund - Growth",
                    "nav": 1292.0,
                    "expense_ratio": {"regular": 1.58, "as_on_date": "2026-09-30"},
                },
            }
        }
    )
    node_compose(state)
    assert seen["system"].startswith(COMPOSE_SYSTEM)
    assert "one specific figure" not in seen["system"].lower()
    assert "Current NAV" not in (state.answer or "")
    assert "1.58" in (state.answer or "")
    assert "annual fee" in (state.answer or "").lower()


def test_nav_full_form_direct_reply():
    q = "what is the full form of nav?"
    assert asks_precise_definition(q)
    reply = direct_glossary_reply(q)
    assert reply
    assert "Net Asset Value" in reply
    plan = glossary_execution_plan(q)
    assert plan is not None
    assert plan.direct_reply
    assert not plan.tool_calls
    assert plan.max_words <= 40


def test_slot_router_glossary_no_tools():
    q = "what is the full form of nav?"
    plan = slot_route(q, confidence_threshold=0.97)
    assert plan is not None
    assert plan.direct_reply
    assert "Net Asset Value" in plan.direct_reply
    assert plan.tool_names == []


def test_rs_rating_question_is_a_composer_concept_not_a_tool_call():
    assert direct_glossary_reply("what is rs rating") is None
    plan = slot_route("How can a fund be a Good Choice and still have Very High risk?", confidence_threshold=0.97)
    assert plan is not None
    assert plan.tool_names == []
    assert plan.requires_compose is True
    assert "four pillars" in plan.concept_brief
    assert plan.funds == []


def test_fund_nav_not_glossary():
    q = "what is the nav of Axis ELSS Tax Saver Fund"
    assert not asks_precise_definition(q)
