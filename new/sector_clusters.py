"""Detect sector clusters among top fund movers (gainers / losers separately)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Literal

from lib.portfolio_scope import is_blocked_sector, sector_query_for_label
from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

from new.stock_explain import _short_name

Side = Literal["up", "down"]
Trigger = Literal["pair", "material_single"]

SECTOR_CLUSTER_MIN = 2
MATERIAL_IMPACT_PCT = 0.06
MATERIAL_RANK1_IMPACT_PCT = 0.04


def canonical_sector_key(industry: str) -> str | None:
    label = str(industry or "").strip()
    if not label or is_blocked_sector(label):
        return None
    mapped = sector_query_for_label(label)
    if mapped:
        return mapped[0]
    try:
        keys = get_sector_fund_ranking_index().resolve_sector_keys([label])
    except Exception:
        keys = []
    return keys[0] if keys else None


def _impact_abs(row: dict[str, Any]) -> float:
    try:
        return abs(float(row.get("impact_1w_pct") or 0))
    except (TypeError, ValueError):
        return 0.0


def _clusters_for_side(
    rows: list[dict[str, Any]],
    *,
    side: Side,
    min_count: int,
    material_impact_pct: float,
) -> tuple[list[SectorCluster], list[str]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    limits: list[str] = []
    for row in rows:
        industry = str(row.get("industry") or "").strip()
        key = canonical_sector_key(industry)
        if not key:
            name = str(row.get("instrument_name") or "")
            if industry:
                limits.append(f"sector_unmapped:{name or industry}")
            continue
        buckets[key].append(row)

    out: list[SectorCluster] = []
    for sector_key, bucket in buckets.items():
        bucket.sort(key=lambda r: _impact_abs(r), reverse=True)
        if len(bucket) >= min_count:
            out.append(
                SectorCluster(sector_key=sector_key, side=side, holdings=list(bucket), trigger="pair")
            )
            continue
        if len(bucket) != 1:
            continue
        holding = bucket[0]
        impact = _impact_abs(holding)
        rank = 0
        for i, r in enumerate(rows):
            if str(r.get("instrument_name") or "") == str(holding.get("instrument_name") or ""):
                rank = i
                break
        if impact >= material_impact_pct or (rank == 0 and impact >= MATERIAL_RANK1_IMPACT_PCT):
            out.append(
                SectorCluster(
                    sector_key=sector_key,
                    side=side,
                    holdings=list(bucket),
                    trigger="material_single",
                )
            )
    out.sort(key=lambda c: (-len(c.holdings), c.sector_key))
    return out, limits


@dataclass
class SectorCluster:
    sector_key: str
    side: Side
    holdings: list[dict[str, Any]] = field(default_factory=list)
    trigger: Trigger = "pair"

    def to_dict(self) -> dict[str, Any]:
        return {
            "sector_key": self.sector_key,
            "side": self.side,
            "trigger": self.trigger,
            "holding_names": [_short_name(str(h.get("instrument_name") or "")) for h in self.holdings],
            "holdings": [
                {
                    "instrument_name": h.get("instrument_name"),
                    "impact_1w_pct": h.get("impact_1w_pct"),
                    "percentage": h.get("percentage"),
                    "industry": h.get("industry"),
                }
                for h in self.holdings
            ],
        }


def detect_sector_clusters(
    gainers: list[dict[str, Any]],
    losers: list[dict[str, Any]],
    *,
    min_count: int = SECTOR_CLUSTER_MIN,
    material_impact_pct: float = MATERIAL_IMPACT_PCT,
) -> tuple[list[SectorCluster], list[str]]:
    """Return clusters and limit strings for unmapped industries."""
    limits: list[str] = []
    up, lim_up = _clusters_for_side(
        gainers, side="up", min_count=min_count, material_impact_pct=material_impact_pct
    )
    down, lim_down = _clusters_for_side(
        losers, side="down", min_count=min_count, material_impact_pct=material_impact_pct
    )
    seen: set[tuple[str, str]] = set()
    clusters: list[SectorCluster] = []
    for c in up + down:
        key = (c.sector_key, c.side)
        if key in seen:
            continue
        seen.add(key)
        clusters.append(c)
    limits.extend(lim_up)
    limits.extend(lim_down)
    return clusters, limits