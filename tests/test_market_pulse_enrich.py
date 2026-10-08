from news_rag.ask_plan import AskPlan, PlannedTool
from news_rag.plan_enrich import enrich_ask_plan


def test_enrich_normalizes_common_market_news_window():
    plan = AskPlan(
        answer_parts="market now",
        tools=[PlannedTool(tool="common_market_news")],
    )
    out = enrich_ask_plan("What's happening in the market right now?", plan)
    assert len(out.tools) == 1
    assert out.tools[0].tool == "common_market_news"
    assert out.tools[0].window_days == 30
    assert (out.raw_json or {}).get("common_market_news") is True


def test_enrich_drops_macro_news_beside_common_market():
    plan = AskPlan(
        tools=[
            PlannedTool(tool="common_market_news"),
            PlannedTool(tool="macro_news", semantic_query="india"),
            PlannedTool(tool="macro_news_enhanced", semantic_query="crude"),
            PlannedTool(tool="sector_news", semantic_query="markets"),
        ],
    )
    out = enrich_ask_plan("market update", plan)
    names = {t.tool for t in out.tools}
    assert names == {"common_market_news"}


def test_enrich_keeps_named_sector_news_beside_common_market():
    plan = AskPlan(
        tools=[
            PlannedTool(tool="common_market_news"),
            PlannedTool(tool="sector_news", sector_name="Energy", semantic_query="crude"),
        ],
    )
    out = enrich_ask_plan("crude oil and the market", plan)
    names = {t.tool for t in out.tools}
    assert names == {"common_market_news", "sector_news"}
