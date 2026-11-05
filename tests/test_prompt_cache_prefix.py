"""Planner and composer must share one Anthropic cache prefix and must not put tools in front of it."""

from news_rag.insight.graph import COMPOSE_SYSTEM
from news_rag.insight.plan import plan_system_prompt
from news_rag.llm_client import build_anthropic_messages_body
from news_rag.prompts import shared_system_prefix


def _body(role: str, *, schema: dict | None = None) -> dict:
    return build_anthropic_messages_body(
        model="claude-haiku-5-5",
        max_tokens=1800,
        cached_prefix=shared_system_prefix(),
        role_prompt=role,
        user_content="Question:\nwhat is happening?",
        response_schema=schema,
        tool_use_enabled=True,
    )


def test_planner_and_composer_share_the_first_system_block():
    prefix = shared_system_prefix()
    planner = _body(plan_system_prompt() + "\n\nReturn a JSON object that matches this schema:\n{}", schema={"type": "object"})
    composer = _body(COMPOSE_SYSTEM)

    assert planner["system"][0]["text"] == composer["system"][0]["text"] == prefix
    assert planner["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert composer["system"][1]["cache_control"]["ttl"] == "1h"
    assert "tools" not in planner
    assert "tool_choice" not in planner
    assert "tools" not in composer
    assert planner["system"][1]["text"] != composer["system"][1]["text"]
    assert "You are the planner" in planner["system"][1]["text"]
    assert prefix not in planner["system"][1]["text"]
    assert "ROLE: COMPOSER" in composer["system"][1]["text"]
    assert "senior financial analyst" not in COMPOSE_SYSTEM
    assert "MARKDOWN LAYOUT" not in COMPOSE_SYSTEM
    assert "MARKDOWN LAYOUT" in prefix


def test_tools_stay_available_when_there_is_no_shared_prefix():
    body = build_anthropic_messages_body(
        model="claude-haiku-5-5",
        max_tokens=200,
        cached_prefix="",
        role_prompt="Return JSON.",
        user_content="hi",
        response_schema={"type": "object"},
        tool_use_enabled=True,
    )
    assert "tools" in body
    assert body["system"][0]["cache_control"]["ttl"] == "1h"
