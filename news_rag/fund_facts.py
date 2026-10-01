"""Deterministic answers for fund NAV / holdings / sectors — no LLM, no Qdrant."""

from __future__ import annotations

import re
from typing import Any

from news_rag.fund_search import extract_top_holdings, extract_top_sectors
from news_rag.insight_format import format_insight_display
from news_rag.parse import ParsedQuery


def _requested_list_count(question: str, default: int = 5) -> int:
    m = re.search(r"\btop\s*(\d{1,2})\b", question, re.I)
    if m:
        return max(1, min(int(m.group(1)), 25))
    m2 = re.search(r"\b(\d{1,2})\s+(?:sectors?|holdings?|stocks?)\b", question, re.I)
    if m2:
        return max(1, min(int(m2.group(1)), 25))
    return default


def _fund_label(detail: dict[str, Any]) -> str:
    return str(detail.get("fund_short_name") or detail.get("fund_name") or detail.get("isin") or "Fund")


def answer_fund_sectors(parsed: ParsedQuery, detail: dict[str, Any]) -> dict[str, Any]:
    limit = _requested_list_count(parsed.question, default=5)
    rows = extract_top_sectors(detail, limit=limit)
    name = _fund_label(detail)
    if not rows:
        msg = f"Sector allocation data is not available for **{name}** right now."
        return _payload(parsed, msg, [], "", "fund_data")

    bullets = [
        f"**{row['sector']}**: {row['percentage']:.2f}%"
        for row in rows
        if row.get("sector")
    ]
    as_on = detail.get("as_on") or detail.get("nav_date") or ""
    summary = ""
    if as_on:
        summary = f"As of {as_on}, these are the largest sector weights in **{name}** (Regular Growth)."
    display = format_insight_display(bullets, summary)
    return _payload(parsed, display, bullets, summary, "fund_data")


def answer_fund_holdings(parsed: ParsedQuery, detail: dict[str, Any]) -> dict[str, Any]:
    limit = _requested_list_count(parsed.question, default=10)
    rows = extract_top_holdings(detail, limit=limit)
    name = _fund_label(detail)
    if not rows:
        msg = f"Holdings data is not available for **{name}** right now."
        return _payload(parsed, msg, [], "", "fund_data")

    bullets = [
        f"**{_clean_name(row['name'])}**: {row['percentage']:.2f}% ({row.get('industry') or 'Equity'})"
        for row in rows
        if row.get("name")
    ]
    display = format_insight_display(bullets, "")
    return _payload(parsed, display, bullets, "", "fund_data")


def answer_fund_nav(parsed: ParsedQuery, detail: dict[str, Any]) -> dict[str, Any]:
    name = _fund_label(detail)
    nav = detail.get("nav")
    nav_date = detail.get("nav_date") or detail.get("as_on") or ""
    if nav is None:
        msg = f"Latest NAV is not available for **{name}** in the fund data feed."
        return _payload(parsed, msg, [], "", "fund_data")

    bullets = [f"**Latest NAV**: ₹{nav} (as of {nav_date})" if nav_date else f"**Latest NAV**: ₹{nav}"]
    ch = detail.get("nav_day_change_pct")
    if ch is not None:
        bullets.append(f"**Day change**: {float(ch):+.2f}%")
    rets = detail.get("returns") or {}
    for label, key in (("1 week", "1W"), ("1 month", "1M"), ("1 year", "1Y")):
        block = rets.get(key) if isinstance(rets, dict) else None
        if isinstance(block, dict) and block.get("change_pct") is not None:
            bullets.append(f"**{label} return**: {float(block['change_pct']):+.2f}%")

    summary = (
        f"**{name}** (Regular Growth) — Net Asset Value (NAV) is the per-unit price of the fund "
        f"after marking its investments to market."
    )
    display = format_insight_display(bullets, summary)
    return _payload(parsed, display, bullets, summary, "fund_data")


def _clean_name(name: str) -> str:
    return str(name or "").strip()


def _payload(
    parsed: ParsedQuery,
    display: str,
    bullets: list[str],
    summary: str,
    source: str,
) -> dict[str, Any]:
    return {
        "insight_bullets": bullets,
        "insight_summary": summary,
        "insight": display,
        "sources": [],
        "intent": parsed.intent,
        "insight_source": source,
        "contract": {
            "must_answer": [],
            "forbidden": [],
            "use_articles_count": 0,
            "include_nav": parsed.intent == "fund_nav",
            "include_holdings": parsed.intent == "fund_holdings",
            "include_sectors": parsed.intent == "fund_sectors",
            "include_stock_price": False,
            "include_metals": False,
            "aligned": True,
        },
    }


def try_fund_fact_answer(parsed: ParsedQuery) -> dict[str, Any] | None:
    """Return a complete API payload for pure fund fact queries, or None."""
    if parsed.intent not in ("fund_nav", "fund_holdings", "fund_sectors"):
        return None
    detail = parsed.fund_resolved
    if not detail:
        return None
    if parsed.intent == "fund_sectors":
        return answer_fund_sectors(parsed, detail)
    if parsed.intent == "fund_holdings":
        return answer_fund_holdings(parsed, detail)
    if parsed.intent == "fund_nav":
        return answer_fund_nav(parsed, detail)
    return None
