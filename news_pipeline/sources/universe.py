"""Top holdings and sectors used as the daily search universe."""

from __future__ import annotations

import csv
import re
from collections import defaultdict

from news_pipeline.config import (
    EXTRA_ALIASES,
    SECTOR_BLOCK_FRAGMENTS,
    SECTOR_QUERIES,
    Settings,
)
from news_pipeline.textutil import contains_phrase

_LEGAL_RE = re.compile(r"\b(limited|ltd|inc|corp|corporation|plc)\b\.?", re.IGNORECASE)
_EQ_RE = re.compile(r"^eq\s*-\s*", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[a-z0-9]+")

_STOP_TOKENS = {
    "limited",
    "ltd",
    "india",
    "company",
    "industries",
    "the",
    "and",
    "of",
    "private",
    "international",
    "enterprise",
    "enterprises",
    "group",
    "bank",
    "power",
    "steel",
    "motors",
    "finance",
    "energy",
    "capital",
    "services",
    "insurance",
    "cement",
    "chemicals",
    "technology",
    "technologies",
    "solutions",
    "global",
    "national",
    "indian",
}


def canonical_key(name: str) -> str:
    text = _EQ_RE.sub("", name.strip())
    text = text.replace("&", " and ")
    text = _LEGAL_RE.sub("", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def short_name(name: str) -> str:
    text = _EQ_RE.sub("", name.strip())
    text = _LEGAL_RE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip(" .,-")
    if text.lower().startswith("the "):
        text = text[4:]
    return text.strip()


def _display_name(current: str, incoming: str, current_count: int, incoming_count: int) -> str:
    if _is_exchange_label(current) and not _is_exchange_label(incoming):
        return incoming
    if _is_exchange_label(incoming) and not _is_exchange_label(current):
        return current
    if incoming_count > current_count:
        return incoming
    return current


def _is_exchange_label(name: str) -> bool:
    return name.upper().startswith("EQ") or name.isupper()


def load_holdings(settings: Settings) -> list[dict]:
    path = settings.path(settings.holdings_csv)
    grouped: dict[str, dict] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            raw_name = (row.get("instrument_name") or "").strip()
            if not raw_name:
                continue
            key = canonical_key(raw_name)
            if not key:
                continue
            fund_count = int(float(row.get("fund_count") or 0))
            total_percentage = float(row.get("total_percentage") or 0)
            industry = (row.get("industry") or "").strip()
            existing = grouped.get(key)
            if existing is None:
                grouped[key] = {
                    "name": raw_name,
                    "industry": industry,
                    "fund_count": fund_count,
                    "total_percentage": total_percentage,
                }
                continue
            existing["name"] = _display_name(existing["name"], raw_name, existing["fund_count"], fund_count)
            if not existing.get("industry") and industry:
                existing["industry"] = industry
            if fund_count > existing["fund_count"]:
                existing["fund_count"] = fund_count
                existing["total_percentage"] = total_percentage

    ranked = sorted(grouped.values(), key=lambda item: (-item["fund_count"], item["name"].lower()))
    selected = ranked[: settings.holdings_limit]
    return _with_holding_aliases(selected)


def _with_holding_aliases(rows: list[dict]) -> list[dict]:
    token_owners: dict[str, set[str]] = defaultdict(set)
    prepared = []
    for row in rows:
        name = short_name(row["name"]) or row["name"]
        aliases = _aliases_for(row["name"], name)
        tokens = [token for token in _TOKEN_RE.findall(canonical_key(name)) if token not in _STOP_TOKENS and len(token) >= 4]
        prepared.append({**row, "short": name, "aliases": aliases, "tokens": tokens})
        for token in tokens:
            token_owners[token].add(canonical_key(name))

    entities = []
    for row in prepared:
        negatives: list[str] = []
        own_aliases = {alias.lower() for alias in row["aliases"]}
        for other in prepared:
            if other["short"] == row["short"]:
                continue
            if not _lookalike(row, other, token_owners):
                continue
            for alias in other["aliases"]:
                if alias.lower() in own_aliases or alias in negatives:
                    continue
                negatives.append(alias)
        display = row["short"] if _is_exchange_label(row["name"]) else row["name"]
        entities.append(
            {
                "name": display,
                "type": "holding",
                "industry": row.get("industry") or "",
                "query": _holding_query(row),
                "aliases": row["aliases"],
                "negative_aliases": negatives,
                "keywords": [],
                "fund_count": row["fund_count"],
                "total_percentage": row["total_percentage"],
            }
        )
    return entities


def _aliases_for(raw_name: str, short: str) -> list[str]:
    aliases: list[str] = []
    for candidate in (raw_name, short, _two_word_alias(short)):
        if not candidate:
            continue
        cleaned = _EQ_RE.sub("", candidate).strip()
        if cleaned and cleaned not in aliases:
            aliases.append(cleaned)
    extra = EXTRA_ALIASES.get(canonical_key(short), ())
    for alias in extra:
        if alias not in aliases:
            aliases.append(alias)
    # Longer aliases first so a specific name is available alongside a short one.
    aliases.sort(key=len, reverse=True)
    return aliases


def _lookalike(row: dict, other: dict, token_owners: dict[str, set[str]]) -> bool:
    own_key = canonical_key(row["short"])
    other_key = canonical_key(other["short"])
    for token in row["tokens"]:
        owners = token_owners[token]
        if own_key in owners and other_key in owners:
            return True
    for left in row["aliases"]:
        for right in other["aliases"]:
            if contains_phrase(left, right) or contains_phrase(right, left):
                return True
    return False


def _industry_search_hint(industry: str) -> str:
    """Short phrase for Google when the company name alone is ambiguous."""
    mapped = None
    for key, spec in SECTOR_QUERIES.items():
        if key.casefold() == industry.casefold():
            mapped = spec.query
            break
    if mapped:
        return mapped.split()[0] if mapped.split() else industry
    return industry.split()[0] if industry.split() else industry


def _needs_industry_query_hint(row: dict) -> bool:
    short = row.get("short") or row["name"]
    if row.get("negative_aliases"):
        return True
    tokens = [token for token in short.split() if token]
    if len(tokens) <= 2 and len(short) < 22:
        return True
    return False


def _holding_query(row: dict) -> str:
    short = row.get("short") or row["name"]
    base = f'"{short}"'
    industry = (row.get("industry") or "").strip()
    if industry and _needs_industry_query_hint(row):
        hint = _industry_search_hint(industry)
        return f"{base} {hint} India"
    return base


def sector_query_gaps(settings: Settings, limit: int = 20) -> list[tuple[str, int]]:
    """Sectors in aggregate CSV that have no Google query mapping in SECTOR_QUERIES."""
    path = settings.path(settings.sectors_csv)
    query_keys = {name.casefold() for name in SECTOR_QUERIES}
    gaps: list[tuple[str, int]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("sector") or "").strip()
            if not name:
                continue
            lowered = name.casefold()
            if any(fragment in lowered for fragment in SECTOR_BLOCK_FRAGMENTS):
                continue
            if lowered in query_keys:
                continue
            fund_count = int(float(row.get("fund_count") or 0))
            gaps.append((name, fund_count))
    gaps.sort(key=lambda item: (-item[1], item[0].lower()))
    return gaps[:limit] if limit > 0 else gaps


def _two_word_alias(short: str) -> str:
    """Headline form such as 'SBI Life' from 'SBI Life Insurance Company'."""
    parts = [
        token
        for token in short.split()
        if token.lower() not in _STOP_TOKENS and len(token) >= 3
    ]
    if len(parts) < 2:
        return ""
    alias = f"{parts[0]} {parts[1]}"
    if alias.lower() == short.lower():
        return ""
    return alias


def load_sectors(settings: Settings) -> list[dict]:
    path = settings.path(settings.sectors_csv)
    query_by_name = {name.casefold(): (name, spec) for name, spec in SECTOR_QUERIES.items()}
    found: list[dict] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            name = (row.get("sector") or "").strip()
            if not name:
                continue
            lowered = name.casefold()
            if any(fragment in lowered for fragment in SECTOR_BLOCK_FRAGMENTS):
                continue
            mapped = query_by_name.get(lowered)
            if mapped is None:
                continue
            _label, spec = mapped
            found.append(
                {
                    "name": name,
                    "type": "sector",
                    "industry": name,
                    "query": spec.query,
                    "aliases": [],
                    "negative_aliases": [],
                    "keywords": list(spec.keywords),
                    "fund_count": int(float(row.get("fund_count") or 0)),
                    "total_percentage": float(row.get("total_percentage") or 0),
                }
            )
    found.sort(key=lambda item: (-item["fund_count"], item["name"].lower()))
    return found[: settings.sectors_limit]


def build_holding_entities(rows: list[dict]) -> list[dict]:
    """Build holding entity dicts for the pipeline from name/industry/count rows."""
    return _with_holding_aliases(rows)


def load_universe(settings: Settings) -> list[dict]:
    if (getattr(settings, "portfolio_json", None) or "").strip():
        from news_pipeline.sources.portfolio_universe import load_portfolio_universe

        entities, _manifest = load_portfolio_universe(settings)
        return entities
    return load_holdings(settings) + load_sectors(settings)
