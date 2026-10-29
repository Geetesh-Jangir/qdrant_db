"""Plan-driven node graph: planner JSON, tool selection, data pack and routing."""

from types import SimpleNamespace

from news_rag.insight import graph as graph_mod
from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ScopeKind, ToolCall
from news_rag.insight.data_pack import build_data_pack
from news_rag.insight.gather import EvidenceItem, EvidenceSet
from news_rag.insight.plan import Plan, parse_plan, plan_to_brief


def test_parse_plan_drops_unknown_tools_and_clamps_values():
    plan = parse_plan(
        {
            "scope": {"kind": "in_scope"},
            "understanding": {"goal": "NAV", "intent": "lookup", "answer_mode": "DATA_ONLY"},
            "entities": {"funds": ["HDFC Large Cap Fund"], "random_funds": {"count": 99}},
            "time": {"window_days": 99999},
            "tool_calls": [{"tool": "get_fund_data"}, {"tool": "not_a_tool"}, {"tool": "get_fund_data"}],
            "presentation": {"style": "short_answer", "max_words": 5},
        }
    )
    assert plan.tool_names == ["get_fund_data", "get_fund_data"]
    assert plan.window_days == 1825
    assert plan.random_fund_count == 10
    assert plan.max_words == 30
    assert plan.requires_compose is True


def test_a_nav_lookup_plans_no_news_facets():
    plan = Plan(funds=["HDFC Large Cap Fund"], tool_calls=[ToolCall(tool="get_fund_data", why="nav")])
    brief = plan_to_brief(plan, sector_keys=[], funds=["HDFC Large Cap Fund"])
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
        "slot_route",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        graph_mod,
        "make_plan",
        lambda *a, **k: Plan(scope_kind=ScopeKind.OUT_OF_SCOPE, direct_reply="I only cover Indian markets."),
    )
    state = graph_mod.run_graph(_state("recipe for pasta"))
    assert [t["node"] for t in state.trace] == ["route", "reply"]
    result = graph_mod.build_result(state)
    assert result["refused"] is True
    assert result["insight"] == "I only cover Indian markets."


def test_lookup_route_skips_news_and_sends_no_identifiers_to_the_writer(monkeypatch):
    plan = Plan(
        funds=["Fund A"],
        answer_mode=AnswerMode.DATA_ONLY,
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"windows": ["1M"]}, wave=1, why="nav")],
        style="short_answer",
        max_words=60,
    )
    monkeypatch.setattr(graph_mod, "make_plan", lambda *a, **k: None)
    monkeypatch.setattr(graph_mod, "slot_route", lambda *a, **k: plan)
    monkeypatch.setattr(graph_mod, "_resolve_funds", lambda *a, **k: (["Fund A"], []))

    def fake_execute_wave(calls, *args, **kwargs):
        return [{"tool": "get_fund_data", "fund": "Fund A", "ok": True, "elapsed_ms": 1, "data": {"fund_name": "Fund A", "nav": 10.5, "isin": "INF000"}}]

    monkeypatch.setattr("news_rag.insight.graph.execute_wave", fake_execute_wave)
    monkeypatch.setattr(graph_mod, "llm_api_key_configured", lambda s: True)

    state = graph_mod.run_graph(_state("nav of fund a"))
    assert [t["node"] for t in state.trace] == ["route", "resolve", "wave1", "evidence_gate", "compose"]
    assert len(state.wave2_results) == 0
    assert "INF000" not in state.answer
    assert "NEWS:" not in state.answer


def test_unmatched_fund_replies_without_calling_tools(monkeypatch):
    plan = Plan(funds=["Nonexistent Fund"], tool_calls=[ToolCall(tool="get_fund_data", why="")])
    monkeypatch.setattr(graph_mod, "make_plan", lambda *a, **k: None)
    monkeypatch.setattr(graph_mod, "slot_route", lambda *a, **k: plan)
    monkeypatch.setattr(graph_mod, "_resolve_funds", lambda *a, **k: ([], ["Nonexistent Fund"]))
    state = graph_mod.run_graph(_state())
    assert [t["node"] for t in state.trace] == ["route", "resolve", "reply"]
    assert "couldn't find" in state.answer
