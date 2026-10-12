"""Turn retrieved news articles into data-backed insight lines (not title dumps)."""

from __future__ import annotations

import re
from typing import Any

_BOILERPLATE = re.compile(
    r"listen to this article|summarized format|read more|subscribe|click here",
    re.I,
)
_QUOTE_CHUNK = re.compile(r'"([^"]{40,220})"')


def _clean_body(raw: str) -> str:
    text = re.sub(r"\s+", " ", (raw or "").strip())
    text = _BOILERPLATE.sub("", text).strip()
    return text


def _best_excerpt(art: dict[str, Any], limit: int = 200) -> str:
    title = str(art.get("title") or "").strip()
    body = _clean_body(
        str(art.get("scraped_text") or art.get("snippet") or art.get("body") or "")
    )
    if body:
        m = _QUOTE_CHUNK.search(body)
        if m:
            body = m.group(1).strip()
    if not body or len(body) < 40:
        return title
    if title and title.lower() not in body.lower()[:60]:
        return f"{title}: {body[:limit]}"
    if len(body) > limit:
        return body[: limit - 3].rstrip() + "..."
    return body


def _extract_numbers(text: str) -> list[str]:
    found: list[str] = []
    for m in re.finditer(r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*%", text):
        found.append(m.group(1).replace(",", ""))
    for m in re.finditer(r"\b(\d{2,3},\d{3})\s+units\b", text, re.I):
        found.append(m.group(1).replace(",", ""))
    return found[:4]


def _dedupe_key(art: dict[str, Any], excerpt: str) -> str:
    url = str(art.get("url") or "").strip()
    if url:
        return url
    title = str(art.get("title") or "").strip().lower()
    return title or excerpt[:80].lower()


def digest_articles(articles: list[dict[str, Any]], *, limit: int = 4) -> tuple[list[str], dict[str, Any]]:
    """Return (insight bullets, stats) from Qdrant article payloads."""
    stats: dict[str, Any] = {
        "positive": 0,
        "negative": 0,
        "neutral": 0,
        "avg_impact": None,
        "count": 0,
    }
    scored: list[tuple[float, dict[str, Any]]] = []
    impacts: list[float] = []
    for art in articles:
        if not isinstance(art, dict):
            continue
        stats["count"] += 1
        d = str(art.get("direction") or "").lower()
        if d == "positive":
            stats["positive"] += 1
        elif d == "negative":
            stats["negative"] += 1
        else:
            stats["neutral"] += 1
        try:
            imp = float(art.get("max_impact") or art.get("impact") or 0)
        except (TypeError, ValueError):
            imp = 0.0
        if imp > 0:
            impacts.append(imp)
        scored.append((imp, art))
    if impacts:
        stats["avg_impact"] = round(sum(impacts) / len(impacts), 2)

    scored.sort(key=lambda x: (-x[0], str(x[1].get("title") or "")))
    seen: set[str] = set()
    insights: list[str] = []
    for imp, art in scored:
        if len(insights) >= limit:
            break
        excerpt = _best_excerpt(art)
        key = _dedupe_key(art, excerpt)
        if key in seen:
            continue
        seen.add(key)
        direction = str(art.get("direction") or "neutral").lower()
        event = str(art.get("event_type") or "news").replace("_", " ")
        nums = _extract_numbers(excerpt)
        num_bit = f" Key figures: **{', '.join(nums)}**." if nums else ""
        imp_s = f"score **{imp:.0f}**/5" if imp > 0 else "score n/a"
        insights.append(
            f"**{direction.title()}** ({imp_s}, {event}) — {excerpt}{num_bit}"
        )
    return insights, stats


def executive_sector_summary(stats: dict[str, Any], insights: list[str]) -> str:
    """One short paragraph tying stats + themes together."""
    pos = int(stats.get("positive") or 0)
    neg = int(stats.get("negative") or 0)
    avg = stats.get("avg_impact")
    if not insights and not stats.get("count"):
        return ""
    tone = "mixed"
    if pos > neg * 1.25:
        tone = "slightly positive"
    elif neg > pos * 1.25:
        tone = "slightly negative"
    avg_bit = f" Average tagged impact **{avg}**/5." if avg is not None else ""
    demand = any("sales" in x.lower() or "volume" in x.lower() or "festive" in x.lower() for x in insights)
    risk = any("cost" in x.lower() or "pressure" in x.lower() or "uncertainty" in x.lower() for x in insights)
    drivers: list[str] = []
    if demand:
        drivers.append("**demand/volume** stories (festive inventory, retail sales)")
    if risk:
        drivers.append("**cost/margin** pressure in some OEM updates")
    driver_txt = " and ".join(drivers) if drivers else "mixed operational themes"
    return (
        f"Sector news reads **{tone}** ({pos} positive vs {neg} negative articles).{avg_bit} "
        f"Drivers in the data: {driver_txt}."
    )
