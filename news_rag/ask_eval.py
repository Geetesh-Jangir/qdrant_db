"""Hard Ask eval cases and response validation (routing + answer sanity)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HardAskCase:
    id: str
    question: str
    expect_intent: str | None = None
    expect_not_intent: str | None = None
    expect_source: str | None = None
    must_contain: tuple[str, ...] = ()
    must_not_contain: tuple[str, ...] = ()
    min_ranking_funds: int = 0
    requires_fund_breakdown: bool = False
    routing_only: bool = False
    allow_llm_sources: tuple[str, ...] = ()


def validate_ask_response(case: HardAskCase, data: dict[str, Any]) -> list[str]:
    """Return list of failure messages; empty if OK."""
    fails: list[str] = []
    intent = str(data.get("intent") or "")
    src = str(data.get("insight_source") or "")
    blob = (
        (data.get("insight_summary") or "")
        + " "
        + (data.get("insight") or "")
        + " "
        + " ".join(data.get("insight_bullets") or [])
    ).lower()

    if case.expect_intent and intent != case.expect_intent:
        fails.append(f"intent={intent!r} expected {case.expect_intent!r}")
    if case.expect_not_intent and intent == case.expect_not_intent:
        fails.append(f"intent must not be {case.expect_not_intent!r}")
    if case.expect_source:
        allowed = {case.expect_source, *case.allow_llm_sources}
        if src not in allowed:
            fails.append(f"insight_source={src!r} expected one of {sorted(allowed)!r}")
    for token in case.must_contain:
        if token.lower() not in blob:
            fails.append(f"missing required text: {token!r}")
    for token in case.must_not_contain:
        if token.lower() in blob:
            fails.append(f"forbidden text present: {token!r}")
    if case.min_ranking_funds:
        funds = (data.get("impact_rankings") or {}).get("funds") or []
        if len(funds) < case.min_ranking_funds:
            fails.append(f"impact_rankings.funds={len(funds)} need >={case.min_ranking_funds}")
    if case.requires_fund_breakdown:
        bd = data.get("impact_breakdown") or {}
        if not bd.get("fund_name"):
            fails.append("missing impact_breakdown.fund_name")
    return fails


HARD_ASK_CASES: list[HardAskCase] = [
    HardAskCase(
        id="fund_sectors_hdfc_lm",
        question="What are the top 5 sectors in HDFC Large and Mid Cap Fund?",
        expect_intent="fund_sectors",
        expect_source="fund_data",
        must_contain=("HDFC", "%"),
        must_not_contain=("UTI Banking",),
    ),
    HardAskCase(
        id="fund_nav_ppfas",
        question="What is the latest NAV of Parag Parikh Flexi Cap Fund?",
        expect_intent="fund_nav",
        expect_source="fund_data",
        must_contain=("NAV", "PPFAS"),
    ),
    HardAskCase(
        id="fund_holdings_hdfc_top100",
        question="What are the top holdings in HDFC Top 100 Fund?",
        expect_intent="fund_holdings",
        expect_source="fund_data",
        must_contain=("HDFC", "holdings"),
        must_not_contain=("RBI repo", "top 10 regular growth funds"),
    ),
    HardAskCase(
        id="impact_discovery_rbi_top10",
        question="Which are the top 10 funds worst hit by RBI repo rate hike news?",
        expect_intent="impact_funds",
        expect_not_intent="fund_event_impact",
        expect_source="impact_sector_ranking",
        must_contain=("Banks",),
        min_ranking_funds=5,
    ),
    HardAskCase(
        id="impact_discovery_auto_top5",
        question="Which are the top 5 funds most affected by recent automotive sector news?",
        expect_intent="impact_funds",
        expect_source="impact_sector_ranking",
        must_contain=("Automobiles",),
        min_ranking_funds=3,
    ),
    HardAskCase(
        id="impact_discovery_banking_positive",
        question="Which top 5 funds benefit most from positive banking sector news?",
        expect_intent="impact_funds",
        expect_source="impact_sector_ranking",
        must_contain=("Banks", "banking", "benefit"),
        must_not_contain=("rbi repo", "rate-hike", "drawdowns when rate-hike"),
        min_ranking_funds=3,
    ),
    HardAskCase(
        id="impact_single_crude_surge_ppfas",
        question="How will a surge in crude oil prices affect Parag Parikh Flexi Cap Fund?",
        expect_intent="fund_event_impact",
        expect_source="impact_single_fund",
        must_contain=("PPFAS", "crude"),
        must_not_contain=("UTI Banking and Financial Services",),
        requires_fund_breakdown=True,
    ),
    HardAskCase(
        id="impact_single_crude_fall_ppfas",
        question="How will a fall in crude oil prices affect Parag Parikh Flexi Cap Fund?",
        expect_intent="fund_event_impact",
        expect_source="impact_single_fund",
        must_contain=("PPFAS",),
        must_not_contain=("top 5 regular growth funds",),
        requires_fund_breakdown=True,
    ),
    HardAskCase(
        id="impact_single_rbi_hdfc_top100",
        question="What is the impact of RBI repo rate changes on HDFC Top 100 Fund?",
        expect_intent="fund_event_impact",
        expect_not_intent="impact_funds",
        expect_source="impact_single_fund",
        must_contain=("RBI", "Banks"),
        must_not_contain=("UTI Banking and Financial Services", "worst hit by rbi"),
        requires_fund_breakdown=True,
    ),
    HardAskCase(
        id="impact_single_rbi_cut_hdfc_large",
        question="What is the impact of an RBI repo rate cut on HDFC Large Cap Fund?",
        expect_intent="fund_event_impact",
        expect_source="impact_single_fund",
        must_contain=("RBI",),
        requires_fund_breakdown=True,
    ),
    HardAskCase(
        id="routing_top100_not_discovery",
        question="What is the impact of RBI repo rate changes on HDFC Top 100 Fund?",
        expect_intent="fund_event_impact",
        expect_not_intent="impact_funds",
        routing_only=True,
    ),
    HardAskCase(
        id="routing_discovery_plural_funds",
        question="Which are the top 10 funds worst hit by RBI repo rate hike news?",
        expect_intent="impact_funds",
        routing_only=True,
    ),
    HardAskCase(
        id="nav_isin_only",
        question="Show me the current NAV for INF879O01019",
        expect_intent="fund_nav",
        expect_source="fund_data",
        must_contain=("NAV",),
    ),
]
