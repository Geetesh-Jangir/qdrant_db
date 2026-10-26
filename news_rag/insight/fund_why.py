"""Detect a why-did-this-fund-move question, and price a fund's holdings."""

from __future__ import annotations

import re
from typing import Any

from news_rag.insight.brief import QuestionBrief

_WHY_RE = re.compile(
    r"\bwhy\b|\bhappen\w*\b|\bdown\b|\bup\b|\bfell\b|\brose\b|\bperform\w*|\bdoing\b|\bmoved\b",
    re.I,
)


def named_fund_why(question: str, brief: QuestionBrief) -> bool:
    return bool(brief.funds) and not brief.primary_sector() and bool(_WHY_RE.search(question or ""))


def _price_holdings(holdings: list[Any], window: int) -> list[dict[str, Any]]:
    from historical_data.stocks_service import get_stock_profile

    rows: list[dict[str, Any]] = []
    ranked = [h for h in holdings if isinstance(h, dict) and h.get("name")]
    ranked.sort(key=lambda h: -float(h.get("percentage") or 0))
    for h in ranked[:30]:
        name = str(h.get("name"))
        profile = get_stock_profile(name) or {}
        if window <= 10:
            raw = profile.get("return_1w")
        else:
            raw = profile.get("return_1m")
        try:
            ret = round(float(raw), 2) if raw is not None else None
        except (TypeError, ValueError):
            ret = None
        rows.append(
            {
                "name": name,
                "industry": str(h.get("industry") or ""),
                "sector": str(h.get("industry") or ""),
                "weight_pct": float(h.get("percentage") or 0),
                "return_pct": ret,
            }
        )
    return rows


