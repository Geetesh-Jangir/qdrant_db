"""Resolve user question intent from data indexes + phrasing (not example-query hardcoding).

Used to validate slot-router plans and to steer the planner LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from news_rag.insight.contracts import ExecutionPlan


@dataclass
class QuestionIntent:
    kind: str
    confidence: float
    primary_tool: str
    summary: str = ""
    tool_args_hint: dict[str, Any] = field(default_factory=dict)
    answer_mode: str = "DATA_ONLY"

    def expected_tools(self) -> set[str]:
        return {self.primary_tool}


def _top_n_from_question(question: str) -> int:
    import re

    m = re.search(r"\b(?:top|any|name|list|give me|show)\s+(\d+)\b", question or "", re.I)
    if m:
        return max(1, min(20, int(m.group(1))))
    m = re.search(r"\b(\d+)\s+funds?\b", question or "", re.I)
    if m:
        return max(1, min(20, int(m.group(1))))
    return 5


def resolve_question_intent(question: str) -> QuestionIntent:
    q = (question or "").strip()
    if not q:
        return QuestionIntent("unknown", 0.0, "", "Empty question")

    from news_rag.tools import (
        asks_fund_portfolio_holdings,
        asks_funds_holding_stock,
        asks_funds_with_sector_exposure,
        portfolio_sections_for_question,
        screen_hints_from_question,
    )

    hints = screen_hints_from_question(q)
    top_n = _top_n_from_question(q)

    if asks_fund_portfolio_holdings(q):
        sec = portfolio_sections_for_question(q)
        return QuestionIntent(
            kind="fund_portfolio",
            confidence=0.93,
            primary_tool="get_portfolio_data",
            summary=f"Holdings/sectors inside a named mutual fund scheme (top {top_n}).",
            tool_args_hint={"sections": sec, "top_n": top_n},
            answer_mode="DATA_ONLY",
        )

    if asks_funds_with_sector_exposure(q):
        from news_rag.sector_fund_ranking import primary_sector_for_question

        canon_sector, _sector_keys = primary_sector_for_question(q)
        sector = hints.get("sector_name") or canon_sector or hints.get("category") or "sector"
        return QuestionIntent(
            kind="screen_sector_exposure",
            confidence=0.92,
            primary_tool="screen_funds_by_exposure",
            summary=f"List funds with highest exposure to {sector} (not what one fund holds).",
            tool_args_hint={
                "sector": sector,
                "direction": "any",
                "top_n": top_n,
            },
            answer_mode="DATA_ONLY",
        )

    if asks_funds_holding_stock(q):
        stock = hints.get("stock_name") or "named stock"
        return QuestionIntent(
            kind="screen_stock_holders",
            confidence=0.91,
            primary_tool="screen_funds_by_exposure",
            summary=f"Funds whose portfolios hold {stock} (reverse lookup).",
            tool_args_hint={"direction": "any", "top_n": top_n},
            answer_mode="DATA_ONLY",
        )

    import re

    from news_rag.insight.slot_router import (
        _asks_fund_manager,
        _asks_catalog_fund_performance,
        _COMPARE_RE,
        _HOLDINGS_RE,
        _NAV_RE,
        _WHY_MOVE_RE,
        _extract_fund_names,
    )
    from news_rag.domain_intake import question_mentions_fund_scheme

    if _asks_fund_manager(q):
        return QuestionIntent(
            kind="fund_managers",
            confidence=0.94,
            primary_tool="get_fund_data",
            summary="Fund manager roster for a named scheme.",
            tool_args_hint={"modules": ["managers"]},
            answer_mode="DATA_ONLY",
        )

    if _asks_catalog_fund_performance(q):
        return QuestionIntent(
            kind="screen_catalog_performance",
            confidence=0.9,
            primary_tool="screen_funds_by_exposure",
            summary="Unnamed fund list filtered by return window / category.",
            tool_args_hint={"top_n": top_n},
            answer_mode="DATA_ONLY",
        )

    funds = _extract_fund_names(q) if question_mentions_fund_scheme(q) else []
    if funds and _COMPARE_RE.search(q) and len(funds) >= 2:
        return QuestionIntent(
            kind="compare_funds",
            confidence=0.88,
            primary_tool="compare_funds",
            summary="Compare named schemes.",
            answer_mode="DATA_ONLY",
        )

    if funds and _HOLDINGS_RE.search(q):
        sec = portfolio_sections_for_question(q)
        return QuestionIntent(
            kind="fund_portfolio",
            confidence=0.88,
            primary_tool="get_portfolio_data",
            tool_args_hint={"sections": sec, "top_n": top_n},
            answer_mode="DATA_ONLY",
        )

    if funds and _NAV_RE.search(q) and not re.search(
        r"\b(?:about|why|overview)\b", q, re.I
    ):
        return QuestionIntent(
            kind="fund_snapshot",
            confidence=0.9,
            primary_tool="get_fund_data",
            tool_args_hint={"modules": ["snapshot"]},
            answer_mode="DATA_ONLY",
        )

    if funds and _WHY_MOVE_RE.search(q):
        return QuestionIntent(
            kind="fund_why_move",
            confidence=0.85,
            primary_tool="get_fund_data",
            summary="Explain fund move with metrics + optional news.",
            tool_args_hint={"modules": ["snapshot", "attribution"]},
            answer_mode="INSIGHT_FUSION",
        )

    from news_rag.fund_rupeestop_metrics import asks_fund_category_average
    from news_rag.tools import asks_fund_related_news

    if funds and asks_fund_category_average(q):
        return QuestionIntent(
            kind="fund_category_average",
            confidence=0.94,
            primary_tool="get_fund_data",
            summary="Category average returns for the fund's peer group (1Y/3Y/5Y from RupeeStop).",
            tool_args_hint={"modules": ["snapshot"]},
            answer_mode="DATA_ONLY",
        )

    if funds and asks_fund_related_news(q):
        return QuestionIntent(
            kind="fund_news",
            confidence=0.92,
            primary_tool="get_fund_data",
            summary="Fund returns + portfolio context, then layered news (holdings/sectors/macro).",
            tool_args_hint={
                "modules": ["snapshot", "return_series", "attribution"],
                "sections": ["holdings", "sectors"],
                "top_n": 5,
            },
            answer_mode="INSIGHT_FUSION",
        )

    if funds:
        return QuestionIntent(
            kind="fund_overview",
            confidence=0.75,
            primary_tool="get_fund_data",
            summary="General fund overview — snapshot, portfolio, news if needed.",
            tool_args_hint={"modules": ["snapshot"]},
            answer_mode="INSIGHT_FUSION",
        )

    return QuestionIntent("unknown", 0.35, "", "Ambiguous — planner should choose tools.")


def plan_matches_intent(plan: ExecutionPlan, intent: QuestionIntent) -> bool:
    if intent.kind == "unknown" or intent.confidence < 0.85:
        return True
    if not plan.tool_calls:
        return False
    tools = plan.tool_names
    if intent.primary_tool not in tools:
        return False
    if intent.kind == "fund_portfolio" and "get_portfolio_data" in tools:
        if "screen_funds_by_exposure" in tools and "get_portfolio_data" not in tools:
            return False
        return True
    if intent.kind in ("screen_sector_exposure", "screen_stock_holders", "screen_catalog_performance"):
        if "get_portfolio_data" in tools and "screen_funds_by_exposure" not in tools:
            return False
        return "screen_funds_by_exposure" in tools
    if intent.kind == "fund_managers":
        for c in plan.tool_calls:
            if c.tool == "get_fund_data":
                mods = (c.arguments or {}).get("modules") or []
                return "managers" in mods
        return False
    if intent.kind == "fund_news":
        return (
            "get_fund_data" in tools
            and "get_portfolio_data" in tools
            and "search_financial_news" in tools
        )
    if intent.kind == "fund_portfolio":
        return "get_portfolio_data" in tools and "search_financial_news" not in tools
    return True


def prefers_planner_over_slot(question: str) -> bool:
    """Compound or pick-one-fund asks need tool chaining the slot router does not plan."""
    q = question or ""
    from news_rag.tools import asks_fund_related_news

    if asks_fund_related_news(q):
        return False
    if re.search(
        r"\b(?:about|overall|tell me about|how is|overview|summarize|summary)\b",
        q,
        re.I,
    ):
        return True
    if re.search(
        r"\b(?:pick|choose|select|suggest)\s+(?:a\s+)?fund\b",
        q,
        re.I,
    ):
        return True
    if q.count("?") > 1 or re.search(r"\band also\b|\band then\b", q, re.I):
        return True
    return False


def planner_supplement_for_question(question: str) -> str:
    """Optional catalog hints for the planner (typos / ambiguous names). Does not choose tools."""
    q = (question or "").strip()
    if not q:
        return ""
    lines: list[str] = []
    try:
        from news_rag.fund_search import resolve_fund_for_query

        detail, ambiguous, close = resolve_fund_for_query(q)
        if detail:
            name = str(detail.get("fund_name") or detail.get("fund_short_name") or "").strip()
            isin = str(detail.get("isin") or "").strip()
            if name:
                lines.append(
                    f"Optional catalog resolution (use only if it matches what the user meant): "
                    f"{name}" + (f" ({isin})" if isin else "")
                )
        if ambiguous and close:
            lines.append(f"Ambiguous scheme phrases in catalog: {', '.join(close[:4])}")
    except Exception:
        pass
    if not lines:
        return ""
    return (
        "REFERENCE for spelling and scheme names only. You still decide intent, data_need, and tool_calls:\n"
        + "\n".join(lines)
    )
