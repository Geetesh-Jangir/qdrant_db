"""Market Today and Institutional Flows prompt contract."""

from ai_insight.common.narrative import build_user_prompt
from ai_insight.common.evidence import EvidenceArticle
from ai_insight.fii_dii_flow_narrative.prompt import SYSTEM as FII_SYSTEM, build_user as fii_user
from ai_insight.fii_dii_flow_narrative.schema import PROMPT_VERSION as FII_VER
from ai_insight.market_driver_digest.prompt import SYSTEM as MARKET_SYSTEM, build_user as market_user
from ai_insight.market_driver_digest.schema import PROMPT_VERSION as MARKET_VER


def test_market_and_flow_prompt_versions():
    assert MARKET_VER == "v9"
    assert FII_VER == "v9.4"


def test_market_investor_section_prompts():
    assert "market_snapshot" in MARKET_SYSTEM
    assert "impacted_how" in MARKET_SYSTEM
    assert "mutual fund" in MARKET_SYSTEM.lower()
    assert "paragraph" in FII_SYSTEM
    assert "one paragraph" in FII_SYSTEM.lower() or "one selective paragraph" in FII_SYSTEM.lower()
    assert "net buyers" in FII_SYSTEM.lower()
    assert "100–150" in FII_SYSTEM or "100-150" in FII_SYSTEM
    assert "observations" in FII_SYSTEM.lower()


def test_build_user_importable():
    art = EvidenceArticle("c0", "t", "s", "p", "https://x", "text", 1.0, "E", "neutral", 2)
    facts = {"trading_date": "2026-03-18", "nifty_change_pct": 0.5, "article_count": 1}
    assert "FACTS" in market_user(facts, [art])
    assert "ARTICLES" in fii_user(facts, [art])
    assert "Step 1" in fii_user({**facts, "datasets": {"fii_dii_daily": []}}, [art])
    assert "INSIGHT:" in build_user_prompt("market_driver_digest", facts, [art])