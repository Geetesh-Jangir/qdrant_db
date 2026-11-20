"""Score and filter holding news before the LLM."""

from __future__ import annotations

import re
from typing import Any, Literal

from news_rag.article_pool import article_dedupe_key
from news_rag.holdings_market import _article_mentions_holding
from news_rag.insight.article_quality import text_relevance_hits
from news_rag.snippet_clean import article_body_for_llm, article_text_usable, starts_mid_sentence

from new.security_master import normalize_name

Move = Literal["up", "down"]
_MIN_BODY = 160
_MIN_IMPACT = 1
_DEFAULT_MIN_SCORE = 4.0
_ABOUT_MIN = 0.25

_BREADCRUMB = re.compile(
    r"home\s*/\s*markets|listen to (?:this|the) article|explore business standard",
    re.I,
)
_ROUNDUP_TITLE = re.compile(
    r"stocks? in focus|nse\s*500|more nse|at new highs|dalal street.*(?:fell|rose)|"
    r"^\s*crude-sensitive stocks|several stocks|top \d+ stocks|stocks to watch",
    re.I,
)
_MULTI_TICKER_TITLE = re.compile(
    r"\b(?:and|&|,)\s+(?:more\s+)?(?:\d+\s+)?(?:nse|stocks?|shares?)\b",
    re.I,
)


def _stock_terms(instrument_name: str) -> set[str]:
    core = normalize_name(instrument_name)
    tokens = {t for t in core.split() if len(t) >= 4}
    short = re.sub(r"\s+(limited|ltd)\b", "", instrument_name.lower(), flags=re.I).strip()
    for part in short.split():
        if len(part) >= 5:
            tokens.add(part)
    return tokens


def _title_mentions_stock(instrument_name: str, title: str) -> bool:
    title_low = (title or "").lower()
    terms = _stock_terms(instrument_name)
    if not terms:
        return instrument_name.lower()[:12] in title_low
    return any(t in title_low for t in terms)


def _is_low_quality_article(row: dict[str, Any], instrument_name: str) -> str | None:
    title = str(row.get("title") or "")
    body = article_body_for_llm(row, limit=800)
    blob = f"{title} {body}"
    if _BREADCRUMB.search(blob):
        return "breadcrumb"
    if _ROUNDUP_TITLE.search(title):
        return "roundup"
    if _MULTI_TICKER_TITLE.search(title) and not _title_mentions_stock(instrument_name, title):
        return "multi_ticker"
    if title.count(",") >= 2 and "focus" in title.lower():
        return "roundup"
    if not _article_mentions_holding(instrument_name, row):
        return "entity_mismatch"
    if not _title_mentions_stock(instrument_name, title):
        return "title_no_stock"
    about = row.get("about_this_name")
    if about is not None:
        try:
            if float(about) < _ABOUT_MIN:
                return "low_about"
        except (TypeError, ValueError):
            pass
    return None


def score_article(row: dict[str, Any], instrument_name: str, move: Move) -> float:
    reject = _is_low_quality_article(row, instrument_name)
    if reject:
        return -100.0

    title = str(row.get("title") or "")
    body = article_body_for_llm(row, limit=0)
    title_ok = bool(title.strip() and article_text_usable(title) and not starts_mid_sentence(title))
    body_ok = bool(body.strip() and article_text_usable(body))
    if not body_ok and not title_ok:
        return -100.0
    if len(body.strip()) < _MIN_BODY and not title_ok:
        return -100.0

    impact = int(row.get("max_impact") or 0)
    if impact < _MIN_IMPACT:
        return -100.0
    if str(row.get("event_type") or "") == "price_recap" and impact < 2:
        return -50.0

    score = float(impact) * 2.5
    score += min(len(body) / 400.0, 3.5)
    vec = _vector_strength(row)
    score += min(vec * 3.0, 4.0)
    if body_ok:
        score += 2.0
    if title_ok:
        score += 0.5
    score += 2.5

    terms = _stock_terms(instrument_name)
    hits = text_relevance_hits(f"{title} {body}", terms)
    score += min(hits * 1.2, 4.0)

    d = str(row.get("direction") or "").lower()
    if move == "up" and d != "negative":
        score += 1.5
    elif move == "down" and d != "positive":
        score += 1.5
    else:
        score -= 8.0

    try:
        rel = float(row.get("relevancy_score") or row.get("relevance") or 0)
        score += min(rel / 2.0, 3.0)
    except (TypeError, ValueError):
        pass

    return score


def _vector_strength(row: dict[str, Any]) -> float:
    for key in ("_vector_score", "score"):
        try:
            val = float(row.get(key) or 0)
        except (TypeError, ValueError):
            continue
        if val > 0:
            return val
    return 0.0


def merge_article_pool(*lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for rows in lists:
        for row in rows:
            if not isinstance(row, dict):
                continue
            key = article_dedupe_key(row) or str(row.get("url") or "").strip()
            if not key:
                continue
            prev = by_key.get(key)
            if prev is None or _vector_strength(row) >= _vector_strength(prev):
                by_key[key] = row
    return list(by_key.values())


def rank_and_pick_articles(
    instrument_name: str,
    move: Move,
    rows: list[dict[str, Any]],
    *,
    limit: int = 8,
    min_score: float = _DEFAULT_MIN_SCORE,
) -> list[dict[str, Any]]:
    scored: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        s = score_article(row, instrument_name, move)
        if s >= min_score:
            scored.append((s, {**row, "_pick_score": round(s, 3)}))
    scored.sort(key=lambda x: (-x[0], -int(x[1].get("max_impact") or 0)))
    return [r for _, r in scored[:limit]]


def filter_usable_articles(
    instrument_name: str,
    move: Move,
    rows: list[dict[str, Any]],
    *,
    limit: int = 8,
    min_score: float = _DEFAULT_MIN_SCORE,
) -> list[dict[str, Any]]:
    return rank_and_pick_articles(instrument_name, move, rows, limit=limit, min_score=min_score)