from news_rag.insight.registry import ensure_registry, pick_tool_for_facet, tools_providing


def test_registry_has_core_tools():
    ensure_registry()
    assert tools_providing("exposure_link")
    assert tools_providing("fund_composition")
    assert tools_providing("return_series")


def test_pick_tool_prefers_layered_news_for_drivers():
    ensure_registry()
    assert pick_tool_for_facet("news_drivers").name == "layered_news"
    assert pick_tool_for_facet("benchmark").name == "index_series"


def test_tools_have_descriptions():
    ensure_registry()
    from news_rag.insight.registry import all_tools

    for spec in all_tools():
        assert (spec.description or "").strip(), spec.name
