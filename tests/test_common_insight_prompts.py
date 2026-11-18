"""Market Today and Institutional Flows prompt contract."""

from ai_insight.fii_dii_flow_narrative.prompt import SYSTEM as FII_SYSTEM
from ai_insight.fii_dii_flow_narrative.schema import PROMPT_VERSION as FII_VER
from ai_insight.market_driver_digest.prompt import SYSTEM as MARKET_SYSTEM
from ai_insight.market_driver_digest.schema import PROMPT_VERSION as MARKET_VER


def test_market_and_flow_prompt_versions():
    assert MARKET_VER == "v3"
    assert FII_VER == "v3"


def test_market_and_flow_short_two_sentence_bodies():
    assert "2 sentences" in MARKET_SYSTEM
    assert "40 words" in MARKET_SYSTEM
    assert "—" in MARKET_SYSTEM
    assert "2 sentences" in FII_SYSTEM
    assert "40 words" in FII_SYSTEM
    assert "Institutional Flows" in MARKET_SYSTEM or "Market Today" in MARKET_SYSTEM
    assert "Market Today" in FII_SYSTEM or "institutional" in FII_SYSTEM.lower()