"""Deterministic plan enrichment — multi-entity news (gold/silver), metals tools."""

from __future__ import annotations

import re

from news_rag.ask_plan import AskPlan, EntityMention, PlannedTool
from news_rag.cross_impact import (
    detect_macro_drivers,
    driver_semantic_query,
    is_cross_impact_question,
)
from news_rag.holdings_market import holdings_top_n_from_question, question_wants_holdings_performance
from news_rag.market_pulse import MARKET_PULSE_DEFAULT_WINDOW_DAYS, market_pulse_window_days
from news_rag.parse import infer_window_days_from_question

_GOLD = re.compile(r"\bgold\b", re.I)
_SILVER = re.compile(r"\bsilver\b", re.I)
_BULLION = re.compile(r"\bbullion\b|\bprecious\s+metal", re.I)
_NEWS_TOOLS = frozenset({"holdings_news", "sector_news", "macro_news"})
_FUND_FACT_TOOLS = frozenset(
    {"fund_nav", "fund_top_stocks", "fund_top_sectors", "fund_holdings", "fund_sectors"}
)
_PURE_NAV = re.compile(
    r"^\s*(?:what(?:'s| is)\s+(?:the\s+)?nav|(?:latest|current)\s+nav|nav\s+(?:of|for))\b",
    re.I,
)
_SECTOR_PERF_FUNDS = re.compile(
    r"\b(best|top|highest|outperform|performed\s+best|performing\s+best)\b",
    re.I,
)
_SECTOR_FUND_PHRASE = re.compile(r"\b(mutual\s+funds?|sector\s+funds?|banking\s+funds?)\b", re.I)


def _has_gold(text: str) -> bool:
    return bool(_GOLD.search(text))


def _has_silver(text: str) -> bool:
    return bool(_SILVER.search(text))


def _fund_entity_index(plan: AskPlan) -> int | None:
    return next(
        (i for i, e in enumerate(plan.entities) if e.role == "fund_scheme"),
        None,
    )


def _fund_label(plan: AskPlan, idx: int) -> str:
    if idx is not None and 0 <= idx < len(plan.entities):
        ent = plan.entities[idx]
        return (ent.cleaned_phrase or ent.raw or "").strip()
    return (plan.answer_parts or "mutual fund").strip()


def _sector_name_hint_from_question(question: str) -> str:
    lower = (question or "").lower()
    if "banking" in lower or "financial services" in lower or "financials" in lower:
        return "banking and financial services"
    if "information technology" in lower or re.search(r"\bit\s+funds?\b", lower):
        return "information technology"
    if "pharma" in lower or "healthcare" in lower:
        return "pharmaceuticals and healthcare"
    if "defence" in lower or "defense" in lower:
        return "defence"
    if "auto" in lower or "automotive" in lower:
        return "automotive"
    return ""


def _ensure_sector_performance_funds(plan: AskPlan, question: str) -> AskPlan:
    """When the user asks for best sector mutual funds, ensure sector_funds runs with a sector hint."""
    names = {t.tool for t in plan.tools}
    hint = _sector_name_hint_from_question(question)
    if "sector_funds" in names:
        if hint:
            for t in plan.tools:
                if t.tool == "sector_funds" and not (t.sector_name or "").strip():
                    t.sector_name = hint
                    if not (t.semantic_query or "").strip():
                        t.semantic_query = hint
        return plan
    q = question or ""
    if not hint or not _SECTOR_PERF_FUNDS.search(q) or not _SECTOR_FUND_PHRASE.search(q):
        return plan
    tools = list(plan.tools)
    tools.append(
        PlannedTool(
            tool="sector_funds",
            sector_name=hint,
            semantic_query=hint,
            top_n=max(plan.affected_funds_top_n or 0, 5),
        )
    )
    plan.tools = tools
    return plan


def _apply_requested_fund_count(plan: AskPlan, question: str) -> AskPlan:
    """Use the user's fund count when they state one; otherwise at least 3."""
    from news_rag.tools import explicit_fund_count

    n = explicit_fund_count(question)
    plan.raw_json = dict(plan.raw_json or {})
    plan.raw_json["fund_count_explicit"] = n is not None
    chosen = n if n is not None else 5
    if plan.affected_funds != "none":
        plan.affected_funds_top_n = chosen if n is not None else max(3, chosen)
    for tool in plan.tools:
        if tool.tool == "sector_funds" and n is not None:
            tool.top_n = n
    return plan


def _is_pure_nav_question(question: str) -> bool:
    q = (question or "").strip()
    if not q:
        return False
    if _PURE_NAV.search(q):
        return True
    lower = q.lower()
    if "nav" in lower and not any(
        w in lower
        for w in (
            "tell",
            "about",
            "overview",
            "profile",
            "holding",
            "sector",
            "composition",
            "portfolio",
            "news",
            "why",
            "perform",
            "working",
            "insight",
        )
    ):
        return len(lower.split()) <= 12
    return False


