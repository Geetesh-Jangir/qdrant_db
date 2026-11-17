"""Curated top holdings: stock name, Google multi-query, and sector from spreadsheet."""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pandas as pd

from news_pipeline.config import Settings
from news_pipeline.sources.universe import canonical_key, short_name

_LEGAL_SUFFIX = re.compile(
    r"\s+(limited|ltd\.?|inc\.?|corp\.?|corporation|plc)\.?\s*$",
    re.IGNORECASE,
)
_COMPANY_BEFORE_LEGAL = re.compile(
    r"\s+Company\s+(Limited|Ltd\.?)\s*$",
    re.IGNORECASE,
)

MAX_STOCK_UNIVERSE = 500


def _strip_legal_suffix(name: str) -> str:
    prev = None
    text = name.strip()
    while text and text != prev:
        prev = text
        text = _LEGAL_SUFFIX.sub("", text).strip(" .,-")
    return text


def multi_query_for(name: str) -> str:
    """Heuristic OR-query for regenerating rows (curated sheet values are not overwritten)."""
    stripped = name.strip()
    if canonical_key(stripped) == canonical_key("Life Insurance Corporation Of India"):
        return f'"{stripped}"'

    company_m = _COMPANY_BEFORE_LEGAL.search(stripped)
    if company_m:
        alias = _COMPANY_BEFORE_LEGAL.sub(f" {company_m.group(1)}", stripped)
        alias = _strip_legal_suffix(alias)
        if alias and alias.casefold() != stripped.casefold():
            return f'"{stripped}" OR "{alias}"'

    alias = _strip_legal_suffix(stripped)
    if alias and alias.casefold() != stripped.casefold():
        if stripped.lower().startswith("the ") and not alias.lower().startswith("the "):
            alias = f"The {alias}"
        return f'"{stripped}" OR "{alias}"'

    short = short_name(stripped)
    if short and short.casefold() != stripped.casefold():
        return f'"{stripped}" OR "{short}"'
    return f'"{stripped}"'


def _fund_stats_from_csv(settings: Settings) -> dict[str, dict]:
    path = settings.path(settings.aggregated_holdings_csv)
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
            existing = grouped.get(key)
            if existing is None or fund_count > existing["fund_count"]:
                grouped[key] = {
                    "fund_count": fund_count,
                    "total_percentage": total_percentage,
                }
    return grouped


def load_holdings_rows_from_xlsx(settings: Settings) -> list[dict]:
    rel = (getattr(settings, "stock_multi_query_sector_xlsx", None) or "").strip()
    if not rel:
        return []
    path = settings.path(rel)
    if not path.is_file():
        return []

    frame = pd.read_excel(path)
    expected = ("Stock Name", "Multi-Query", "Sector")
    if tuple(frame.columns) != expected:
        raise RuntimeError(
            f"{path} must have columns {expected}, got {tuple(frame.columns)}"
        )

    limit = min(int(settings.holdings_limit), MAX_STOCK_UNIVERSE, len(frame))
    stats = _fund_stats_from_csv(settings)
    rows: list[dict] = []
    for _, record in frame.iloc[:limit].iterrows():
        name = str(record["Stock Name"]).strip()
        if not name:
            continue
        key = canonical_key(name)
        stat = stats.get(key, {})
        rows.append(
            {
                "name": name,
                "industry": str(record["Sector"]).strip(),
                "query": str(record["Multi-Query"]).strip(),
                "fund_count": int(stat.get("fund_count") or 0),
                "total_percentage": float(stat.get("total_percentage") or 0),
            }
        )
    return rows