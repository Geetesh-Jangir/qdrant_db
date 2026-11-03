from news_rag.insight.graph import COMPOSE_SYSTEM, COMPOSE_SYSTEM_FACTS


def test_compose_prompts_use_you_voice():
    assert "**you**" in COMPOSE_SYSTEM
    assert "an investor" not in COMPOSE_SYSTEM_FACTS.lower()
    assert "one note for you" in COMPOSE_SYSTEM_FACTS.lower()
