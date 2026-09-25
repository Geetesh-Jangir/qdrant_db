"""Portfolio fund scope: holdings >= 2%%, sectors >= 3%% (shared by pipeline and RAG)."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from news_pipeline.config import SECTOR_BLOCK_FRAGMENTS, SECTOR_QUERIES
from news_pipeline.sources.universe import canonical_key

HOLDING_MIN_PCT = 2.0
SECTOR_MIN_PCT = 3.0

_SECTOR_AND_RE = re.compile(r"\s+And\s+", re.IGNORECASE)


def normalize_sector_label(name: str) -> str:
    text = (name or "").strip()
    text = _SECTOR_AND_RE.sub(" & ", text)
    return " ".join(text.split())


def sector_query_for_label(raw_sector: str) -> tuple[str, Any] | None:
    """Return (canonical SECTOR_QUERIES key, SectorQuery) or None."""
    normalized = normalize_sector_label(raw_sector)
    by_fold = {k.casefold(): k for k in SECTOR_QUERIES}
    key = by_fold.get(normalized.casefold())
    if key is None:
        return None
    return key, SECTOR_QUERIES[key]


def is_blocked_sector(name: str) -> bool:
    lowered = name.casefold()
    return any(fragment in lowered for fragment in SECTOR_BLOCK_FRAGMENTS)


@dataclass
class FundRef:
    isin: str
    fund_short_name: str
    current_value: float


@dataclass
class ScopedHolding:
    instrument_name: str
    industry: str
    percentage: float
    by_fund: dict[str, float] = field(default_factory=dict)


@dataclass
class ScopedSector:
    sector_label: str
    canonical_name: str
    percentage: float
    by_fund: dict[str, float] = field(default_factory=dict)


@dataclass
class PortfolioScope:
    funds: list[FundRef]
    holdings: list[ScopedHolding]
    sectors: list[ScopedSector]
    skipped_sectors: list[str]
    skipped_holdings_non_equity: list[str]
    skipped_holdings_not_in_aggregate: list[str]
    entity_names_for_news: list[str]

    def holdings_for_isin(self, isin: str) -> list[ScopedHolding]:
        return [h for h in self.holdings if isin in h.by_fund]

    def sectors_for_isin(self, isin: str) -> list[ScopedSector]:
        return [s for s in self.sectors if isin in s.by_fund]


def load_portfolio_funds(portfolio_path: Path) -> list[FundRef]:
    doc = json.loads(portfolio_path.read_text(encoding="utf-8"))
    data = doc.get("data") or {}
    holdings = data.get("holdings") or []
    funds: list[FundRef] = []
    for row in holdings:
        isin = str(row.get("isin") or "").strip()
        if not isin:
            continue
        try:
            value = float(row.get("current_value") or 0)
        except (TypeError, ValueError):
            value = 0.0
        funds.append(
            FundRef(
                isin=isin,
                fund_short_name=str(row.get("fund_short_name") or row.get("fund_name") or isin).strip(),
                current_value=value,
            )
        )
    if not funds:
        raise ValueError(f"No funds in portfolio file: {portfolio_path}")
    return funds


def load_allisin_doc(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_allisin_holdings_path(
    repo_root: Path,
    *,
    full_relative: str,
    subset_relative: str,
) -> Path:
    """Prefer full ISIN map when present; otherwise portfolio subset (CI / lightweight)."""
    full = repo_root / full_relative
    subset = repo_root / subset_relative
    if full.is_file():
        return full
    if subset.is_file():
        return subset
    raise FileNotFoundError(
        f"Holdings file missing. Expected {full} or {subset}. "
        "Run: python scripts/build_portfolio_allisin_subset.py"
    )


def load_aggregated_equity_keys(
    *,
    map_path: Path,
    csv_path: Path | None = None,
) -> set[str]:
    """Canonical keys for instruments in aggregated holdings (equity-only aggregate)."""
    keys: set[str] = set()
    if map_path.is_file():
        doc = json.loads(map_path.read_text(encoding="utf-8"))
        if isinstance(doc, dict):
            for name in doc:
                key = canonical_key(str(name))
                if key:
                    keys.add(key)
    if keys:
        return keys
    if csv_path and csv_path.is_file():
        with csv_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                name = (row.get("instrument_name") or "").strip()
                key = canonical_key(name)
                if key:
                    keys.add(key)
    if not keys:
        raise FileNotFoundError(
            f"No aggregated equity holdings found at {map_path}"
            + (f" or {csv_path}" if csv_path else "")
        )
    return keys


def _holding_equity_allowed(info: dict, instrument: str, equity_aggregate_keys: set[str] | None) -> str | None:
    """Return skip reason, or None if the holding may be included."""
    rating = str(info.get("rating") or "").strip().casefold()
    if rating and rating != "equity":
        return "non_equity"
    if equity_aggregate_keys is not None:
        key = canonical_key(instrument)
        if key not in equity_aggregate_keys:
            return "not_in_aggregate"
    elif rating != "equity":
        return "non_equity"
    return None


def build_portfolio_scope(
    *,
    portfolio_path: Path,
    allisin_path: Path,
    holding_min: float = HOLDING_MIN_PCT,
    sector_min: float = SECTOR_MIN_PCT,
    aggregated_holdings_map_path: Path | None = None,
    aggregated_holdings_csv_path: Path | None = None,
    require_aggregated_equity: bool = True,
) -> PortfolioScope:
    funds = load_portfolio_funds(portfolio_path)
    allisin = load_allisin_doc(allisin_path)

    holding_map: dict[str, ScopedHolding] = {}
    sector_map: dict[str, ScopedSector] = {}
    skipped_sectors: set[str] = set()
    skipped_non_equity: list[str] = []
    skipped_not_in_aggregate: list[str] = []

    equity_aggregate_keys: set[str] | None = None
    if require_aggregated_equity and aggregated_holdings_map_path is not None:
        equity_aggregate_keys = load_aggregated_equity_keys(
            map_path=aggregated_holdings_map_path,
            csv_path=aggregated_holdings_csv_path,
        )

    for fund in funds:
        entry = allisin.get(fund.isin)
        if not isinstance(entry, dict):
            raise ValueError(f"ISIN not found in holdings file: {fund.isin}")
        if entry.get("error"):
            raise ValueError(f"Holdings error for {fund.isin}: {entry.get('error')}")

        raw_holdings = entry.get("holdings") or {}
        if isinstance(raw_holdings, dict):
            for name, info in raw_holdings.items():
                if not isinstance(info, dict):
                    continue
                try:
                    pct = float(info.get("percentage") or 0)
                except (TypeError, ValueError):
                    continue
                if pct < holding_min:
                    continue
                instrument = str(name).strip()
                skip_reason = _holding_equity_allowed(info, instrument, equity_aggregate_keys)
                if skip_reason == "non_equity":
                    skipped_non_equity.append(f"{instrument} ({fund.isin})")
                    continue
                if skip_reason == "not_in_aggregate":
                    skipped_not_in_aggregate.append(f"{instrument} ({fund.isin})")
                    continue
                industry = str(info.get("industry") or "").strip()
                key = instrument.casefold()
                row = holding_map.get(key)
                if row is None:
                    row = ScopedHolding(
                        instrument_name=instrument,
                        industry=industry,
                        percentage=pct,
                        by_fund={fund.isin: pct},
                    )
                    holding_map[key] = row
                else:
                    row.by_fund[fund.isin] = pct
                    if pct > row.percentage:
                        row.percentage = pct

        raw_sectors = entry.get("sectors") or {}
        if isinstance(raw_sectors, dict):
            for sector_name, weight in raw_sectors.items():
                label = str(sector_name).strip()
                if not label or is_blocked_sector(label):
                    continue
                try:
                    pct = float(weight)
                except (TypeError, ValueError):
                    continue
                if pct < sector_min:
                    continue
                mapped = sector_query_for_label(label)
                if mapped is None:
                    skipped_sectors.add(label)
                    continue
                canonical, _spec = mapped
                key = canonical.casefold()
                row = sector_map.get(key)
                if row is None:
                    row = ScopedSector(
                        sector_label=label,
                        canonical_name=canonical,
                        percentage=pct,
                        by_fund={fund.isin: pct},
                    )
                    sector_map[key] = row
                else:
                    row.by_fund[fund.isin] = pct
                    if pct > row.percentage:
                        row.percentage = pct

    holdings = sorted(holding_map.values(), key=lambda h: (-h.percentage, h.instrument_name.lower()))
    sectors = sorted(sector_map.values(), key=lambda s: (-s.percentage, s.canonical_name.lower()))

    entity_names: set[str] = set()
    for h in holdings:
        entity_names.add(h.instrument_name)
    for s in sectors:
        entity_names.add(s.canonical_name)

    return PortfolioScope(
        funds=funds,
        holdings=holdings,
        sectors=sectors,
        skipped_sectors=sorted(skipped_sectors),
        skipped_holdings_non_equity=sorted(set(skipped_non_equity)),
        skipped_holdings_not_in_aggregate=sorted(set(skipped_not_in_aggregate)),
        entity_names_for_news=sorted(entity_names),
    )


def scope_to_manifest(scope: PortfolioScope) -> dict[str, Any]:
    total_value = sum(f.current_value for f in scope.funds) or 1.0
    return {
        "holding_min_pct": HOLDING_MIN_PCT,
        "sector_min_pct": SECTOR_MIN_PCT,
        "funds": [
            {
                "isin": f.isin,
                "fund_short_name": f.fund_short_name,
                "current_value": f.current_value,
                "portfolio_weight_pct": round(100.0 * f.current_value / total_value, 4),
            }
            for f in scope.funds
        ],
        "holdings": [
            {
                "instrument_name": h.instrument_name,
                "industry": h.industry,
                "max_pct_in_any_fund": h.percentage,
                "by_fund_pct": h.by_fund,
            }
            for h in scope.holdings
        ],
        "sectors": [
            {
                "sector_label": s.sector_label,
                "canonical_name": s.canonical_name,
                "max_pct_in_any_fund": s.percentage,
                "by_fund_pct": s.by_fund,
            }
            for s in scope.sectors
        ],
        "skipped_sectors_no_query": scope.skipped_sectors,
        "skipped_holdings_non_equity": scope.skipped_holdings_non_equity,
        "skipped_holdings_not_in_aggregate": scope.skipped_holdings_not_in_aggregate,
        "entity_names_searched": scope.entity_names_for_news,
    }


def write_manifest(path: Path, scope: PortfolioScope) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scope_to_manifest(scope), ensure_ascii=False, indent=2), encoding="utf-8")


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def instrument_to_qdrant_names(scope: PortfolioScope) -> dict[str, str]:
    """Map fund-file instrument names to pipeline entity display names."""
    from news_pipeline.sources.universe import build_holding_entities, canonical_key

    rows = [
        {
            "name": h.instrument_name,
            "industry": h.industry,
            "fund_count": len(h.by_fund),
            "total_percentage": h.percentage,
        }
        for h in scope.holdings
    ]
    entities = build_holding_entities(rows)
    by_key: dict[str, str] = {}
    for entity in entities:
        for alias in entity.get("aliases") or []:
            by_key[canonical_key(alias)] = entity["name"]
        by_key[canonical_key(entity["name"])] = entity["name"]
    out: dict[str, str] = {}
    for h in scope.holdings:
        key = canonical_key(h.instrument_name)
        out[h.instrument_name] = by_key.get(key, h.instrument_name)
    return out


def qdrant_filter_names(scope: PortfolioScope) -> list[str]:
    """Entity labels as stored on Qdrant points (holdings + sectors)."""
    names = set(instrument_to_qdrant_names(scope).values())
    for s in scope.sectors:
        names.add(s.canonical_name)
    return sorted(names)
