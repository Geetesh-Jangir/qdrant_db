"""Hard Ask cases — routing + pipeline (retrieve + generate_answer)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from news_rag.answer import generate_answer
from news_rag.ask_eval import HARD_ASK_CASES, HardAskCase, validate_ask_response
from news_rag.query_router import route_query
from news_rag.retrieve import retrieve_for_question

ROUTING_CASES = [c for c in HARD_ASK_CASES if c.routing_only]
E2E_CASES = [c for c in HARD_ASK_CASES if not c.routing_only]

_DUMMY_VECTOR = [0.0] * 384


def _run_ask_pipeline(question: str) -> dict:
    with patch("news_rag.retrieve.embed_query", return_value=_DUMMY_VECTOR):
        with patch("news_rag.embed.embed_query", return_value=_DUMMY_VECTOR):
            with patch("news_rag.retrieve.QdrantReader") as mock_reader:
                mock_reader.return_value.query_vector.return_value = []
                mock_reader.return_value.scroll_filtered.return_value = []
                parsed, articles = retrieve_for_question(question)
                return generate_answer(parsed, articles)


@pytest.mark.parametrize("case", ROUTING_CASES, ids=[c.id for c in ROUTING_CASES])
def test_hard_routing(case: HardAskCase) -> None:
    r = route_query(case.question)
    fake = {"intent": r.intent, "insight_source": "", "insight_summary": "", "insight": ""}
    fails = validate_ask_response(case, fake)
    assert not fails, fails


@pytest.mark.parametrize("case", E2E_CASES, ids=[c.id for c in E2E_CASES])
def test_hard_ask_pipeline(case: HardAskCase) -> None:
    result = _run_ask_pipeline(case.question)
    fails = validate_ask_response(case, result)
    assert not fails, f"{case.id}: {fails}"
