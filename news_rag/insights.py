"""Build readable insight text from retrieved articles (LLM fallback)."""

from __future__ import annotations

import re

from news_rag.parse import ParsedQuery

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


def _informative_takeaway(snippet: str, title: str, *, limit: int = 220) -> str:
    cleaned = " ".join((snippet or "").split())
    if not cleaned:
        return title
    sentences = [part.strip() for part in _SENTENCE_END.split(cleaned) if part.strip()]
    useful: list[str] = []
    for sentence in sentences:
        if _looks_like_title(sentence, title):
            continue
        useful.append(sentence)
        if len(useful) >= 2:
            break
    if not useful:
        useful = [_first_sentence(cleaned, limit=limit)]
    text = " ".join(useful)
    if len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


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
        takeaway = _informative_takeaway(row.get("snippet") or "", title)
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
