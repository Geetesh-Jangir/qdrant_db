"""Cluster ranking for the market digest. Index recaps explain the move only as a last resort."""

from __future__ import annotations

from dataclasses import dataclass

from ai_insight.common.clustering import Cluster, cluster_score, rank_clusters
from ai_insight.market_driver_digest.schema import INDEX_ENTITIES


@dataclass
class Drivers:
    primary: Cluster | None
    secondary: Cluster | None
    ranked: list[Cluster]
    used_recap_only: bool


def move_size(change_pct: float | None, *, small: float = 0.25, large: float = 1.0) -> str:
    if change_pct is None:
        return "unknown"
    magnitude = abs(change_pct)
    if magnitude < small:
        return "small"
    if magnitude <= large:
        return "moderate"
    return "large"


def move_phrase(change_pct: float | None) -> str:
    size = move_size(change_pct)
    if change_pct is None:
        return "moved"
    if size == "small":
        return "stayed range-bound"
    up = change_pct > 0
    if size == "moderate":
        return "edged up" if up else "edged down"
    return "rallied" if up else "fell sharply"


def is_index_recap(cluster: Cluster) -> bool:
    names = {str((row.get("entity") or {}).get("name") or "") for row in cluster.articles}
    names.discard("")
    return bool(names) and names <= INDEX_ENTITIES


def split_index_recaps(clusters: list[Cluster]) -> tuple[list[Cluster], list[Cluster]]:
    recaps = [cluster for cluster in clusters if is_index_recap(cluster)]
    rest = [cluster for cluster in clusters if not is_index_recap(cluster)]
    return rest, recaps


def pick_drivers(clusters: list[Cluster]) -> Drivers:
    rest, recaps = split_index_recaps(clusters)
    pool = rank_clusters(rest or recaps)
    primary = pool[0] if pool else None
    secondary = None
    if primary is not None:
        primary_names = _names(primary)
        for cluster in pool[1:]:
            if _names(cluster).isdisjoint(primary_names):
                secondary = cluster
                break
    return Drivers(primary, secondary, pool, used_recap_only=not rest and bool(recaps))


def _names(cluster: Cluster) -> set[str]:
    return {str((row.get("entity") or {}).get("name") or "") for row in cluster.articles} - {""}


def score(cluster: Cluster) -> float:
    return cluster_score(cluster)
