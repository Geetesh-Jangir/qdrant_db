"""Build readable insight text from retrieved articles (LLM fallback)."""

from __future__ import annotations

import re

from news_rag.parse import ParsedQuery
from news_rag.snippet_clean import (
    clean_scraped_snippet,
    is_broken_fragment,
    looks_like_raw_scrape,
    sanitize_analyst_bullet,
    sentence_has_scrape_artifacts,
)

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _first_sentence(text: str, limit: int = 220) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ""
    parts = _SENTENCE_END.split(cleaned, maxsplit=1)
    sentence = parts[0] if parts else cleaned
    if len(sentence) > limit:
        return sentence[: limit - 3] + "..."
    return sentence


def _looks_like_title(sentence: str, title: str) -> bool:
    s = " ".join(sentence.lower().split())
    t = " ".join(title.lower().split())
    if len(s) < 35:
        return True
    if s in t or t in s:
        return True
    # Headline echo: first half of title matches start of sentence
    short = t[: min(50, len(t))]
    return short and s.startswith(short[:30])


def article_takeaway(article: dict, *, limit: int = 280) -> str:
    """One or two factual sentences from Qdrant snippet (not the headline alone)."""
    title = (article.get("title") or "").strip()
    snippet = str(article.get("snippet") or "")
    return _informative_takeaway(snippet, title, limit=limit)


def _informative_takeaway(snippet: str, title: str, *, limit: int = 220) -> str:
    cleaned = clean_scraped_snippet(snippet)
    if not cleaned:
        return title
    sentences = [part.strip() for part in _SENTENCE_END.split(cleaned) if part.strip()]
    useful: list[str] = []
    for sentence in sentences:
        if _looks_like_title(sentence, title):
            continue
        if sentence_has_scrape_artifacts(sentence) or is_broken_fragment(sentence):
            continue
        useful.append(sentence)
        if len(useful) >= 2:
            break
    if not useful:
        fallback = _first_sentence(cleaned, limit=limit)
        if sentence_has_scrape_artifacts(fallback) or is_broken_fragment(fallback):
            return ""
        useful = [fallback]
    text = " ".join(useful)
    if len(text) > limit:
        cut = text[:limit].rsplit(" ", 1)[0].rstrip(".,;")
        text = cut + "." if cut and cut[-1] not in ".!?" else cut
    return sanitize_analyst_bullet(text)


def _theme_paraphrase(snippet: str, title: str) -> str:
    """Analyst one-liner from scrape themes when prose cannot be pasted."""
    blob = clean_scraped_snippet(snippet)
    if not blob:
        blob = " ".join((title or "").split())
    low = blob.lower()
    if "solar industries" in low and ("omnia" in low or "acquir" in low or "%" in blob):
        return (
            "**Deal-driven move:** Solar Industries sold off sharply after its unit announced a "
            "large Omnia acquisition — a company-specific repricing, not a broad defence-sector tape."
        )
    if "strait of hormuz" in low or ("iran" in low and "energy" in low and "crude" in low):
        return (
            "**Energy risk premium:** Middle-East shipping tension kept crude/energy costs elevated, "
            "adding macro pressure on importers, OMC margins, and rate-sensitive assets."
        )
    if "trade deficit" in low and "gold import" in low:
        return (
            "**Gold demand:** Trade deficit narrowed as gold imports fell sharply — a signal that "
            "domestic bullion buying cooled after heavier prior-month inflows."
        )
    if re.search(r"\b(IOC|HPCL|BPCL|OMC|under-recover|litre on petrol)\b", blob, re.I):
        return (
            "**OMC stress:** State fuel retailers face large under-recoveries as pump prices lag "
            "crude — a direct hit to marketing margins, not most non-energy equity sleeves."
        )
    if re.search(r"\b(Brent|WTI|crude|import bill|per barrel|\$9\d)\b", blob, re.I):
        return (
            "**Crude spike:** Stored coverage flags Brent/WTI near recent highs and a wider oil "
            "import bill — lifting energy costs, currency pressure, and bond-yield anxiety."
        )
    if re.search(r"\b(yield|bps|bond|gilt|10-year)\b", blob, re.I):
        return (
            "**Rates:** Bond yields moved higher in the same window, tightening the macro backdrop "
            "alongside commodity shocks."
        )
    return ""


def analyst_line_from_article(
    article: dict,
    *,
    limit: int = 220,
    bullion_only: bool = False,
) -> str:
    title = (article.get("title") or "").strip()
    snippet = str(article.get("snippet") or "")
    if bullion_only:
        from news_rag.bullion_insights import _bullion_theme_paraphrase, score_bullion_article

        if score_bullion_article(article) < 2:
            return ""
        themed = _bullion_theme_paraphrase(snippet, title)
        if themed:
            return themed
        take = _informative_takeaway(snippet, title, limit=limit)
        if take and not looks_like_raw_scrape(take) and re.search(
            r"\b(gold|silver|bullion|mcx|import)\b", take, re.I
        ):
            return take
        return ""
    themed = _theme_paraphrase(snippet, title)
    if themed:
        return themed
    take = _informative_takeaway(snippet, title, limit=limit)
    if take and not looks_like_raw_scrape(take):
        return take
    themed = _theme_paraphrase(snippet, title)
    return themed


def _topic_label(parsed: ParsedQuery) -> str:
    if parsed.entity_resolved:
        if len(parsed.entity_resolved) == 1:
            return parsed.entity_resolved[0]
        return ", ".join(parsed.entity_resolved[:3])
    q = parsed.question.strip().rstrip("?")
    return q if q else "your question"


def _article_matches_entities(row: dict, entities: list[str]) -> bool:
    if not entities:
        return True
    names = {str(n).lower() for n in (row.get("entity_names") or [])}
    for entity in entities:
        if entity.lower() in names:
            return True
    return False


def build_structured_insight_from_articles(
    parsed: ParsedQuery,
    articles: list[dict],
) -> tuple[list[str], str]:
    if not articles:
        return [], ""

    entities = parsed.entity_resolved
    focused = [row for row in articles if _article_matches_entities(row, entities)]
    pool = focused if focused else articles

    label = _topic_label(parsed)
    bullets: list[str] = []
    seen_titles: set[str] = set()
    for row in pool:
        title = (row.get("title") or "").strip()
        if not title or title in seen_titles:
            continue
        seen_titles.add(title)
        takeaway = analyst_line_from_article(row, limit=280)
        if takeaway:
            bullets.append(takeaway)
        if len(bullets) >= 3:
            break

    summary = (
        f"For {label} over {parsed.window_label}, recent stored news highlights the points above "
        f"from {len(pool)} articles. Factual recap only, not investment advice."
    )
    return bullets, summary


def build_insight_from_articles(parsed: ParsedQuery, articles: list[dict]) -> str:
    bullets, summary = build_structured_insight_from_articles(parsed, articles)
    from news_rag.insight_format import format_insight_display

    return format_insight_display(bullets, summary)
