from news_rag.insight.facets import EVIDENCE_FACETS
from news_rag.insight.registry import (
    all_tools,
    ensure_registry,
    pick_tool_for_facet,
    registry_prompt_block,
    tools_providing,
)


def test_registry_has_core_tools():
    ensure_registry()
    assert tools_providing("exposure_link")
    assert tools_providing("fund_composition")
    assert tools_providing("return_series")


def test_pick_tool_gated_by_context():
    ensure_registry()
    sector_ctx = {"sector_name": "Automobiles", "drivers": []}
    driver_ctx = {"drivers": ["crude_oil"], "sector_name": ""}
    assert pick_tool_for_facet("news_drivers", sector_ctx).name == "layered_news"
    assert pick_tool_for_facet("news_drivers", driver_ctx).name == "macro_news_enhanced"
    assert pick_tool_for_facet("exposure_link", sector_ctx).name == "sector_funds"
    assert pick_tool_for_facet("exposure_link", driver_ctx).name == "driver_affected_funds"
    assert pick_tool_for_facet("benchmark", sector_ctx).name == "index_series"


def test_pick_tool_exclude_gives_next_provider():
    ensure_registry()
    ctx = {"sector_name": "Automobiles", "drivers": []}
    first = pick_tool_for_facet("news_drivers", ctx)
    second = pick_tool_for_facet("news_drivers", ctx, exclude={first.name})
    assert second is not None and second.name != first.name


def test_inapplicable_tool_is_not_picked():
    ensure_registry()
    assert pick_tool_for_facet("peer_compare", {"fund_names": ["one fund"]}) is None
    assert pick_tool_for_facet("peer_compare", {"fund_names": ["a", "b"]}).name == "compare_funds"
    assert pick_tool_for_facet("stock_price", {"stock_name": ""}) is None


def test_tools_have_guidance():
    ensure_registry()
    for spec in all_tools():
        assert (spec.description or "").strip(), spec.name
        assert (spec.when_to_use or "").strip(), spec.name
        assert spec.run is not None, spec.name


def test_every_facet_has_a_provider():
    ensure_registry()
    missing = [f for f in EVIDENCE_FACETS if not tools_providing(f)]
    # forward_view / market_overview are served by news tools; none should be orphaned.
    assert not missing, missing


def test_prompt_block_mentions_use_and_avoid():
    ensure_registry()
    block = registry_prompt_block()
    assert "use when:" in block
    assert "do NOT use when:" in block
    assert "driver_affected_funds" in block
