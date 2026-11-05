from news_rag.insight.graph import COMPOSE_SYSTEM
from news_rag.prompts import FINANCIAL_SYSTEM_BASE, shared_system_prefix


def test_compose_prompts_use_you_voice():
    assert "**you**" in COMPOSE_SYSTEM
    assert "an investor" not in COMPOSE_SYSTEM.lower()


def test_rupee_grouping_lives_in_the_shared_prefix():
    assert "Indian grouping" in FINANCIAL_SYSTEM_BASE
    assert "1,00,000" in shared_system_prefix()
    assert "1 lakh" in shared_system_prefix()


def test_composer_and_prefix_carry_the_product_rules():
    prefix = shared_system_prefix()
    assert "please visit our app" in prefix and "please visit our app" in COMPOSE_SYSTEM
    assert "Never discuss how this assistant works" in prefix
    assert "2-3 plain prose lines" in COMPOSE_SYSTEM
    assert "The short answer" in COMPOSE_SYSTEM
    assert "**Bold**" in prefix
    assert len(COMPOSE_SYSTEM) + len(prefix) < 8000
