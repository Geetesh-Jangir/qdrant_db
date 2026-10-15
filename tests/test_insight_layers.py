"""Layered planner args, news target expansion and coverage."""

from news_rag.insight.graph import GraphState, compose_user_content
from news_rag.insight.layer_tools import clamp_news_scope, clamp_tool_args
from news_rag.insight.layers import coverage_report, expand_targets, widen_thin
from news_rag.insight.market_news import MARKET_PULSE_THEME_COUNT, market_query_for_topic
from news_rag.insight.news_fanout import NewsTarget
from news_rag.insight.plan import Plan, parse_plan


def test_portfolio_defaults_are_top_three():
    args = clamp_tool_args("fund_portfolio", {})
    assert args["top_n_holdings"] == 3
    assert args["top_n_sectors"] == 3
    news = clamp_news_scope({"scope": "holdings", "source": "layer1"}, default_window=30)
    assert news["top_n"] == 3


def test_portfolio_args_are_clamped():
    args = clamp_tool_args("fund_portfolio", {"top_n_holdings": 80, "top_n_sectors": 0, "find": "Reliance", "nope": 1})
    assert args["top_n_holdings"] == 50
    assert args["top_n_sectors"] == 1
    assert args["find"] == "Reliance"
    assert "nope" not in args


def test_parse_plan_reads_layers_and_drops_unknown_tools():
    plan = parse_plan(
        {
            "scope": {"kind": "in_scope"},
            "understanding": {"goal": "how is the fund", "intent": "overview"},
            "layer1": [
                {"tool": "fund_snapshot", "args": {"windows": ["1M"]}},
                {"tool": "not_a_tool"},
            ],
            "layer2_news": [
                {"scope": "holdings", "source": "layer1", "top_n": 8, "window_days": 30},
                {"scope": "sideways"},
            ],
            "asks_not_supported": ["expense ratio"],
            "presentation": {"style": "sections"},
        }
    )
    assert plan.tool_names == ["fund_snapshot"]
    assert plan.dropped_tools == ["not_a_tool"]
    assert [s["scope"] for s in plan.layer2_news] == ["holdings"]
    assert plan.asks_not_supported == ["expense ratio"]
    assert clamp_news_scope({"scope": "macro", "source": ["crude oil"]}, default_window=30)["topics"] == ["crude oil"]


def test_market_scope_expands_to_eight_parallel_themes():
    scope = clamp_news_scope({"scope": "market", "source": "layer1", "window_days": 7}, default_window=7)
    plan = Plan(layer2_news=[scope], window_days=7)
    targets = expand_targets(plan, [])
    assert len(targets) == MARKET_PULSE_THEME_COUNT
    assert all(t.scope == "market" for t in targets)
    assert targets[0].query  # semantic query from pulse specs


def test_market_scope_focused_topic():
    scope = clamp_news_scope(
        {"scope": "market", "source": ["crude oil", "RBI"], "window_days": 14},
        default_window=14,
    )
    plan = Plan(layer2_news=[scope])
    targets = expand_targets(plan, [])
    assert len(targets) == 2
    assert {t.entity for t in targets} == {"crude oil", "RBI"}
    assert "crude" in market_query_for_topic("crude oil").lower()
    assert "RBI" in market_query_for_topic("RBI")


def test_expand_uses_portfolio_holdings_and_attribution_movers():
    plan = Plan(
        layer2_news=[
            {"scope": "holdings", "source": "layer1", "topics": [], "top_n": 4, "window_days": 30, "direction": "any", "articles_per_entity": 2, "chars_per_article": 400, "required": True},
            {"scope": "macro", "source": "layer1", "topics": [], "top_n": 3, "window_days": 14, "direction": "any", "articles_per_entity": 1, "chars_per_article": 300, "required": False},
        ]
    )
    results = [
        {"ok": True, "data": {"holdings": [{"name": "HDFC Bank"}, {"name": "ICICI Bank"}], "sectors": [{"sector": "Banks"}]}},
        {"ok": True, "data": {"detractors": [{"name": "Reliance"}], "contributors": [{"name": "TCS"}]}},
    ]
    targets = expand_targets(plan, results)
    holding_names = [t.entity for t in targets if t.scope == "holdings"]
    assert holding_names[0] == "Reliance"
    assert any(t.scope == "macro" for t in targets)


def test_widen_once_replaces_only_empty_required_targets():
    empty = NewsTarget(scope="holdings", entity="NTPC", query="q", window_days=30, required=True)
    full = NewsTarget(scope="holdings", entity="TCS", query="q", window_days=30, required=True, articles=[{"headline": "x", "text": "y"}])

    def fake_search(targets):
        for target in targets:
            target.articles = [{"headline": "later", "text": "found"}]

    import news_rag.insight.layers as layers

    original = layers.search_targets
    layers.search_targets = fake_search
    try:
        widened = widen_thin([empty, full])
    finally:
        layers.search_targets = original
    assert widened == ["NTPC"]
    assert empty.articles[0]["headline"] == "later"
    assert full.articles[0]["headline"] == "x"


def test_coverage_lists_missing_tools_and_thin_news():
    plan = Plan(layer1=[{"tool": "fund_snapshot", "required": True}], asks_not_supported=["exit load"])
    report = coverage_report(plan, [{"tool": "fund_snapshot", "ok": False}], [NewsTarget(scope="sectors", entity="Banks", query="q")], [])
    assert report["missing_tools"] == ["fund_snapshot"]
    assert report["news_without_articles"] == ["sectors: Banks"]
    assert report["not_supported"] == ["exit load"]


def test_composer_input_groups_news_and_coverage():
    state = GraphState(question="how is the fund doing")
    state.plan = Plan(goal="fund health", style="sections", max_words=200, window_label="1 month")
    state.data_pack = {"funds": {"Fund A": {"fund_snapshot": {"nav": 10}}}}
    state.news_grouped = {"holdings": {"HDFC Bank": [{"headline": "h", "text": "body", "url": "http://x"}]}}
    state.coverage = {"missing_tools": [], "news_without_articles": ["sectors: Power"], "not_supported": ["expense ratio"]}
    text = compose_user_content(state)
    assert "NEWS:" in text and "HDFC Bank" in text and "http://x" not in text
    assert "COVERAGE:" in text and "expense ratio" in text
