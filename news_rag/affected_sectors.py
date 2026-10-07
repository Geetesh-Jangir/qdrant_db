"""Choose sectors from the news, then the fund ranking uses only those names."""

from __future__ import annotations

import re
from typing import Any

from news_rag.llm_client import call_json_llm
from news_rag.snippet_clean import article_body_for_llm

_AFFECTED_RE = re.compile(
    r"\b(affected|affecting|impact(?:ed)?|due to|because of)\b",
    re.I,
)

_DIRECTION_LINES = {
    "positive": (
        "The user asked which funds are positively affected. "
        "Return only sectors that benefit. Do not return sectors that are hurt."
    ),
    "negative": (
        "The user asked which funds are hurt. "
        "Return only sectors that are hurt. Do not return sectors that benefit."
    ),
    "any": (
        "The user asked which funds are affected, without asking for only winners or only losers. "
        "Return both groups. Tag a sector positive when it benefits and negative when it is hurt."
    ),
}

PICKER_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "sectors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "direction": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        }
    },
    "required": ["sectors"],
}


def picker_direction_line(direction: str) -> str:
    asked = str(direction or "any").strip().lower()
    return _DIRECTION_LINES.get(asked, _DIRECTION_LINES["any"])


def question_needs_affected_sectors(question: str) -> bool:
    """Funds affected by a driver. Exposure, AMC, and category questions stay on the normal screen."""
    from news_rag.tools import _exposure_ask, screen_hints_from_question

    text = question or ""
    if not _AFFECTED_RE.search(text):
        return False
    if _exposure_ask(text):
        return False
    hints = screen_hints_from_question(text)
    if hints.get("category") or hints.get("amc") or hints.get("stock_name"):
        return False
    return bool(re.search(r"\bfunds?\b|\bschemes?\b", text, re.I))


def _article_lines(articles: list[dict[str, Any]], *, limit: int = 8) -> str:
    lines: list[str] = []
    for article in articles[:limit]:
        if not isinstance(article, dict):
            continue
        body = article_body_for_llm(article, limit=700).strip()
        if body:
            lines.append(body)
    return "\n\n".join(lines)


def build_picker_prompt(
    *,
    question: str,
    direction: str,
    articles: list[dict[str, Any]],
    sector_names: list[str],
) -> str:
    names = ", ".join(sector_names)
    return (
        f"{picker_direction_line(direction)}\n\n"
        f"Question: {question}\n\n"
        "Copy sector names only from this list. Drop any name that is not in the list. "
        "Do not invent a sector.\n"
        f"Sectors: {names}\n\n"
        "Articles:\n"
        f"{_article_lines(articles)}\n\n"
        "For each sector, give one sentence on why the articles say it moves that way."
    )


def accepted_sectors(
    raw: list[Any],
    sector_names: list[str],
    *,
    direction: str,
) -> list[dict[str, str]]:
    """Keep names that exist in the index and match the asked direction."""
    allowed = {name.casefold(): name for name in sector_names}
    asked = str(direction or "any").strip().lower()
    kept: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        canon = allowed.get(str(item.get("name") or "").strip().casefold())
        if not canon or canon in seen:
            continue
        tagged = str(item.get("direction") or asked).strip().lower()
        if tagged not in ("positive", "negative"):
            tagged = asked if asked in ("positive", "negative") else "positive"
        if asked in ("positive", "negative") and tagged != asked:
            continue
        seen.add(canon)
        kept.append(
            {
                "name": canon,
                "direction": tagged,
                "reason": str(item.get("reason") or "").strip(),
            }
        )
    return kept


def pick_affected_sectors(
    *,
    question: str,
    articles: list[dict[str, Any]],
    direction: str = "any",
    sector_names: list[str] | None = None,
    query_log: Any = None,
) -> list[dict[str, str]]:
    from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

    names = list(sector_names if sector_names is not None else get_sector_fund_ranking_index().sector_names)
    if not names:
        return []
    prompt = build_picker_prompt(
        question=question,
        direction=direction,
        articles=articles,
        sector_names=names,
    )
    result = call_json_llm(
        system_prompt=(
            "You choose sectors for an Indian mutual-fund question. "
            "Return JSON only. Use only the sector names you were given."
        ),
        user_content=prompt,
        max_tokens=800,
        temperature=0.0,
        query_log=query_log,
        response_schema=PICKER_RESPONSE_SCHEMA,
        stage="affected_sectors",
    )
    parsed = result.parsed if isinstance(result.parsed, dict) else {}
    raw = parsed.get("sectors") or []
    return accepted_sectors(raw if isinstance(raw, list) else [], names, direction=direction)


_COMPANY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"companies": {"type": "array", "items": {"type": "string"}}},
    "required": ["companies"],
}


def pick_affected_companies(
    *,
    question: str,
    articles: list[dict[str, Any]],
    direction: str = "any",
    query_log: Any = None,
) -> list[str]:
    """Company names the articles tie to the asked direction, kept only if the archive knows them."""
    from news_rag.stock_fund_ranking import _match_aggregated

    result = call_json_llm(
        system_prompt=(
            "You name Indian listed companies from news. Return JSON only. "
            "Copy names that appear in the articles."
        ),
        user_content=(
            f"{picker_direction_line(direction)}\n\n"
            f"Question: {question}\n\n"
            "Name the companies these articles say are affected in that direction. "
            "Do not invent a company that the articles do not mention.\n\n"
            f"Articles:\n{_article_lines(articles)}"
        ),
        max_tokens=400,
        temperature=0.0,
        query_log=query_log,
        response_schema=_COMPANY_SCHEMA,
        stage="affected_companies",
    )
    parsed = result.parsed if isinstance(result.parsed, dict) else {}
    raw = parsed.get("companies") or []
    kept: list[str] = []
    seen: set[str] = set()
    for item in raw if isinstance(raw, list) else []:
        matched = _match_aggregated(str(item))
        if not matched:
            continue
        name = matched[0]
        if name in seen:
            continue
        seen.add(name)
        kept.append(name)
    return kept[:3]
