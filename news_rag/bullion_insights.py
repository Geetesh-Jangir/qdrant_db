"""Gold/silver drop drivers — filter news and build analyst bullets (not equity paste)."""

from __future__ import annotations

import re
from typing import Any

from news_rag.bullion_retrieve import MACRO_GOLD, MACRO_SILVER
from news_rag.insights import _informative_takeaway
from news_rag.snippet_clean import clean_scraped_snippet, looks_like_raw_scrape

_BULLION_TERMS = re.compile(
    r"\b(gold|silver|bullion|precious\s*metal|mcx|ibja|xau|xag|"
    r"gold\s+etf|sgb|sovereign\s+gold|jewell?ery|import(?:s)?\s+of\s+gold)\b",
    re.I,
)
_OFF_TOPIC = re.compile(
    r"\b(solar\s+industries|omnia\s+holdings|defence\s+fund|strait\s+of\s+hormuz|"
    r"bharat\s+electronics|under-recover|OMC|HPCL|BPCL)\b",
    re.I,
)
_MACRO_RATES = re.compile(
    r"\b(dollar|dxy|rupee|usd/?inr|fed|real\s+yield|bond\s+yield|"
    r"rate\s+hike|repo\s+rate|rbi|inflation|cpi)\b",
    re.I,
)


def _article_blob(article: dict) -> str:
    parts = [
        str(article.get("title") or ""),
        clean_scraped_snippet(str(article.get("snippet") or "")),
        " ".join(str(x) for x in (article.get("entity_names") or [])[:8]),
        " ".join(str(x) for x in (article.get("sector_names") or [])[:6]),
    ]
    return " ".join(parts)


def is_macro_bullion_tagged(article: dict) -> bool:
    ents = {str(e) for e in (article.get("entity_names") or [])}
    return MACRO_GOLD in ents or MACRO_SILVER in ents


def score_bullion_article(article: dict) -> int:
    blob = _article_blob(article)
    if not blob.strip():
        return -10
    score = 0
    if is_macro_bullion_tagged(article):
        score += 8
    if _BULLION_TERMS.search(blob):
        score += 4
    if re.search(r"\b(fall|fell|decline|drop|slip|weak|correction|profit)\b", blob, re.I):
        score += 1
    if _MACRO_RATES.search(blob):
        score += 2
    if _OFF_TOPIC.search(blob) and not _BULLION_TERMS.search(blob):
        score -= 8
    if _OFF_TOPIC.search(blob) and _BULLION_TERMS.search(blob):
        score += 1
    return score


def filter_bullion_articles(articles: list[dict], *, min_score: int = 2) -> list[dict]:
    ranked = sorted(
        articles,
        key=lambda a: (is_macro_bullion_tagged(a), score_bullion_article(a)),
        reverse=True,
    )
    picked = [
        a
        for a in ranked
        if is_macro_bullion_tagged(a) or score_bullion_article(a) >= min_score
    ]
    return picked[:8]


def _bullion_theme_paraphrase(snippet: str, title: str) -> str:
    blob = clean_scraped_snippet(snippet)
    if not blob:
        blob = " ".join((title or "").split())
    low = blob.lower()
    if "trade deficit" in low and "gold import" in low:
        return (
            "**Domestic demand:** India's trade deficit narrowed as gold imports fell sharply — "
            "less fresh buying in the local market can weigh on rupee gold after prior heavy inflows."
        )
    if _MACRO_RATES.search(blob) and _BULLION_TERMS.search(blob):
        return (
            "**Macro headwind:** Coverage links the bullion move to rates/rupee/dollar moves — "
            "higher real yields and a stronger USD typically pressure non-yielding gold and silver."
        )
    if re.search(r"\b(mcx|futures)\b", low) and _BULLION_TERMS.search(blob):
        return (
            "**MCX/futures:** Domestic gold and silver futures weakened in the window — "
            "that feeds straight into ETF/FoF and jewellery-linked portfolio marks."
        )
    if re.search(r"\b(etf|fof|mutual fund)\b", low) and _BULLION_TERMS.search(blob):
        return (
            "**Fund channel:** News flags precious-metal funds/ETFs reacting to the spot move — "
            "gold and silver FoFs track the underlying bullion tape, not diversified equity beta."
        )
    if re.search(r"\b(safe.?haven|geopolitical)\b", low) and _BULLION_TERMS.search(blob):
        return (
            "**Safe-haven flows:** Geopolitical headlines moved bullion — when risk assets stabilize, "
            "gold can give back prior hedge-demand gains even if energy stays volatile."
        )
    return ""


