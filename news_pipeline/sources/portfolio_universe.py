"""Search universe from a portfolio file (holdings >= 2%%, sectors >= 3%%)."""

from __future__ import annotations

from pathlib import Path

from lib.portfolio_scope import (
    build_portfolio_scope,
    resolve_allisin_holdings_path,
    sector_query_for_label,
    write_manifest,
)
from news_pipeline.config import Settings, repo_root
from news_pipeline.sources.universe import build_holding_entities, canonical_key


def load_portfolio_universe(settings: Settings) -> tuple[list[dict], Path | None]:
    portfolio_raw = (getattr(settings, "portfolio_json", None) or "").strip()
    if not portfolio_raw:
        raise RuntimeError("portfolio_json not configured")

    portfolio_path = Path(portfolio_raw)
    if not portfolio_path.is_absolute():
        portfolio_path = settings.path(portfolio_raw)

    configured_allisin = settings.path(settings.allisin_sectors_holdings_json)
    if configured_allisin.is_file():
        allisin_path = configured_allisin
    else:
        allisin_path = resolve_allisin_holdings_path(
            repo_root(),
            full_relative=settings.allisin_sectors_holdings_json,
            subset_relative=settings.portfolio_allisin_holdings_json,
        )

    manifest_raw = getattr(settings, "portfolio_manifest_path", "") or (
        "data/fund_holdings_aggregate/portfolio_news_scope.json"
    )
    manifest_path = settings.path(manifest_raw)

    scope = build_portfolio_scope(
        portfolio_path=portfolio_path,
        allisin_path=allisin_path,
        holding_min=float(getattr(settings, "portfolio_holding_min_pct", 2.0)),
        sector_min=float(getattr(settings, "portfolio_sector_min_pct", 3.0)),
        aggregated_holdings_map_path=settings.path(settings.aggregated_holdings_map),
        aggregated_holdings_csv_path=settings.path(settings.aggregated_holdings_csv),
        require_aggregated_equity=True,
    )
    write_manifest(manifest_path, scope)

    holding_rows: dict[str, dict] = {}
    for h in scope.holdings:
        key = canonical_key(h.instrument_name)
        if not key:
            continue
        fund_count = len(h.by_fund)
        existing = holding_rows.get(key)
        if existing is None:
            holding_rows[key] = {
                "name": h.instrument_name,
                "industry": h.industry,
                "fund_count": fund_count,
                "total_percentage": h.percentage,
            }
            continue
        if h.percentage > existing["total_percentage"]:
            existing["total_percentage"] = h.percentage
        if fund_count > existing["fund_count"]:
            existing["fund_count"] = fund_count

    holding_entities = build_holding_entities(list(holding_rows.values()))

    sector_entities: list[dict] = []
    seen_sector: set[str] = set()
    for s in scope.sectors:
        if s.canonical_name.casefold() in seen_sector:
            continue
        seen_sector.add(s.canonical_name.casefold())
        mapped = sector_query_for_label(s.canonical_name)
        if mapped is None:
            continue
        canonical, spec = mapped
        sector_entities.append(
            {
                "name": canonical,
                "type": "sector",
                "industry": canonical,
                "query": spec.query,
                "aliases": [],
                "negative_aliases": [],
                "keywords": list(spec.keywords),
                "fund_count": len(s.by_fund),
                "total_percentage": s.percentage,
            }
        )

    sector_entities.sort(key=lambda item: (-item["fund_count"], item["name"].lower()))
    return holding_entities + sector_entities, manifest_path
