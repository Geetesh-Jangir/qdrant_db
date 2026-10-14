"""Rank and filter retrieved news before LLM stages — query-agnostic, driven by brief + evidence."""

from __future__ import annotations

import re
from typing import Any

from news_rag.insight.brief import QuestionBrief
from news_rag.snippet_clean import article_body_for_llm, article_text_usable, starts_mid_sentence

# Tokens so generic they rarely distinguish relevance for any question.
_STOP_TOKENS = frozenset(
    {
        "fund",
        "funds",
        "mutual",
        "scheme",
        "with",
        "what",
        "about",
        "happening",
        "recent",
        "market",
        "india",
        "indian",
        "stock",
        "stocks",
        "share",
        "shares",
    }
)


def _tokenize(text: str, *, min_len: int = 4) -> set[str]:
    return {
        t
        for t in re.findall(rf"[a-z]{{{min_len},}}", (text or "").lower())
        if t not in _STOP_TOKENS
    }


def _has_movers(evidence: Any) -> bool:
    for item in getattr(evidence, "items", []) or []:
        if getattr(item, "facet", "") != "fund_attribution":
            continue
        d = item.data if isinstance(item.data, dict) else {}
        for fund in d.get("funds") or []:
            attr = fund.get("attribution") if isinstance(fund, dict) else None
            if isinstance(attr, dict) and (attr.get("detractors") or attr.get("contributors")):
                return True
    return False


def relevance_terms(
    brief: QuestionBrief | None,
    evidence: Any = None,
    *,
    question: str = "",
) -> set[str]:
    """Terms that define what “on-topic” means for this run (no fixed sector/topic lists)."""
    terms: set[str] = set()
    if not brief:
        if question:
            terms |= _tokenize(question)
        return terms

    for name in (brief.funds or []) + (brief.stocks or []):
        terms |= _tokenize(name)
    sector = brief.primary_sector()
    if sector:
        terms |= _tokenize(sector)
    for sk in brief.sector_keys or []:
        terms |= _tokenize(str(sk))
    for sub in brief.subjects or []:
        terms |= _tokenize(str(sub.get("canonical") or sub.get("raw") or ""))
    for d in brief.drivers or []:
        terms |= _tokenize(str(d).replace("_", " "))
    for ask in brief.sub_asks or []:
        terms |= _tokenize(getattr(ask, "text", "") or "")
    terms |= _tokenize(brief.goal)
    if question:
        terms |= _tokenize(question)

    for item in getattr(evidence, "items", []) or []:
        facet = getattr(item, "facet", "") or ""
        d = item.data if isinstance(item.data, dict) else {}
        if facet in ("fund_composition", "fund_facts_holdings") and not _has_movers(evidence):
            for h in d.get("holdings") or []:
                if isinstance(h, dict) and h.get("name"):
                    terms |= _tokenize(str(h.get("name")))
            for s in d.get("sectors") or []:
                if isinstance(s, dict) and s.get("sector"):
                    terms |= _tokenize(str(s.get("sector")))
        elif facet == "fund_attribution":
            for fund in d.get("funds") or []:
                if not isinstance(fund, dict):
                    continue
                attr = fund.get("attribution") if isinstance(fund.get("attribution"), dict) else {}
                for row in (attr.get("detractors") or []) + (attr.get("contributors") or []):
                    if isinstance(row, dict) and row.get("name"):
                        terms |= _tokenize(str(row.get("name")))
        elif facet in ("news_drivers", "holding_drivers", "fund_portfolio_news"):
            for key in ("sector", "isin", "entity", "name"):
                if d.get(key):
                    terms |= _tokenize(str(d.get(key)))

    for art in getattr(evidence, "articles", []) or []:
        if not isinstance(art, dict):
            continue
        if art.get("_attr_sector"):
            terms |= _tokenize(str(art.get("_attr_sector")))
        if art.get("_attr_isin"):
            terms |= _tokenize(str(art.get("_attr_isin")))

    return terms


def text_relevance_hits(text: str, terms: set[str]) -> int:
    if not terms:
        return 0
    blob = (text or "").lower()
    return sum(1 for t in terms if t in blob)


def claim_matches_label(claim_text: str, label: str, extra_terms: set[str] | None = None) -> bool:
    """Whether a news claim relates to a portfolio sleeve / driver label for this question."""
    terms = _tokenize(label, min_len=3) | (extra_terms or set())
    if not terms:
        return False
    blob = (claim_text or "").lower()
    return any(t in blob for t in terms)


def _impact(a: dict[str, Any]) -> float:
    try:
        return float(a.get("max_impact") or a.get("impact") or 0)
    except (TypeError, ValueError):
        return 0.0


def _body_len(a: dict[str, Any], char_limit: int) -> int:
    return len(article_body_for_llm(a, limit=char_limit) or "")


def _article_blob(a: dict[str, Any], char_limit: int) -> str:
    title = str(a.get("title") or "")
    body = article_body_for_llm(a, limit=char_limit) or ""
    return f"{title} {body}"


def _quality_score(
    a: dict[str, Any],
    *,
    terms: set[str],
    char_limit: int,
    min_impact: float = 2.0,
) -> float:
    title = str(a.get("title") or "")
    body = article_body_for_llm(a, limit=char_limit)
    attributed = bool(a.get("_attr_sector") or a.get("_attr_isin"))
    body_ok = bool(body and article_text_usable(body))
    title_ok = bool(title and article_text_usable(title))

    if not body_ok and not title_ok and not attributed:
        return -100.0
    if not body_ok and starts_mid_sentence(title) and not attributed:
        return -100.0

    score = _impact(a) * 2.0
    if attributed:
        score += 5.0
    score += min(_body_len(a, char_limit) / 400.0, 4.0)
    if body_ok:
        score += 1.5

    hits = text_relevance_hits(_article_blob(a, char_limit), terms)
    score += min(hits * 1.8, 8.0)

    if terms and not attributed and hits == 0 and _impact(a) < min_impact + 0.5:
        score -= 4.0
    if _impact(a) < min_impact and not attributed:
        score -= 1.5

    return score


def filter_quality_articles(
    articles: list[dict[str, Any]],
    *,
    brief: QuestionBrief | None = None,
    evidence: Any = None,
    question: str = "",
    char_limit: int = 3500,
    limit: int = 10,
    min_score: float = 1.0,
) -> list[dict[str, Any]]:
    """Highest-quality articles for LLM reading (impact, readable body, relevance to this question)."""
    terms = relevance_terms(brief, evidence, question=question)
    seen: set[str] = set()
    scored: list[tuple[float, dict[str, Any]]] = []
    for a in articles:
        if not isinstance(a, dict):
            continue
        key = re.sub(r"\W+", " ", str(a.get("title") or "")).strip().lower()[:90] or str(a.get("url") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        sc = _quality_score(a, terms=terms, char_limit=char_limit)
        if sc >= min_score:
            scored.append((sc, a))
    scored.sort(key=lambda x: x[0], reverse=True)
    attr = [a for _, a in scored if a.get("_attr_sector") or a.get("_attr_isin")]
    rest = [a for _, a in scored if not (a.get("_attr_sector") or a.get("_attr_isin"))]
    ordered = attr + rest
    return ordered[:limit]
