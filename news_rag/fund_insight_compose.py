"""Readable fund insight bullets and summary — simple language, no scrape paste."""

from __future__ import annotations

import re
from typing import Any

from news_rag.insights import _informative_takeaway, _theme_paraphrase
from news_rag.snippet_clean import is_broken_fragment, looks_like_raw_scrape, sanitize_analyst_bullet

_FRAGMENT_START = re.compile(
    r"^(?:giants?|yet at home|the country'?s|however|also|and the|but the|while the)\b",
    re.I,
)


def _is_weak_news_line(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 40:
        return True
    if _FRAGMENT_START.match(t):
        return True
    words = t.split()
    if words and words[0][0].islower() and words[0] not in {"fcnr", "bpcl", "hpcl", "ioc"}:
        return True
    if is_broken_fragment(t) or looks_like_raw_scrape(t):
        return True
    return False


def _one_line_from_article(article: dict, *, max_words: int = 32) -> str:
    title = (article.get("title") or "").strip()
    snippet = str(article.get("snippet") or "")
    themed = _theme_paraphrase(snippet, title)
    if themed:
        line = re.sub(r"^\*\*[^*]+:\*\*\s*", "", themed).strip()
        return sanitize_analyst_bullet(line)
    take = _informative_takeaway(snippet, title, limit=200)
    if take and not _is_weak_news_line(take):
        return sanitize_analyst_bullet(take)
    if title and len(title.split()) >= 5:
        return sanitize_analyst_bullet(title)
    return ""


def _layer_prefix(article: dict) -> str:
    layer = str(article.get("_news_layer") or "")
    label = str(article.get("_news_source_label") or "").strip()
    if layer == "holding" and label:
        return f"Holding — {label}"
    if layer == "sector" and label:
        return f"Sector — {label}"
    if layer == "macro" and label:
        return f"Macro — {label}"
    if layer == "holding":
        return "Holding news"
    if layer == "sector":
        return "Sector news"
    return "Macro"


def _nav_bullet(nav: dict[str, Any] | None) -> str:
    if not nav:
        return ""
    name = nav.get("fund_name") or "Fund"
    nav_val = nav.get("nav")
    nav_date = nav.get("nav_date") or ""
    rets = nav.get("returns") or {}
    parts: list[str] = []
    if nav_val is not None:
        bit = f"**{name}** is at **₹{nav_val}**"
        if nav_date:
            bit += f" (as of {nav_date})"
        parts.append(bit)
    trail: list[str] = []
    for label, key in (("1 month", "1m"), ("1 week", "1w"), ("1 year", "1y")):
        val = rets.get(key)
        if val is not None:
            try:
                trail.append(f"{label} {float(val):+.1f}%")
            except (TypeError, ValueError):
                pass
    if trail:
        parts.append("Recent returns: " + ", ".join(trail))
    if not parts:
        return ""
    return "**Performance:** " + ". ".join(parts) + "."


def _holdings_bullet(holdings: list[dict]) -> str:
    if not holdings:
        return ""
    names = ", ".join(
        f"**{r.get('name')}** ({float(r.get('percentage', 0)):.1f}%)"
        for r in holdings[:5]
        if r.get("name")
    )
    if not names:
        return ""
    return f"**Portfolio:** Largest positions are {names}."


def _sectors_bullet(sectors: list[dict]) -> str:
    if not sectors:
        return ""
    names = ", ".join(
        f"**{r.get('sector')}** ({float(r.get('percentage', 0)):.1f}%)"
        for r in sectors[:4]
        if r.get("sector")
    )
    if not names:
        return ""
    return f"**Sector mix:** {names}."


def compose_fund_insight_bullets(
    *,
    nav: dict[str, Any] | None,
    holdings: list[dict],
    sectors: list[dict],
    articles: list[dict],
    min_news: int = 5,
    max_news: int = 7,
) -> list[str]:
    bullets: list[str] = []
    perf = _nav_bullet(nav)
    if perf:
        bullets.append(perf)
    hold = _holdings_bullet(holdings)
    if hold:
        bullets.append(hold)
    sec = _sectors_bullet(sectors)
    if sec:
        bullets.append(sec)

    news_bullets: list[str] = []
    seen: set[str] = set()
    for art in articles:
        line = _one_line_from_article(art)
        if not line or line in seen:
            continue
        seen.add(line)
        prefix = _layer_prefix(art)
        news_bullets.append(f"**{prefix}:** {line}")
        if len(news_bullets) >= max_news:
            break

    # Prefer at least one holding-tagged story if available
    holding_first = [b for b in news_bullets if b.startswith("**Holding")]
    sector_next = [b for b in news_bullets if b.startswith("**Sector")]
    macro_last = [b for b in news_bullets if b.startswith("**Macro")]
    ordered = holding_first + sector_next + macro_last
    if len(ordered) < len(news_bullets):
        rest = [b for b in news_bullets if b not in ordered]
        ordered.extend(rest)

    bullets.extend(ordered[:max_news])
    if len([b for b in bullets if b.startswith("**Holding") or b.startswith("**Sector") or b.startswith("**Macro")]) < min_news:
        for art in articles:
            if len(bullets) >= 3 + min_news:
                break
            line = _one_line_from_article(art)
            if not line:
                continue
            tag = f"**{_layer_prefix(art)}:** {line}"
            if tag not in bullets:
                bullets.append(tag)

    return bullets[:10]


def compose_fund_insight_summary(
    *,
    nav: dict[str, Any] | None,
    holdings: list[dict],
    sectors: list[dict],
    articles: list[dict],
) -> str:
    name = (nav or {}).get("fund_name") or "This fund"
    rets = (nav or {}).get("returns") or {}
    one_m = rets.get("1m")
    try:
        one_m_f = float(one_m) if one_m is not None else None
    except (TypeError, ValueError):
        one_m_f = None

    top_sectors = [str(s.get("sector") or "") for s in sectors[:3] if s.get("sector")]
    top_hold = [str(h.get("name") or "") for h in holdings[:3] if h.get("name")]
    n_hold_news = sum(1 for a in articles if a.get("_news_layer") == "holding")
    n_sector_news = sum(1 for a in articles if a.get("_news_layer") == "sector")
    n_macro = sum(1 for a in articles if a.get("_news_layer") == "macro")

    p1: list[str] = [f"**{name}**"]
    if one_m_f is not None:
        tone = "under pressure" if one_m_f < -3 else "roughly flat" if abs(one_m_f) < 2 else "holding up"
        p1.append(f"has {tone} over the last month ({one_m_f:+.1f}%)")
    if top_sectors:
        p1.append(f"with most of the book in **{top_sectors[0]}**" + (f" and **{top_sectors[1]}**" if len(top_sectors) > 1 else ""))
    lead = " ".join(p1) + "."

    p2_parts: list[str] = []
    if top_hold:
        p2_parts.append(
            f"Headlines in our store most often touch **{', '.join(top_hold[:2])}** "
            f"({n_hold_news} holding-linked pieces in this window)."
        )
    if n_sector_news:
        p2_parts.append(
            f"Sector stories ({n_sector_news}) matter because those industries make up a large share of the portfolio."
        )
    if n_macro:
        p2_parts.append(
            f"Macro coverage ({n_macro} items) — rates, crude, rupee — sets the backdrop for those sectors even when a single stock is not named."
        )
    body = " ".join(p2_parts) if p2_parts else (
        "News in this window was thin; rely on NAV and weights above until fresher headlines land in the store."
    )

    close = (
        "This is a factual recap of NAV, weights, and stored news — not a recommendation to buy, sell, or hold."
    )
    return f"{lead} {body} {close}"