def _ensure_fund_nav_tool(plan: AskPlan) -> AskPlan:
    names = {t.tool for t in plan.tools}
    if "fund_nav" in names:
        return plan
    fund_idx = _fund_entity_index(plan)
    if fund_idx is None:
        return plan
    tools = list(plan.tools)
    tools.insert(0, PlannedTool(tool="fund_nav", fund_entity_index=fund_idx))
    plan.tools = tools
    return plan


def _ensure_fund_news_tools(plan: AskPlan, question: str) -> AskPlan:
    """Planner often omits vector news for overview fund questions — add holdings/sector/macro search."""
    fund_idx = _fund_entity_index(plan)
    if fund_idx is None:
        return plan
    if _is_pure_nav_question(question):
        return plan

    tool_names = {t.tool for t in plan.tools}
    if tool_names & _NEWS_TOOLS:
        return plan

    has_fund_facts = bool(tool_names & _FUND_FACT_TOOLS)
    if not has_fund_facts:
        return plan

    label = _fund_label(plan, fund_idx)
    window = 30
    lower = (question or "").lower()
    if any(w in lower for w in ("week", "lately", "recent", "today", "this month")):
        window = 14

    tools = list(plan.tools)
    tools.append(
        PlannedTool(
            tool="holdings_news",
            fund_entity_index=fund_idx,
            semantic_query=f"{label} top stock holdings earnings results news India",
            window_days=window,
        )
    )
    tools.append(
        PlannedTool(
            tool="sector_news",
            fund_entity_index=fund_idx,
            semantic_query=f"{label} sector allocation banks pharma consumer news India",
            window_days=window,
        )
    )
    tools.append(
        PlannedTool(
            tool="macro_news",
            semantic_query=f"India equity markets large cap banks RBI policy news {label}",
            window_days=window,
        )
    )
    plan.tools = tools
    return plan


def _ensure_cross_impact_tools(plan: AskPlan, question: str, drivers: list[str]) -> AskPlan:
    """Fund + macro driver impact: spot prices, driver news, and portfolio facts for sector mapping."""
    fund_idx = _fund_entity_index(plan)
    if fund_idx is None or not drivers:
        return plan

    plan.raw_json = dict(plan.raw_json or {})
    plan.raw_json["cross_impact"] = {
        "drivers": drivers,
        "fund_entity_index": fund_idx,
        "question": (question or "").strip(),
    }

    tools = list(plan.tools)
    names = {t.tool for t in tools}
    macro_focuses = {
        (t.search_focus or "").strip().lower()
        for t in tools
        if t.tool == "macro_news" and t.search_focus
    }
    lower = (question or "").lower()
    window = 21
    if any(w in lower for w in ("lately", "recent", "sudden", "movement", "moving", "today")):
        window = 14

    if ("gold" in drivers or "silver" in drivers) and "metals_spot" not in names:
        tools.append(PlannedTool(tool="metals_spot"))

    for driver in drivers:
        focus = driver if driver in ("gold", "silver") else driver
        if focus in macro_focuses:
            continue
        tools.append(
            PlannedTool(
                tool="macro_news",
                search_focus=focus,
                semantic_query=driver_semantic_query(driver),
                window_days=window,
            )
        )
        macro_focuses.add(focus)

    plan.tools = tools
    return plan


def _tune_holdings_top_n(plan: AskPlan, question: str) -> AskPlan:
    """When user asks how top holdings are doing, ensure we fetch enough names (default top 3)."""
    if not question_wants_holdings_performance(question):
        return plan
    n = holdings_top_n_from_question(question, default=3)
    tools: list[PlannedTool] = []
    for t in plan.tools:
        if t.tool in ("fund_top_stocks", "fund_holdings"):
            t.top_n = max(t.top_n, n)
        tools.append(t)
    plan.tools = tools
    return plan


def _ensure_fund_portfolio_tools(plan: AskPlan) -> AskPlan:
    fund_idx = _fund_entity_index(plan)
    if fund_idx is None:
        return plan
    names = {t.tool for t in plan.tools}
    tools = list(plan.tools)
    if "fund_top_stocks" not in names and "fund_holdings" not in names:
        tools.append(PlannedTool(tool="fund_top_stocks", fund_entity_index=fund_idx, top_n=8))
    if "fund_top_sectors" not in names and "fund_sectors" not in names:
        tools.append(PlannedTool(tool="fund_top_sectors", fund_entity_index=fund_idx, top_n=8))
    plan.tools = tools
    return plan


