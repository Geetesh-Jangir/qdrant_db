"""Tie each news theme to a holding weight and its sector, or to a sector or macro line."""

from __future__ import annotations

import re
from typing import Any

_DROP_WORDS = re.compile(r"\b(ltd|limited|inc|pvt|private|company|co)\b\.?", re.I)


def _key(name: str) -> str:
    text = _DROP_WORDS.sub(" ", name or "")
    text = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    return " ".join(text.split())


def _pct(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number == 0:
        return None
    return round(number, 2)


def _match(theme: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    key = _key(theme)
    if not key:
        return None
    for row in rows:
        row_key = _key(str(row.get("name") or row.get("sector") or ""))
        if not row_key:
            continue
        if key == row_key or key in row_key or row_key in key:
            return row
    head = key.split()[0]
    if len(head) < 4:
        return None
    for row in rows:
        row_key = _key(str(row.get("name") or row.get("sector") or ""))
        if row_key.startswith(head):
            return row
    return None


def _fact(title: str, summary: str = "") -> str:
    body = " ".join((summary or "").split())
    if len(body) >= 40:
        return body[:500]
    text = re.sub(r"\s+[-–—|]\s+[^-–—|]{0,40}$", "", title or "").strip()
    return text[:180]


def _portfolio_rows(data_pack: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    holdings: list[dict[str, Any]] = []
    sectors: list[dict[str, Any]] = []
    fund_name = ""
    for key, block in (data_pack or {}).items():
        if not str(key).startswith("portfolio:") or not isinstance(block, dict):
            continue
        fund_name = str(block.get("fund_name") or fund_name)
        holdings.extend(row for row in (block.get("holdings") or []) if isinstance(row, dict))
        sectors.extend(row for row in (block.get("sectors") or []) if isinstance(row, dict))
    return holdings, sectors, fund_name


def _wider_holdings(fund_name: str) -> list[dict[str, Any]]:
    if not fund_name:
        return []
    from news_rag.fund_search import extract_top_holdings, normalize_holding_row, resolve_fund_for_query

    detail, _amb, _close = resolve_fund_for_query(fund_name)
    if not detail:
        return []
    return [normalize_holding_row(row) for row in extract_top_holdings(detail, limit=40)]


def build_insight_links(data_pack: dict[str, Any], news_grouped: dict[str, Any]) -> list[dict[str, Any]]:
    """One card per news theme: holding weight and sector, sector weight, or macro."""
    holdings, sectors, fund_name = _portfolio_rows(data_pack)
    grouped = news_grouped or {}
    themes: dict[str, list[str]] = {}
    for scope in ("holdings", "sectors", "macro"):
        for article in grouped.get(scope) or []:
            if not isinstance(article, dict):
                continue
            theme = str(article.get("theme") or article.get("title") or "").strip()
            fact = _fact(
                str(article.get("title") or ""),
                str(article.get("summary") or article.get("text") or ""),
            )
            if not theme or not fact:
                continue
            bucket = themes.setdefault(f"{scope}|{theme}", [])
            if fact not in bucket and len(bucket) < 4:
                bucket.append(fact)

    links: list[dict[str, Any]] = []
    seen: set[str] = set()
    needs_wider = False
    holding_themes = [key.split("|", 1)[1] for key in themes if key.startswith("holdings|")]
    for theme in holding_themes:
        if _match(theme, holdings) is None:
            needs_wider = True
            break
    if needs_wider:
        for row in _wider_holdings(fund_name):
            if _match(str(row.get("name") or ""), holdings) is None:
                holdings.append(row)

    for raw_key, facts in themes.items():
        scope, theme = raw_key.split("|", 1)
        if scope == "holdings":
            row = _match(theme, holdings)
            if row is None:
                continue
            weight = _pct(row.get("weight_pct") if row.get("weight_pct") is not None else row.get("percentage"))
            sector = str(row.get("sector") or row.get("industry") or "").strip()
            if weight is None:
                continue
            name = str(row.get("name") or theme)
            marker = _key(name)
            if marker in seen:
                continue
            seen.add(marker)
            links.append({
                "kind": "holding",
                "name": name,
                "weight_pct": weight,
                "sector": sector,
                "points": facts,
            })
        elif scope == "sectors":
            row = _match(theme, sectors)
            weight = _pct(row.get("weight_pct") if row else None)
            if weight is None and row is not None:
                weight = _pct(row.get("percentage"))
            if weight is None:
                continue
            label = str((row or {}).get("sector") or theme)
            marker = "sector:" + _key(label)
            if marker in seen:
                continue
            seen.add(marker)
            links.append({
                "kind": "sector",
                "name": label,
                "weight_pct": weight,
                "points": facts,
            })
        else:
            links.append({"kind": "macro", "name": theme, "points": facts})
    return links
