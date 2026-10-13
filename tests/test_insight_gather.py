"""Spec-driven gather with fake tools (no network)."""

import pytest

from news_rag.insight import gather as gather_mod
from news_rag.insight import registry
from news_rag.insight.brief import QuestionBrief
from news_rag.insight.gather import GatherContext, gather_evidence
from news_rag.insight.registry import ToolSpec

CALLS: list[tuple[str, str]] = []


def _news(ctx):
    CALLS.append(("news", ""))
    return {"ok": True, "data": {"articles": [{"title": "t1", "url": "u1"}]}}


def _sectors(ctx):
    CALLS.append(("sectors", str(len(ctx.get("_articles") or []))))
    return {"ok": True, "data": {"sector_picks": [{"name": "Banks", "direction": "negative", "reason": "r"}]}}


def _funds(ctx):
    CALLS.append(("funds", str(len(ctx.get("_sector_picks") or []))))
    return {
        "ok": True,
        "data": {
            "rankings": [
                {"isin": "INF1", "fund_name": "Fund One", "sector_weight_pct": 20},
                {"isin": "INF2", "fund_name": "Fund Two", "sector_weight_pct": 12},
                {"isin": "INF3", "fund_name": "Fund Three", "sector_weight_pct": 9},
            ]
        },
    }


def _comp(ctx):
    CALLS.append(("comp", ctx["isin"]))
    return {"ok": True, "data": {"isin": ctx["isin"], "sectors": []}}


def _bad(ctx):
    CALLS.append(("bad", ""))
    return {"ok": False, "error": "boom"}


@pytest.fixture()
def fake_registry(monkeypatch):
    CALLS.clear()
    reg = {
        "news": ToolSpec("news", frozenset({"news_drivers"}), run=_news, description="d", when_to_use="w"),
        "sectors": ToolSpec(
            "sectors",
            frozenset({"sector_impact_direction"}),
            requires=frozenset({"news_drivers"}),
            run=_sectors,
            description="d",
            when_to_use="w",
        ),
        "funds": ToolSpec(
            "funds",
            frozenset({"exposure_link"}),
            requires=frozenset({"sector_impact_direction"}),
            run=_funds,
            description="d",
            when_to_use="w",
        ),
        "comp": ToolSpec(
            "comp", frozenset({"fund_composition"}), fan_out_over="fund", fan_out_cap=2, run=_comp,
            description="d", when_to_use="w",
        ),
    }
    monkeypatch.setattr(registry, "_REGISTRY", reg)
    monkeypatch.setattr(registry, "FACET_TOOL_PREFERENCE", {})
    monkeypatch.setattr(gather_mod, "_prewarm_tool_modules", lambda: None)
    return reg


def _ctx(needs):
    return GatherContext(question="q", brief=QuestionBrief(goal="g", evidence_needs=needs), fan_out_cap=8)


def test_dependencies_run_in_order_and_fan_out_is_capped(fake_registry):
    # the brief only asks for exposure_link + fund_composition; the closure pulls in the rest
    ev = gather_evidence(_ctx(["exposure_link", "fund_composition"]))
    status = {e.facet: e.status for e in ev.ledger}
    assert status["exposure_link"] == "satisfied"
    assert status["fund_composition"] == "satisfied"
    assert status["news_drivers"] == "satisfied"
    assert status["sector_impact_direction"] == "satisfied"

    names = [c[0] for c in CALLS]
    assert names.index("news") < names.index("sectors") < names.index("funds") < names.index("comp")
    assert ("sectors", "1") in CALLS  # sectors saw the articles
    assert ("funds", "1") in CALLS  # funds saw the sector picks
    assert sum(1 for c in CALLS if c[0] == "comp") == 2  # fan_out_cap=2
    implied = {e.facet for e in ev.ledger if e.implied}
    assert implied == {"news_drivers", "sector_impact_direction"}
    assert len(ev.articles) == 1


def test_fan_out_without_shortlist_is_unavailable(fake_registry):
    ev = gather_evidence(_ctx(["fund_composition"]))
    entry = next(e for e in ev.ledger if e.facet == "fund_composition")
    assert entry.status == "unavailable"
    assert entry.reason == "no_fund_shortlist"
    assert not any(c[0] == "comp" for c in CALLS)


def test_failed_tool_retries_with_next_provider(fake_registry, monkeypatch):
    fake_registry["bad"] = ToolSpec(
        "bad", frozenset({"news_drivers"}), run=_bad, description="d", when_to_use="w"
    )
    monkeypatch.setattr(registry, "FACET_TOOL_PREFERENCE", {"news_drivers": ["bad", "news"]})
    ev = gather_evidence(_ctx(["news_drivers"]))
    entry = next(e for e in ev.ledger if e.facet == "news_drivers")
    assert entry.status == "satisfied"
    assert entry.tool == "news"
    assert [c[0] for c in CALLS][:2] == ["bad", "news"]


def test_all_providers_failing_marks_unavailable(fake_registry, monkeypatch):
    fake_registry.pop("news")
    fake_registry["bad"] = ToolSpec(
        "bad", frozenset({"news_drivers"}), run=_bad, description="d", when_to_use="w"
    )
    ev = gather_evidence(_ctx(["news_drivers"]))
    entry = next(e for e in ev.ledger if e.facet == "news_drivers")
    assert entry.status == "unavailable"


def test_same_tool_for_two_facets_runs_once(fake_registry):
    fake_registry["news"] = ToolSpec(
        "news", frozenset({"news_drivers", "entity_state_over_time"}), run=_news, description="d", when_to_use="w"
    )
    ev = gather_evidence(_ctx(["news_drivers", "entity_state_over_time"]))
    assert sum(1 for c in CALLS if c[0] == "news") == 1
    assert {e.status for e in ev.ledger} == {"satisfied"}
