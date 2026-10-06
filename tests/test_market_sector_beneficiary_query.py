from news_rag.ask_plan import AskPlan, PlannedTool
from news_rag.ask_composer import (
    _apply_positive_sector_postprocess,
    _finalize_compose,
    _is_entity_pair_cluster_bullet,
)
from news_rag.news_digest import LayerDigest
from news_rag.name_resolution import ResolvedNames
from news_rag.ask_execution import ExecutionBundle
from news_rag.plan_enrich import enrich_ask_plan


def test_entity_pair_cluster_bullet_detected():
    assert _is_entity_pair_cluster_bullet(
        "**PB Fintech Limited · Reliance Industries Limited** — RIL among 24 BSE 500 stocks at lows"
    )
    assert not _is_entity_pair_cluster_bullet(
        "**Information Technology** — Exporters benefit from a weaker rupee."
    )


def test_positive_postprocess_drops_noise_and_injects_sectors():
    bullets = [
        "**Market Backdrop** — Nifty under pressure as yields rise.",
        "**PB Fintech Limited · Reliance Industries Limited** — 52-week lows across names.",
        "**Brokerage firms** continue to issue strategic picks across NBFCs.",
    ]
    digests = [
        LayerDigest(
            layer="macro",
            focus="market_pulse",
            sectors_positive=[
                "Information Technology",
                "Public Sector Banks",
                "Pharmaceuticals",
                "Capital Goods",
            ],
            items=[
                {
                    "theme": "Information Technology",
                    "meaning": "A weaker rupee lifts rupee value of dollar export revenues for IT services firms.",
                },
            ],
        )
    ]
    out = _apply_positive_sector_postprocess(
        bullets, digests, sentiment="positive", pulse_mode=True
    )
    blob = " ".join(out).lower()
    assert "pb fintech" not in blob
    assert "brokerage firms" not in blob
    assert "information technology" in blob
    assert "capital goods" not in blob
    assert "pharmaceutical" not in blob


def test_finalize_compose_positive_sentiment_filters_clusters():
    bundle = ExecutionBundle(names=ResolvedNames())
    digests = [
        LayerDigest(
            layer="macro",
            focus="market_pulse",
            sectors_positive=["Information Technology", "Banking", "Healthcare", "Defence"],
            items=[],
        )
    ]
    clusters = [{"label": "Bond Yields", "article_count": 5, "articles": [{"title": "x"}]}]
    llm_bullets = [
        "**Macro** — Bond yields at 7.19% weigh on indices.",
        "**PB Fintech · Reliance Industries** — Stocks at 52-week lows.",
        "**Information Technology** — Rupee weakness supports export earnings.",
        "**Public Sector Banks** — FCNR(B) inflows lower funding costs.",
        "**Automobiles** — Sectors under pressure from crude costs.",
        "**Aviation** — Fuel costs squeeze margins.",
    ]
    _, _, bullets = _finalize_compose(
        "Headline",
        "",
        llm_bullets,
        bundle,
        digests,
        market_pulse_clusters=clusters,
        sentiment="positive",
    )
    assert not any("PB Fintech" in b for b in bullets)
    assert _count_beneficiary(bullets) >= 1
    pressure = [b for b in bullets if "under pressure" in b.lower() or "squeeze" in b.lower()]
    assert len(pressure) <= 1


def _count_beneficiary(bullets: list[str]) -> int:
    hints = ("technology", "banking", "healthcare", "defence", "beneficiary", "pharma")
    return sum(1 for b in bullets if any(h in b.lower() for h in hints))


def test_enrich_does_not_auto_add_sector_news_without_planner():
    plan = AskPlan(tools=[PlannedTool(tool="common_market_news")])
    out = enrich_ask_plan("market now and positive sectors", plan)
    assert {t.tool for t in out.tools} == {"common_market_news"}


def test_enrich_keeps_planner_sector_news():
    plan = AskPlan(
        tools=[
            PlannedTool(tool="common_market_news"),
            PlannedTool(tool="sector_news", semantic_query="India IT banking sector gainers"),
        ],
    )
    out = enrich_ask_plan("market and sectors", plan)
    names = {t.tool for t in out.tools}
    assert names == {"common_market_news", "sector_news"}