def metals_inferred_driver_bullets(metals: dict[str, Any] | None) -> list[str]:
    if not metals:
        return []
    recap = metals.get("recap") if isinstance(metals.get("recap"), dict) else metals
    if not isinstance(recap, dict):
        return []

    bullets: list[str] = []
    try:
        g7 = float(recap.get("gold_7d_change_pct"))
        s7 = float(recap.get("silver_7d_change_pct"))
        g_latest = float(recap.get("gold_24k_latest_10g") or 0)
        g_max = float(recap.get("gold_24k_30d_max_10g") or 0)
        s_latest = float(recap.get("silver_latest_kg") or 0)
        s_max = float(recap.get("silver_30d_max_kg") or 0)
    except (TypeError, ValueError):
        return []

    if g7 < -0.5 and g_max > 0 and g_latest > 0:
        off_high = (g_latest / g_max - 1.0) * 100.0
        if off_high < -0.5:
            bullets.append(
                f"**Pullback from highs:** 24K gold is about {abs(off_high):.1f}% below its recent "
                f"30-day peak — consistent with profit-booking after a strong run, not a single-day glitch."
            )
    if s7 < g7 - 1.0:
        bullets.append(
            "**Silver beta:** Silver's weekly drop was steeper than gold's — industrial-metal "
            "sensitivity often amplifies bullion corrections when liquidity tightens."
        )
    if g7 < 0 and s7 < 0:
        bullets.append(
            "**Common driver:** Gold and silver fell together in the spot tape — that pattern usually "
            "points to macro (rupee, rates, dollar) or broad demand cooling rather than one equity story."
        )
    if s_max > 0 and s_latest > 0 and s7 < -1.0:
        off_s = (s_latest / s_max - 1.0) * 100.0
        if off_s < -1.0:
            bullets.append(
                f"**Silver range:** Silver is roughly {abs(off_s):.1f}% below its 30-day high — "
                f"aligns with the sharper {s7:+.2f}% weekly move vs gold {g7:+.2f}%."
            )
    return bullets[:3]


def bullion_news_driver_bullets(articles: list[dict], *, limit: int = 3) -> list[str]:
    pool = filter_bullion_articles(articles)
    out: list[str] = []
    seen: set[str] = set()
    for art in pool:
        title = (art.get("title") or "").strip()
        snippet = str(art.get("snippet") or "")
        themed = _bullion_theme_paraphrase(snippet, title)
        line = themed
        if not line:
            take = _informative_takeaway(snippet, title, limit=200)
            if take and not looks_like_raw_scrape(take) and _BULLION_TERMS.search(take):
                line = f"**From stored news:** {take}"
        if not line or line in seen:
            continue
        seen.add(line)
        out.append(line)
        if len(out) >= limit:
            break
    return out


def _metal_headline_label(article: dict) -> str:
    ents = {str(e) for e in (article.get("entity_names") or [])}
    if MACRO_SILVER in ents:
        return "Silver"
    if MACRO_GOLD in ents:
        return "Gold"
    blob = _article_blob(article).lower()
    if re.search(r"\bsilver\b", blob) and not re.search(r"\bgold\b", blob):
        return "Silver"
    if re.search(r"\bgold\b", blob):
        return "Gold"
    return "Bullion"


def bullion_article_bullet(article: dict) -> str:
    title = (article.get("title") or "").strip()
    snippet = str(article.get("snippet") or "")
    label = _metal_headline_label(article)
    take = _informative_takeaway(snippet, title, limit=210)
    if take and not looks_like_raw_scrape(take):
        return f"**{label}:** {take}"
    themed = _bullion_theme_paraphrase(snippet, title)
    if themed:
        return themed.replace("**", f"**{label} — ", 1) if themed.startswith("**") else f"**{label}:** {themed}"
    if title:
        short = clean_scraped_snippet(title)
        if short and len(short) > 20:
            return f"**{label}:** {short}"
    return ""