def _enrich_commodity_only_plan(question: str, plan: AskPlan) -> AskPlan:
    """Gold/silver/bullion questions without a named fund — metals funds ranking."""
    q = question or ""
    lower = q.lower()
    gold = _has_gold(q)
    silver = _has_silver(q)
    bullion = bool(_BULLION.search(q))
    if not (gold or silver or bullion):
        return plan

    tools: list[PlannedTool] = list(plan.tools)
    names = {t.tool for t in tools}
    macro_focuses = {
        (t.search_focus or "").strip().lower()
        for t in tools
        if t.tool == "macro_news" and t.search_focus
    }

    if "metals_spot" not in names:
        tools.append(PlannedTool(tool="metals_spot"))

    window = 21
    if "lately" in lower or "recent" in lower or "sudden" in lower:
        window = 14

    def _add_macro(focus: str, semantic: str) -> None:
        if focus in macro_focuses:
            return
        tools.append(
            PlannedTool(
                tool="macro_news",
                search_focus=focus,
                semantic_query=semantic,
                window_days=window,
            )
        )
        macro_focuses.add(focus)

    if gold and silver:
        _add_macro(
            "gold",
            "gold prices India decline fall reasons dollar rupee RBI safe haven",
        )
        _add_macro(
            "silver",
            "silver prices India decline fall reasons industrial demand COMEX",
        )
    elif gold:
        _add_macro("gold", "gold prices India recent move decline reasons news")
    elif silver:
        _add_macro("silver", "silver prices India recent move decline reasons news")
    elif bullion:
        _add_macro("gold", "gold bullion India prices news drivers")
        _add_macro("silver", "silver bullion India prices news drivers")

    if not plan.entities:
        ents: list[EntityMention] = []
        if gold:
            ents.append(EntityMention(raw="gold", role="sector", cleaned_phrase="Gold"))
        if silver:
            ents.append(EntityMention(raw="silver", role="sector", cleaned_phrase="Silver"))
        plan.entities = ents

    if "sector_funds" not in names and plan.affected_funds in ("none", "now"):
        tools.append(
            PlannedTool(
                tool="sector_funds",
                semantic_query="gold silver precious metals ETF mutual funds India",
                top_n=plan.affected_funds_top_n or 10,
            )
        )
        if plan.affected_funds == "none":
            plan.affected_funds = "now"
        if not plan.affected_funds_sectors:
            plan.affected_funds_sectors = ["Non - Ferrous Metals"]

    plan.tools = tools
    return plan


def _normalize_planner_market_tools(plan: AskPlan, question: str) -> AskPlan:
    """Planner-chosen market tools only — default windows, drop redundant macro_news."""
    q = question or ""
    has_common = any(t.tool == "common_market_news" for t in plan.tools)
    if not has_common:
        return plan
    window = market_pulse_window_days(
        q,
        infer_window_days_from_question(q, default_days=MARKET_PULSE_DEFAULT_WINDOW_DAYS),
    )
    kept: list[PlannedTool] = []
    has_sector_news = False
    for t in plan.tools:
        if t.tool == "macro_news" and has_common:
            continue
        if t.tool == "common_market_news":
            if not t.window_days:
                t.window_days = window
            if not t.semantic_query:
                t.semantic_query = "India equity markets Nifty RBI flows macro drivers"
        if t.tool == "sector_news":
            has_sector_news = True
            if not t.window_days:
                t.window_days = window
            if not t.semantic_query:
                t.semantic_query = (
                    "India sector gainers beneficiaries macro impact IT banking pharma exports PSU banks"
                )
        kept.append(t)

    wants_funds = any(
        w in (question or "").lower()
        for w in ("mutual fund", "mutual funds", "which fund", "which funds", "what fund", "what funds", "schemes")
    )
    if wants_funds and plan.affected_funds == "none":
        plan.affected_funds = "after_news"
        if not plan.affected_funds_top_n:
            plan.affected_funds_top_n = 6

    plan.tools = kept
    plan.raw_json = dict(plan.raw_json or {})
    plan.raw_json["common_market_news"] = True
    return plan


def _normalize_macro_enhanced_tools(plan: AskPlan, question: str) -> AskPlan:
    q = question or ""
    for t in plan.tools:
        if t.tool != "macro_news_enhanced":
            continue
        if not t.window_days:
            t.window_days = market_pulse_window_days(q, MARKET_PULSE_DEFAULT_WINDOW_DAYS)
        if not t.semantic_query:
            t.semantic_query = (plan.answer_parts or q)[:200]
    return plan


def enrich_ask_plan(question: str, plan: AskPlan) -> AskPlan:
    """Fill a missing market window. Tool choice stays with the research agent."""
    q = question or ""
    for tool in plan.tools:
        if tool.tool == "common_market_news":
            if not tool.window_days:
                tool.window_days = market_pulse_window_days(q, MARKET_PULSE_DEFAULT_WINDOW_DAYS)
            plan.raw_json = dict(plan.raw_json or {})
            plan.raw_json["common_market_news"] = True
        elif tool.tool == "macro_news_enhanced" and not tool.window_days:
            tool.window_days = market_pulse_window_days(q, MARKET_PULSE_DEFAULT_WINDOW_DAYS)
    return plan
