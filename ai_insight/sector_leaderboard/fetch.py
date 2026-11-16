"""One gated read of every pipeline sector, then one cluster per distinct story."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from ai_insight.common.clustering import Cluster, cluster_rows
from ai_insight.common.entity_retrieval import fetch_sector_news_pack
from ai_insight.common.qdrant_access import GateConfig, GateDiagnostics, fetch_entity_rows
from ai_insight.common.time_ist import ist_now, session_window

SECTOR_NEWS_GATE = GateConfig(min_relevance=2, min_impact=1, min_about=0.45)

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
    gate: GateConfig | None = None,
) -> SectorFetch:
    """Gated sector read; cluster ids are namespaced so sectors cannot collide."""
    from news_pipeline.config import SECTOR_QUERIES

    names = [item for item in (only_sectors or list(SECTOR_QUERIES.keys())) if item in SECTOR_QUERIES]
    result = fetch_entity_rows("sector", window, names or None, gate=gate or SECTOR_NEWS_GATE, client=client, log=log)
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


def fetch_targeted_sector_stories(
    ctx,
    window: tuple[str, str],
    sector_names: list[str],
    *,
    client: Any = None,
) -> SectorFetch:
    """Week pulse: sector news plus bellwether holdings when sector entity scores are weak."""
    from news_pipeline.config import SECTOR_QUERIES

    sector_index = {name: index for index, name in enumerate(SECTOR_QUERIES)}
    today = session_window(ctx.trading_date, now=ist_now() if ctx.live else None, config=ctx.config)
    sectors: list[SectorStories] = []
    scanned = 0
    passed = 0
    for name in sector_names:
        if name not in SECTOR_QUERIES:
            continue
        pack = fetch_sector_news_pack(ctx, name, window, today, top_clusters=24, client=client)
        scanned += int(pack.diagnostics.get("scanned") or 0)
        passed += len(pack.rows)
        if ctx.log is not None:
            ctx.log.line(
                "PULSE_NEWS",
                f"sector={name} rows={len(pack.rows)} clusters={len(pack.clusters)} "
                f"holdings={pack.diagnostics.get('holdings_passed', 0)}",
            )
        if not pack.rows:
            continue
        index = sector_index.get(name, len(sectors))
        clusters = cluster_rows(pack.rows, cluster_by="title", top_clusters=_TOP_CLUSTERS)
        for cluster in clusters:
            cluster.cluster_id = f"s{index:02d}_{cluster.cluster_id}"
        sectors.append(SectorStories(name=name, index=index, clusters=clusters))
    diagnostics = GateDiagnostics()
    diagnostics.articles_scanned = scanned
    diagnostics.entities_passed = passed
    return SectorFetch(sectors=sectors, diagnostics=diagnostics)
