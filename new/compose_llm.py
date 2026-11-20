"""Structured fund-week narrative from per-stock news paragraphs."""

from __future__ import annotations

import re
from typing import Any

from new.stock_explain import _short_name

_FORBIDDEN_OUTPUT = re.compile(
    r"\b(no news|news not|not present|no coverage|unavailable|no article|home\s*/\s*markets)\b",
    re.I,
)
_BREADCRUMB = re.compile(r"home\s*/\s*markets|listen to this article", re.I)


def _usable_block(block: dict[str, Any]) -> bool:
    if block.get("why_skip"):
        return False
    why = str(block.get("why") or "").strip()
    if not why or _BREADCRUMB.search(why) or _FORBIDDEN_OUTPUT.search(why):
        return False
    return bool(block.get("usable_news") or block.get("articles"))


def _paragraph_entry(block: dict[str, Any]) -> dict[str, Any] | None:
    if not _usable_block(block):
        return None
    name = _short_name(str(block.get("instrument_name") or ""))
    ch = block.get("change_1w_pct")
    try:
        ch_f = round(float(ch), 2) if ch is not None else None
    except (TypeError, ValueError):
        ch_f = None
    why = str(block.get("why") or "").strip()
    return {"name": name, "change_1w_pct": ch_f, "why": why}


def compose_fund_narrative(facts: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
    scheme = str(facts.get("scheme_name") or "Fund")
    nav = facts.get("nav_1w_pct")
    book = facts.get("portfolio_pct")
    try:
        nav_f = float(nav) if nav is not None else 0.0
    except (TypeError, ValueError):
        nav_f = 0.0
    verb = "gained" if nav_f >= 0 else "lost"

    opening = f"{scheme} {verb} {abs(nav_f):.2f}% over the last week"
    if book is not None:
        opening += f" (about {book}% of your portfolio)"
    opening += "."

    stock_news = facts.get("stock_news") or []
    g_blocks = [b for b in stock_news if b.get("move") == "up"]
    l_blocks = [b for b in stock_news if b.get("move") == "down"]
    gainers = [e for b in g_blocks if (e := _paragraph_entry(b))]
    losers = [e for b in l_blocks if (e := _paragraph_entry(b))]

    if nav_f >= 0:
        closing = (
            f"Overall, {scheme} still ended the week up {nav_f:+.2f}% — "
            "the strongest contributors outweighed the laggards."
            if gainers or losers
            else f"Overall, {scheme} ended the week up {nav_f:+.2f}%."
        )
    else:
        closing = (
            f"Overall, {scheme} closed the week at {nav_f:+.2f}% after those pushes and pulls."
            if gainers or losers
            else f"Overall, {scheme} closed the week at {nav_f:+.2f}%."
        )

    cushioned = [c.get("scheme_name") for c in facts.get("cushioned_by") or [] if c.get("scheme_name")]
    sources: list[str] = []
    for block in stock_news:
        if not _usable_block(block):
            continue
        for art in block.get("articles") or []:
            u = art.get("url")
            if u:
                sources.append(str(u))

    body_parts: list[str] = []
    if gainers:
        body_parts.append("What helped the fund:")
        for g in gainers:
            ch = g.get("change_1w_pct")
            ch_s = f" ({ch:+.2f}%)" if ch is not None else ""
            body_parts.append(f"{g['name']}{ch_s}. {g['why']}")
        body_parts.append("")
    if losers:
        body_parts.append("What held the fund back:")
        for l in losers:
            ch = l.get("change_1w_pct")
            ch_s = f" ({ch:+.2f}%)" if ch is not None else ""
            body_parts.append(f"{l['name']}{ch_s}. {l['why']}")
        body_parts.append("")

    insight_parts = [opening, ""]
    insight_parts.extend(body_parts)
    if closing:
        insight_parts.append(closing)
    insight = "\n\n".join(p for p in insight_parts if p is not None)

    return {
        "headline": f"{scheme} — week in short",
        "opening": opening,
        "gainers": gainers,
        "losers": losers,
        "closing": closing,
        "insight": insight,
        "summary": insight,
        "cushioned_funds": cushioned,
        "sources": sources[:24],
        "narrative_source": "stitched" if not dry_run else "dry_run",
    }