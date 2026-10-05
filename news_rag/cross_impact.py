"""Macro/commodity driver × named fund — indirect impact questions."""

from __future__ import annotations

import re

from news_rag.ask_plan import AskPlan

_CROSS_IMPACT = re.compile(
    r"\b(affecting|affected|impact|impacts|influence|influencing|exposed|exposure|"
    r"sensitive|sensitivity|hurt|hurting|benefit|benefiting|because\s+of|due\s+to)\b",
    re.I,
)
_GOLD = re.compile(r"\bgold\b|\bbullion\b|\byellow\s+metal\b", re.I)
_SILVER = re.compile(r"\bsilver\b|\bwhite\s+metal\b", re.I)
_OIL = re.compile(r"\b(crude|crude\s+oil|brent|oil\s+price|petroleum|opec)\b", re.I)
_RATES = re.compile(
    r"\b(rbi|repo\s+rate|interest\s+rate|rate\s+cut|rate\s+hike|monetary\s+policy|mpc)\b",
    re.I,
)
_RUPEE = re.compile(r"\brupee\b|\binr\b|\bforex\b|\bdollar\b|\bcurrency\b", re.I)
_INFLATION = re.compile(r"\binflation\b|\bcpi\b|\bwpi\b", re.I)

DRIVER_LABELS = {
    "gold": "gold prices",
    "silver": "silver prices",
    "oil": "crude oil",
    "rates": "RBI / interest rates",
    "rupee": "rupee / USD",
    "inflation": "inflation",
}


def is_cross_impact_question(question: str) -> bool:
    return bool(_CROSS_IMPACT.search(question or ""))


def detect_macro_drivers(question: str) -> list[str]:
    q = question or ""
    drivers: list[str] = []
    if _GOLD.search(q):
        drivers.append("gold")
    if _SILVER.search(q):
        drivers.append("silver")
    if _OIL.search(q):
        drivers.append("oil")
    if _RATES.search(q):
        drivers.append("rates")
    if _RUPEE.search(q):
        drivers.append("rupee")
    if _INFLATION.search(q):
        drivers.append("inflation")
    seen: set[str] = set()
    out: list[str] = []
    for d in drivers:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def cross_impact_from_plan(plan: AskPlan) -> dict | None:
    raw = plan.raw_json.get("cross_impact") if isinstance(plan.raw_json, dict) else None
    return raw if isinstance(raw, dict) and raw.get("drivers") else None


def driver_semantic_query(driver: str) -> str:
    queries = {
        "gold": "gold prices India move drivers safe haven dollar rupee RBI jewellery demand",
        "silver": "silver prices India industrial demand COMEX dollar rupee",
        "oil": "crude oil India prices OPEC import bill inflation rupee",
        "rates": "RBI repo rate India banks liquidity credit transmission",
        "rupee": "rupee dollar India forex RBI intervention FII flows",
        "inflation": "India CPI inflation RBI policy consumption demand",
    }
    return queries.get(driver, f"{driver} India markets macro news")


CROSS_IMPACT_COMPOSER_ADDENDUM = """
CROSS-IMPACT MODE (macro driver × named fund):
The user asks whether a macro/commodity move affects a fund that may NOT hold that asset directly.

Required reasoning in bullets (plain sentences, no section labels):
1) Brief fund snapshot: NAV/returns if available; note direct holdings of the driver (e.g. gold ETFs) or absence.
2) Cite driver context: use context.metals_spot for gold/silver when present; summarize driver news from digests whose focus matches the driver (gold, silver, oil, macro).
3) Indirect impact: map driver news to THIS fund's top sectors and holdings — channels include safe-haven flows, rupee, rates, inflation, import costs, consumer demand, jewellery, banking liquidity, etc.
4) Conclude with a balanced view (limited vs meaningful indirect exposure) grounded in the fund's sector weights.

Do NOT answer "no impact" only because the fund lacks gold. Do NOT claim "no gold news" when driver digests or metals_spot exist.
Do NOT list unrelated holding news unless it ties to the driver story.
"""
