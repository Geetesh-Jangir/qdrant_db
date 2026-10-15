"""Plan-driven node graph: planner JSON, tool selection, data pack and routing."""

from types import SimpleNamespace

from news_rag.insight import graph as graph_mod
from news_rag.insight.data_pack import build_data_pack
from news_rag.insight.gather import EvidenceItem, EvidenceSet
from news_rag.insight.plan import Plan, parse_plan, plan_to_brief, tools_to_facets


def test_parse_plan_drops_unknown_tools_and_clamps_values():
    plan = parse_plan(
        {
            "scope": {"kind": "in_scope"},
            "understanding": {"goal": "NAV", "intent": "lookup"},
            "entities": {"funds": ["HDFC Large Cap Fund"], "random_funds": {"count": 99}},
            "time": {"window_days": 99999},
            "tool_calls": [{"tool": "fund_nav"}, {"tool": "not_a_tool"}, {"tool": "fund_nav"}],
            "news": {"depth": "bogus"},
            "presentation": {"style": "short_answer", "max_words": 5},
        }
    )
    assert plan.tool_names == ["fund_nav"]
    assert plan.dropped_tools == ["not_a_tool"]
    assert plan.news_depth == "none"
    assert plan.window_days == 1825
    assert plan.random_fund_count == 10
    assert plan.max_words == 30


def test_tools_to_facets_keeps_the_planners_own_prerequisites():
    facets, forced = tools_to_facets(["layered_news", "affected_sectors", "driver_affected_funds"])
    assert forced["sector_impact_direction"] == "affected_sectors"
    assert forced["exposure_link"] == "driver_affected_funds"
    # layered_news fills the facet affected_sectors needs, so no default news tool is substituted.
    assert forced["news_drivers"] == "layered_news"
    assert len(facets) == 3


def test_a_nav_lookup_plans_no_news_facets():
    plan = Plan(funds=["HDFC Large Cap Fund"], tool_calls=[{"tool": "fund_nav", "why": ""}])
    brief = plan_to_brief(plan, sector_keys=[], funds=["HDFC Large Cap Fund"])
    assert brief.evidence_needs == ["fund_facts_nav"]
    assert brief.funds == ["HDFC Large Cap Fund"]


def test_data_pack_groups_by_fund_and_hides_internal_fields():
    ev = EvidenceSet()
    ev.items.append(
        EvidenceItem(
            "fund_facts_nav",
            "fund_nav",
            "INF000",
            {"isin": "INF000", "fund_name": "Fund A", "nav": 12.3456, "url": "http://x", "elapsed_ms": 4},
        )
    )
    pack = build_data_pack(ev)
    text = str(pack)
    assert "Fund A" in pack["funds"]
    assert pack["funds"]["Fund A"]["nav_and_returns"]["nav"] == 12.35
    assert "INF000" not in text and "http" not in text and "elapsed" not in text


def _state(question="q"):
    return graph_mod.GraphState(question=question)


def test_out_of_scope_question_ends_after_the_planner(monkeypatch):
    monkeypatch.setattr(
        graph_mod,
        "make_plan",
        lambda *a, **k: Plan(scope_kind="out_of_scope", direct_reply="I only cover Indian markets."),
    )
    state = graph_mod.run_graph(_state("recipe for pasta"))
    assert [t["node"] for t in state.trace] == ["plan", "reply"]
    result = graph_mod.build_result(state)
    assert result["refused"] is True
    assert result["insight"] == "I only cover Indian markets."


def test_lookup_route_skips_news_and_sends_no_identifiers_to_the_writer(monkeypatch):
    plan = Plan(
        funds=["Fund A"],
        layer1=[{"tool": "fund_snapshot", "args": {}, "required": True, "why": "nav"}],
        news_depth="none",
        style="short_answer",
        max_words=60,
    )
    monkeypatch.setattr(graph_mod, "make_plan", lambda *a, **k: plan)
    monkeypatch.setattr(graph_mod, "_resolve_funds", lambda p, s: (["Fund A"], []))

    def fake_layer1(*_a, **_k):
        return [{"tool": "fund_snapshot", "fund": "Fund A", "ok": True, "elapsed_ms": 1, "data": {"fund_name": "Fund A", "nav": 10.5, "isin": "INF000"}}]

    monkeypatch.setattr("news_rag.insight.layers.run_layer1", fake_layer1)
    monkeypatch.setattr("news_rag.insight.layers._retry_failed", lambda _p, rows, *_a, **_k: rows)
    monkeypatch.setattr(graph_mod, "llm_api_key_configured", lambda s: True)
    seen = {}

    def fake_llm(**kwargs):
        seen["user"] = kwargs["user_content"]
        return SimpleNamespace(raw_text="Fund A's NAV is 10.5.")

    monkeypatch.setattr(graph_mod, "call_insight_llm", fake_llm)
    state = graph_mod.run_graph(_state("nav of fund a"))
    assert [t["node"] for t in state.trace] == ["plan", "resolve", "layer1", "check", "compose"]
    assert "INF000" not in seen["user"]
    assert "NEWS:" not in seen["user"]
    assert state.answer.endswith("not investment advice.*")


def test_unmatched_fund_replies_without_calling_tools(monkeypatch):
    plan = Plan(funds=["Nonexistent Fund"], tool_calls=[{"tool": "fund_nav", "why": ""}])
    monkeypatch.setattr(graph_mod, "make_plan", lambda *a, **k: plan)
    monkeypatch.setattr(graph_mod, "_resolve_funds", lambda p, s: ([], ["Nonexistent Fund"]))
    state = graph_mod.run_graph(_state())
    assert [t["node"] for t in state.trace] == ["plan", "resolve", "reply"]
    assert "couldn't find" in state.answer
