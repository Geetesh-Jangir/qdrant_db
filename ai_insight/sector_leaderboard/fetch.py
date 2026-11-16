"""One gated read of every pipeline sector, then one cluster per distinct story."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ai_insight.common.clustering import Cluster, cluster_rows
from ai_insight.common.qdrant_access import GateDiagnostics, fetch_entity_rows

_TOP_CLUSTERS = 1000


@dataclass
class SectorStories:
    name: str
    index: int
    clusters: list[Cluster] = field(default_factory=list)


@dataclass
class SectorFetch:
    sectors: list[SectorStories]
    diagnostics: GateDiagnostics


def fetch_sector_stories(
    window: tuple[str, str],
    *,
    client: Any = None,
    log: Any = None,
    only_sectors: list[str] | None = None,
) -> SectorFetch:
    """Gated sector read; cluster ids are namespaced so sectors cannot collide."""
    from news_pipeline.config import SECTOR_QUERIES

    names = [item for item in (only_sectors or list(SECTOR_QUERIES.keys())) if item in SECTOR_QUERIES]
    result = fetch_entity_rows("sector", window, names or None, client=client, log=log)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in result.rows:
        grouped[str(row["entity"]["name"])].append(row)
    sectors: list[SectorStories] = []
    for index, name in enumerate(SECTOR_QUERIES):
        if only_sectors is not None and name not in only_sectors:
            continue
        rows = grouped.get(name) or []
        if not rows:
            continue
        clusters = cluster_rows(rows, cluster_by="title", top_clusters=_TOP_CLUSTERS)
        for cluster in clusters:
            cluster.cluster_id = f"s{index:02d}_{cluster.cluster_id}"
        sectors.append(SectorStories(name=name, index=index, clusters=clusters))
    return SectorFetch(sectors=sectors, diagnostics=result.diagnostics)