def metals_tape_bullets(metals: dict[str, Any] | None) -> list[str]:
    if not metals:
        return []
    recap = metals.get("recap") if isinstance(metals.get("recap"), dict) else metals
    if not isinstance(recap, dict):
        return []
    g7 = recap.get("gold_7d_change_pct")
    s7 = recap.get("silver_7d_change_pct")
    g1 = recap.get("gold_1d_change_pct")
    s1 = recap.get("silver_1d_change_pct")
    g_px = recap.get("gold_24k_latest_10g")
    s_px = recap.get("silver_latest_kg")
    try:
        parts = [
            f"**Spot (IBJA):** 24K gold 7d {float(g7 or 0):+.2f}%; silver 7d {float(s7 or 0):+.2f}% "
            f"(1d gold {float(g1 or 0):+.2f}%, silver {float(s1 or 0):+.2f}%)."
        ]
        if g_px is not None and s_px is not None:
            parts.append(
                f"**Levels:** ~₹{float(g_px):,.0f}/10g gold; ~₹{float(s_px):,.0f}/kg silver (latest benchmark in store)."
            )
        return parts
    except (TypeError, ValueError):
        return []


def _ranking_bullet(rankings: list[dict] | None) -> str:
    if not rankings:
        return ""
    names = []
    for row in rankings[:5]:
        name = row.get("fund_name") or row.get("isin")
        w = row.get("sector_weight_pct")
        if not name:
            continue
        if w is not None:
            try:
                names.append(f"**{name}** ({float(w):.1f}%)")
            except (TypeError, ValueError):
                names.append(f"**{name}**")
        else:
            names.append(f"**{name}**")
    if not names:
        return ""
    return "Funds with the highest metals/energy-adjacent weights in our ranking: " + "; ".join(names) + "."


def compose_macro_metals_insight(
    articles: list[dict],
    metals: dict[str, Any] | None,
    rankings: list[dict] | None,
) -> tuple[list[str], str, list[dict[str, Any]]]:
    """Structured macro-metals answer: spot | news drivers | fund exposure."""
    tape = metals_tape_bullets(metals)
    pool = filter_bullion_articles(articles)
    news_lines: list[str] = []
    seen: set[str] = set()
    for art in pool:
        line = bullion_article_bullet(art)
        if line and line not in seen:
            seen.add(line)
            news_lines.append(line)
        if len(news_lines) >= 4:
            break

    if news_lines:
        context_lines = list(news_lines)
        if len(news_lines) < 2:
            context_lines.extend(metals_inferred_driver_bullets(metals)[:1])
    else:
        context_lines = metals_inferred_driver_bullets(metals)[:3]
        if not context_lines:
            context_lines = [
                "**News gap:** No Macro - Gold / Macro - Silver tagged articles in this window — "
                "drivers below are from the spot tape only."
            ]

    fund_line = _ranking_bullet(rankings)
    fund_bullets = [fund_line] if fund_line else []

    insight_sections = [
        {"heading": "Spot move (IBJA)", "bullets": tape or ["**Spot:** Benchmark recap unavailable in this run."]},
        {"heading": "Why prices moved (stored macro news)", "bullets": context_lines},
        {"heading": "Mutual fund exposure", "bullets": fund_bullets or ["No sector-fund ranking returned for this query."]},
    ]

    flat = []
    for sec in insight_sections:
        flat.extend(sec["bullets"])

    macro_n = sum(1 for a in pool if is_macro_bullion_tagged(a))
    summary = (
        f"Gold and silver weakened on the official India bullion tape; {macro_n} article(s) in our store "
        f"are tagged Macro - Gold / Macro - Silver with the drivers above. "
        f"Precious-metal FoFs and commodity-heavy funds move with spot; diversified equity funds are indirect."
    )
    return flat, summary, insight_sections
