from news_rag.ask_plan import AskPlan, PlannedTool
from news_rag.plan_enrich import enrich_ask_plan


def test_enrich_swaps_macro_for_market_pulse():
    plan = AskPlan(
        answer_parts="market now",
        tools=[
            PlannedTool(tool="macro_news", semantic_query="india markets"),
            PlannedTool(tool="sector_news", semantic_query="sectors"),
        ],
    )
    out = enrich_ask_plan("What's happening in the market right now?", plan)
    names = {t.tool for t in out.tools}
    assert "market_pulse" in names
    assert "macro_news" not in names
    assert (out.raw_json or {}).get("market_pulse") is True
    pulse = next(t for t in out.tools if t.tool == "market_pulse")
    assert pulse.window_days == 30
