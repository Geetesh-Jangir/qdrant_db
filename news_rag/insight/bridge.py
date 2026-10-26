"""Deterministic Bridge — decides whether Wave 2 runs from Wave 1 metrics.

Zero second-planner LLM calls. Strictly deterministic logic:
1. DATA_ONLY queries never run Wave 2.
2. Checks wave_2_policy (negative_return, material_sector, always).
3. If triggered, returns at most 1 (max 2) targeted Wave 2 capability calls
   (e.g., search_financial_news for top detractors or heavy sectors).
"""

from __future__ import annotations

import logging
from typing import Any

from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall

logger = logging.getLogger(__name__)


def _extract_returns_from_results(results: list[dict[str, Any]]) -> list[float]:
    """Find fund return percentages from Wave 1 results."""
    returns: list[float] = []
    for r in results:
        data = r.get("data") if isinstance(r, dict) else {}
        if not isinstance(data, dict):
            continue

        # From get_fund_data snapshot
        snapshot = data.get("snapshot") or (data if data.get("nav") is not None else {})
        if isinstance(snapshot, dict):
            # Check returns dict
            rets = snapshot.get("returns") or {}
            if isinstance(rets, dict):
                for window in ("1D", "1W", "1M", "3M"):
                    val = rets.get(window)
                    if val is not None:
                        try:
                            returns.append(float(val))
                        except (TypeError, ValueError):
                            pass
            day_chg = snapshot.get("day_change_pct") or snapshot.get("day_change")
            if day_chg is not None:
                try:
                    returns.append(float(day_chg))
                except (TypeError, ValueError):
                    pass

        # From return_series or attribution
        series = data.get("return_series") or {}
        if isinstance(series, dict) and series.get("fund_return") is not None:
            try:
                returns.append(float(series["fund_return"]))
            except (TypeError, ValueError):
                pass

        attribution = data.get("attribution") or {}
        if isinstance(attribution, dict) and attribution.get("fund_return") is not None:
            try:
                returns.append(float(attribution["fund_return"]))
            except (TypeError, ValueError):
                pass

    return returns


def _extract_top_entities_from_results(results: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Extract top holdings, sectors, and detractors from Wave 1 results."""
    holdings: list[str] = []
    sectors: list[str] = []
    detractors: list[str] = []

    for r in results:
        data = r.get("data") if isinstance(r, dict) else {}
        if not isinstance(data, dict):
            continue

        # From get_portfolio_data
        for h in data.get("holdings") or []:
            if isinstance(h, dict) and h.get("company_name"):
                name = str(h["company_name"]).strip()
                if name and name not in holdings:
                    holdings.append(name)

        for s in data.get("sectors") or []:
            if isinstance(s, dict) and s.get("sector"):
                s_name = str(s["sector"]).strip()
                if s_name and s_name not in sectors:
                    sectors.append(s_name)

        # From attribution
        attr = data.get("attribution") or {}
        if isinstance(attr, dict):
            for d in attr.get("detractors") or []:
                if isinstance(d, dict) and d.get("stock"):
                    stock = str(d["stock"]).strip()
                    if stock and stock not in detractors:
                        detractors.append(stock)

    return {
        "holdings": holdings[:5],
        "sectors": sectors[:3],
        "detractors": detractors[:3],
    }


def evaluate_wave2(
    plan: ExecutionPlan,
    wave1_results: list[dict[str, Any]],
    *,
    deadline_remaining_ms: float = 10000.0,
) -> list[ToolCall]:
    """Evaluate whether to run Wave 2 and return the tool calls to execute.

    Deterministic rules:
    - DATA_ONLY: wave 2 is always skipped.
    - If deadline remaining is under 2000ms: skip wave 2.
    - If policy is 'none': skip wave 2.
    - If policy is 'always': execute planned wave 2 calls.
    - If policy is 'negative_return': check if any return is <= threshold (default 0.0).
    - If policy is 'material_sector': check if sectors/holdings were returned.
    """
    # Rule 1: DATA_ONLY never runs wave 2
    if plan.answer_mode == AnswerMode.DATA_ONLY:
        logger.debug("Bridge: skipping Wave 2 for DATA_ONLY query")
        return []

    # Rule 2: Insufficient time remaining
    if deadline_remaining_ms < 2000.0:
        logger.info(
            "Bridge: skipping Wave 2 due to tight deadline (remaining=%sms)",
            deadline_remaining_ms,
        )
        return []

    policy = plan.wave_2_policy
    trigger = (policy.trigger or "none").lower()
    max_calls = min(2, max(1, policy.max_calls))

    # Pre-planned wave 2 calls from plan
    planned_wave2 = plan.wave2_calls

    if trigger == "none":
        return []

    should_fire = False
    entities = _extract_top_entities_from_results(wave1_results)

    if trigger == "always":
        should_fire = True

    elif trigger == "negative_return":
        threshold = policy.threshold if policy.threshold is not None else 0.0
        returns = _extract_returns_from_results(wave1_results)
        # If any return is negative or below threshold, fire
        if any(r <= threshold for r in returns):
            should_fire = True
            logger.info("Bridge: negative_return trigger fired (returns=%s, threshold=%s)", returns, threshold)
        elif not returns and plan.answer_mode == AnswerMode.INSIGHT_FUSION:
            # If no returns were found but fusion was requested, fire defensively
            should_fire = True

    elif trigger == "material_sector":
        # Check if sectors or holdings exist
        if entities["sectors"] or entities["holdings"]:
            should_fire = True
            logger.info("Bridge: material_sector trigger fired (sectors=%s)", entities["sectors"])

    if not should_fire:
        logger.debug("Bridge: Wave 2 trigger '%s' did not fire", trigger)
        return []

    # If the plan already specified wave 2 calls, use them
    if planned_wave2:
        return planned_wave2[:max_calls]

    # Dynamically synthesize at most 1 news call based on Wave 1 findings
    topics: list[str] = []
    if entities["detractors"]:
        topics = entities["detractors"][:3]
        scope = "holdings"
    elif entities["sectors"]:
        topics = entities["sectors"][:2]
        scope = "sectors"
    elif entities["holdings"]:
        topics = entities["holdings"][:3]
        scope = "holdings"
    elif plan.sectors:
        topics = plan.sectors[:2]
        scope = "sectors"
    elif plan.funds:
        topics = plan.funds[:1]
        scope = "holdings"
    else:
        topics = ["market"]
        scope = "market"

    synthesized_call = ToolCall(
        tool="search_financial_news",
        arguments={
            "scope": scope,
            "topics": topics,
            "top_n": 3,
            "window_days": min(plan.window_days, 30),
            "direction": "negative" if trigger == "negative_return" else "any",
        },
        wave=2,
        required=False,
        why=f"Bridge triggered news for {scope} ({', '.join(topics)})",
    )
    return [synthesized_call][:max_calls]
