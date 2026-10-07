"""Direct holdings/weights and indirect news co-occurrence for one driver and target."""

from __future__ import annotations

import re
from typing import Any

from news_rag.sector_fund_ranking import rank_funds_by_sector_exposure


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _matches(needle: str, hay: str) -> bool:
    left = _norm(needle)
    right = _norm(hay)
    if not left or not right or len(left) < 3:
        return False
    return left in right or right in left


def _article_blob(article: dict[str, Any]) -> str:
    parts = [
        str(article.get("title") or ""),
        str(article.get("snippet") or ""),
        str(article.get("body") or ""),
        " ".join(str(x) for x in (article.get("entity_names") or [])),
        " ".join(str(x) for x in (article.get("holding_names") or [])),
        " ".join(str(x) for x in (article.get("sector_names") or [])),
    ]
    return " ".join(parts)


def _names_on_article(article: dict[str, Any]) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for name in article.get("holding_names") or []:
        if str(name).strip():
            found.append((str(name).strip(), "holding"))
    for name in article.get("entity_names") or []:
        if str(name).strip():
            found.append((str(name).strip(), "entity"))
    for name in article.get("sector_names") or []:
        if str(name).strip():
            found.append((str(name).strip(), "sector"))
    industry = str(article.get("primary_industry") or "").strip()
    if industry:
        found.append((industry, "sector"))
    return found


def trace_relationships(
    *,
    driver: str,
    target: str = "",
    holdings_rows: list[dict[str, Any]] | None = None,
    sector_rows: list[dict[str, Any]] | None = None,
    articles: list[dict[str, Any]] | None = None,
    fund_name: str = "",
) -> dict[str, Any]:
    """Return computed links only. No canned market sentence."""
    driver = (driver or "").strip()
    target = (target or "").strip()
    direct: list[dict[str, Any]] = []
    for row in holdings_rows or []:
        name = str(row.get("name") or "")
        if _matches(driver, name) or (target and _matches(target, name)):
            direct.append(
                {
                    "kind": "direct",
                    "channel": "holding",
                    "name": name,
                    "weight_pct": row.get("percentage") or row.get("weight_pct"),
                    "fund_name": fund_name,
                }
            )
    for row in sector_rows or []:
        name = str(row.get("sector") or row.get("name") or "")
        if _matches(driver, name) or (target and _matches(target, name)):
            direct.append(
                {
                    "kind": "direct",
                    "channel": "sector_weight",
                    "name": name,
                    "weight_pct": row.get("percentage") or row.get("weight_pct"),
                    "fund_name": fund_name,
                }
            )

    indirect: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for article in articles or []:
        blob = _article_blob(article)
        if not _matches(driver, blob) and driver.lower() not in blob.lower():
            continue
        for name, kind in _names_on_article(article):
            if _matches(driver, name):
                continue
            key = (_norm(name), kind)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            indirect.append(
                {
                    "kind": "indirect",
                    "channel": "news_cooccurrence",
                    "name": name,
                    "via": kind,
                    "article_title": str(article.get("title") or "")[:180],
                    "direction": article.get("direction"),
                }
            )

    sector_channel: list[dict[str, Any]] = []
    sector_query = target or driver
    if sector_query:
        try:
            ranked = rank_funds_by_sector_exposure([sector_query], limit=5)
        except Exception:
            ranked = {}
        rows = ranked.get("rankings") or [] if isinstance(ranked, dict) else []
        for row in list(rows)[:5]:
            if not isinstance(row, dict):
                continue
            sector_channel.append(
                {
                    "kind": "sector_channel",
                    "sector": sector_query,
                    "fund_name": row.get("fund_name"),
                    "sector_weight_pct": row.get("sector_weight_pct"),
                    "isin": row.get("isin"),
                }
            )

    return {
        "driver": driver,
        "target": target,
        "fund_name": fund_name,
        "direct": direct,
        "indirect_news": indirect[:12],
        "sector_channel": sector_channel,
    }
