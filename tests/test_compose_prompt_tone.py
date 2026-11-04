from news_rag.insight.graph import COMPOSE_SYSTEM, COMPOSE_SYSTEM_FACTS
from news_rag.prompts import FINANCIAL_SYSTEM_BASE


def test_compose_prompts_use_you_voice():
    assert "**you**" in COMPOSE_SYSTEM
    assert "an investor" not in COMPOSE_SYSTEM_FACTS.lower()
    assert "one note for you" in COMPOSE_SYSTEM_FACTS.lower()


def test_compose_prompts_indian_rupee_grouping_from_one_lakh():
    assert "Indian comma" in COMPOSE_SYSTEM or "Indian commas" in COMPOSE_SYSTEM
    assert "1,00,000" in COMPOSE_SYSTEM
    assert "₹1 lakh" in COMPOSE_SYSTEM or "1 lakh" in COMPOSE_SYSTEM
    assert "Indian comma grouping" in FINANCIAL_SYSTEM_BASE
