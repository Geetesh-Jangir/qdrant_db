"""Hard Ask cases — LLM ask engine (requires live LLM + Qdrant; skipped in default CI)."""

from __future__ import annotations

import pytest

from news_rag.ask_eval import HARD_ASK_CASES, HardAskCase, validate_ask_response

ROUTING_CASES = [c for c in HARD_ASK_CASES if c.routing_only]
E2E_CASES = [c for c in HARD_ASK_CASES if not c.routing_only]


@pytest.mark.skip(reason="Legacy query_router removed from /api/ask; use planner integration tests.")
@pytest.mark.parametrize("case", ROUTING_CASES, ids=[c.id for c in ROUTING_CASES])
def test_hard_routing(case: HardAskCase) -> None:
    assert case.id


@pytest.mark.skip(reason="Legacy retrieve/generate_answer removed; run eval with live LLM separately.")
@pytest.mark.parametrize("case", E2E_CASES, ids=[c.id for c in E2E_CASES])
def test_hard_ask_pipeline(case: HardAskCase) -> None:
    result = {"insight": "", "intent": "general"}
    fails = validate_ask_response(case, result)
    assert not fails, f"{case.id}: {fails}"
