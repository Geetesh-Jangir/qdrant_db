"""call_json_llm schema delivery and truncation repair."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from news_rag.ask_plan import AskPlan
from news_rag.llm_client import call_json_llm
from news_rag.llm_text import salvage_truncated_json
from news_rag.tools import _layered_news_topics


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        rag_llm_provider="gemini",
        gemini_api_key="test-key",
        gemini_model="gemini-test",
        gemini_base_url="https://example.googleapis.com/v1beta",
        deepseek_api_key="",
        deepseek_model="deepseek-test",
        deepseek_base_url="https://api.deepseek.com",
        llm_max_tokens=2000,
        rag_router_model="",
    )


def _gemini_response(text: str, finish: str = "STOP") -> MagicMock:
    response = MagicMock()
    response.status_code = 200
    response.text = text
    response.json.return_value = {
        "candidates": [
            {
                "content": {"parts": [{"text": text}]},
                "finishReason": finish,
            }
        ],
        "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "totalTokenCount": 15},
    }
    return response


def _client(responses: list[MagicMock]) -> MagicMock:
    client = MagicMock()
    client.post.side_effect = responses
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    return client


@patch("news_rag.llm_client.httpx.Client")
@patch("news_rag.llm_client.get_settings")
def test_gemini_request_includes_response_schema(mock_settings, mock_client_cls):
    mock_settings.return_value = _settings()
    mock_client_cls.return_value = _client([_gemini_response('{"status": "ready", "why": "enough"}')])
    schema = {"type": "object", "properties": {"status": {"type": "string"}}}
    result = call_json_llm(
        system_prompt="Return JSON",
        user_content="",
        context_blocks=[{"name": "question", "text": "What moved the market?"}],
        response_schema=schema,
        stage="agent",
        max_tokens=800,
    )
    payload = mock_client_cls.return_value.post.call_args.kwargs["json"]
    assert payload["generationConfig"]["responseSchema"] == schema
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert any("What moved the market?" in part["parts"][0]["text"] for part in payload["contents"])
    assert result.parsed == {"status": "ready", "why": "enough"}
    assert result.repaired is False


@patch("news_rag.llm_client.httpx.Client")
@patch("news_rag.llm_client.get_settings")
def test_truncated_json_triggers_one_repair_call(mock_settings, mock_client_cls):
    mock_settings.return_value = _settings()
    mock_client_cls.return_value = _client(
        [
            _gemini_response('{"status": "need_tools"', finish="MAX_TOKENS"),
            _gemini_response('{"status": "ready", "why": "complete"}', finish="STOP"),
        ]
    )
    result = call_json_llm(
        system_prompt="Return JSON",
        user_content="Question",
        response_schema={"type": "object"},
        max_tokens=800,
    )
    assert mock_client_cls.return_value.post.call_count == 2
    assert result.repaired is True
    assert result.parsed == {"status": "ready", "why": "complete"}
    repair_body = mock_client_cls.return_value.post.call_args_list[1].kwargs["json"]
    repair_text = repair_body["contents"][0]["parts"][0]["text"]
    assert "cut off" in repair_text
    assert '{"status": "need_tools"' in repair_text


def test_salvage_closes_a_cut_off_composer_object():
    raw = '{"headline": "Banks are leading", "narrative": "Lenders rose after the policy hold'
    parsed = salvage_truncated_json(raw)
    assert parsed is not None
    assert parsed["headline"] == "Banks are leading"
    assert "Lenders rose" in parsed["narrative"]


@patch("news_rag.llm_client.httpx.Client")
@patch("news_rag.llm_client.get_settings")
def test_composer_keeps_truncated_answer_without_a_second_call(mock_settings, mock_client_cls):
    mock_settings.return_value = _settings()
    raw = '{"headline": "Markets are firm", "narrative": "Banks led the session after earnings'
    mock_client_cls.return_value = _client([_gemini_response(raw, finish="MAX_TOKENS")])
    result = call_json_llm(
        system_prompt="Return JSON",
        user_content="Question",
        response_schema={"type": "object"},
        stage="composer",
        max_tokens=800,
    )
    assert mock_client_cls.return_value.post.call_count == 1
    assert result.parsed["headline"] == "Markets are firm"
    assert "Banks led" in result.parsed["narrative"]


def test_macro_news_does_not_use_the_user_sentence_as_a_topic():
    sentence = "whats happening in the market right now?"
    assert _layered_news_topics("macro_news", sentence) == []
    assert _layered_news_topics("sector_news", sentence) == []
    assert _layered_news_topics("sector_news", "banking sector") == ["banking sector"]


def test_ask_plan_keeps_rich_agent_fields():
    plan = AskPlan.from_dict(
        {
            "status": "need_tools",
            "question_reading": {
                "intent": "Explain the oil move for this fund",
                "answer_shape": "narrative",
                "must_cover": ["direct weight", "indirect channel"],
                "sentiment": "negative",
                "declined_parts": ["should I sell"],
            },
            "entities": [
                {
                    "raw": "PPFAS",
                    "role": "fund_scheme",
                    "cleaned_phrase": "Parag Parikh Flexi Cap Fund",
                    "why": "named fund",
                }
            ],
            "relationships_to_check": [
                {"driver": "crude oil", "target": "Parag Parikh Flexi Cap Fund", "kind_guess": "indirect"}
            ],
            "information_gaps": ["sector weights"],
            "tools": [
                {
                    "tool": "fund_top_sectors",
                    "purpose": "see if energy is a direct weight",
                    "depends_on": "",
                    "fund_entity_index": 0,
                }
            ],
        }
    )
    assert plan.question_reading["answer_shape"] == "narrative"
    assert plan.relationships_to_check[0]["driver"] == "crude oil"
    assert plan.information_gaps == ["sector weights"]
    assert plan.tools[0].purpose.startswith("see if energy")
    assert plan.tools[0].depends_on == ""
    assert plan.entities[0].why == "named fund"
    assert plan.sentiment == "negative"
    assert plan.declined_parts == ["should I sell"]
    assert "oil move" in plan.answer_parts
    json.dumps(plan.raw_json)
