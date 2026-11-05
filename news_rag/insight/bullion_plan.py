"""Bullion (spot) gold/silver price asks — not gold ETF / scheme unless the user named one."""

from __future__ import annotations

from news_rag.insight.brief import (
    primary_metal_in_question,
    question_is_bullion_metal_price_question,
)
from news_rag.insight.contracts import ExecutionPlan, ToolCall


def apply_bullion_metal_scope(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Drop memory-bound gold ETFs when the user meant bullion price, not a fund."""
    if not question_is_bullion_metal_price_question(question):
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

    metal = primary_metal_in_question(question)
    has_metals = any(
        c.tool == "get_market_snapshot"
        and "metals_spot" in list((c.arguments or {}).get("modules") or [])
        for c in (plan.tool_calls or [])
    )
    if metal == "gold" and not has_metals:
        plan.tool_calls.insert(
            0,
            ToolCall(
                tool="get_market_snapshot",
                arguments={
                    "modules": ["metals_spot"],
                    "metal": "gold",
                    "windows": ["1D", "1W", "1M"],
                    "history_months": 3,
                },
                wave=1,
            ),
        )

    if not any(c.tool == "search_financial_news" for c in (plan.tool_calls or [])):
        topics = ["Gold"] if metal != "silver" else ["Silver"]
        plan.tool_calls.append(
            ToolCall(
                tool="search_financial_news",
                arguments={"scope": "macro", "topics": topics, "top_n": 8, "window_days": 30},
                wave=1,
            )
        )

    note = (
        "User asked about bullion/spot metal price (India gold from metals_spot if present), "
        "not a gold ETF or mutual fund NAV unless they named a scheme or ETF."
    )
    existing = str(plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    return plan
