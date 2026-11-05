"""Macro / geopolitics / FX questions with no fund subject in this turn."""

from __future__ import annotations

import re

from news_rag.insight.brief import question_is_standalone_macro
from news_rag.insight.contracts import ExecutionPlan, ToolCall


def _macro_news_topics(question: str) -> list[str]:
    q = (question or "").lower()
    topics: list[str] = []
    if re.search(r"\brupee|inr\b", q):
        topics.append("rupee")
    if re.search(r"\belection|midterm|mid-term|congress|senate\b", q):
        topics.append("US elections")
    if re.search(r"\bdollar|usd|forex|fx\b", q):
        topics.append("dollar")
    if re.search(r"\byield|treasury|\bfed\b", q):
        topics.append("US Fed yields")
    return topics or ["rupee"]


def apply_standalone_macro_scope(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Drop memory-bound funds; ensure macro news and FX series tools exist."""
    if not question_is_standalone_macro(question):
        return plan

    plan.funds = []
    ref = str(plan.subject_ref or "none").strip().lower()
    if ref in ("memory_primary", "memory_stack", "list_cursor"):
        plan.subject_ref = "none"

    plan.tool_calls = [
        c
        for c in (plan.tool_calls or [])
        if c.tool not in ("get_fund_data", "get_portfolio_data", "compare_funds")
    ]

    window_days = min(max(int(plan.window_days or 14), 7), 30)
    if not any(c.tool == "search_financial_news" for c in (plan.tool_calls or [])):
        plan.tool_calls.append(
            ToolCall(
                tool="search_financial_news",
                arguments={
                    "scope": "macro",
                    "topics": _macro_news_topics(question),
                    "top_n": 8,
                    "window_days": window_days,
                    "direction": "any",
                },
                wave=1,
            )
        )

    has_macro_series = any(
        c.tool == "get_market_snapshot"
        and "macro_series" in list((c.arguments or {}).get("modules") or [])
        for c in (plan.tool_calls or [])
    )
    if not has_macro_series and re.search(r"\brupee|inr|dollar|usd|yield|forex|election", question, re.I):
        series = ["usdinr"]
        if re.search(r"\byield|treasury|\bfed\b|election", question, re.I):
            series.append("yield")
        plan.tool_calls.append(
            ToolCall(
                tool="get_market_snapshot",
                arguments={
                    "modules": ["macro_series"],
                    "index": "nifty50",
                    "window_days": min(window_days, 14),
                    "series": series,
                    "top_n": 6,
                },
                wave=1,
            )
        )

    note = (
        "Standalone macro/geopolitics or FX question — no mutual fund is the subject; "
        "answer from macro news and market series only, without a fund title or holdings link."
    )
    existing = str(plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    plan.requires_compose = True
    return plan
