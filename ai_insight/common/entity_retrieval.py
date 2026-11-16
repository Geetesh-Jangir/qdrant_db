"""Entity-scoped Qdrant reads: cluster per macro/sector, pick top articles per cluster."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Literal

from news_pipeline.config import MACRO_ENTITIES, SECTOR_QUERIES

from ai_insight.common.clustering import Cluster, cluster_rows, rank_clusters
from ai_insight.common.evidence import EvidenceArticle, enforce_prompt_budget, pick_evidence
from ai_insight.common.qdrant_access import GateConfig, fetch_entity_rows
from ai_insight.common.retrieval_plan import RELAXED_GATE, SectionRetrieval, _tag_rows
from ai_insight.common.sector_indices import IndexSeries, fetch_ohlc, load_catalog

EntityType = Literal["macro", "sector"]

MARKET_DRIVER_MACROS: tuple[str, ...] = tuple(row["name"] for row in MACRO_ENTITIES)

MARKET_DRIVER_PRIORITY: tuple[str, ...] = (
    "Macro - Nifty 50",
    "Macro - Crude Oil",
    "Macro - Rupee / USD",
    "Macro - Bank Nifty",
    "Macro - India VIX",
    "Macro - Bond Yields",
    "Macro - RBI Repo Rate",
    "Macro - FII DII Flows",
    "Macro - GDP & Economy",
    "Macro - Geopolitical Risk",
    "Macro - Tariffs & Trade",
    "Macro - Inflation (CPI)",
)


@dataclass
class EntityPack:
    entity_name: str
    entity_type: EntityType
    clusters: list[Cluster] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


def slug(name: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", name.casefold().strip())
    return text.strip("_")[:48] or "entity"


SECTOR_INDEX_GATE = GateConfig(min_relevance=2, min_impact=1, min_about=0.45)


def fetch_entity_pack(
    ctx,
    entity_name: str,
    entity_type: EntityType,
    window: tuple[str, str],
    *,
    top_clusters: int = 2,
    client: Any = None,
    gate: GateConfig | None = None,
) -> EntityPack:
    gate = gate or RELAXED_GATE
    names = [entity_name] if entity_type == "macro" else [entity_name]
    result = fetch_entity_rows(entity_type, window, names, gate=gate, client=client, log=ctx.log)
    clusters = rank_clusters(cluster_rows(result.rows, top_clusters=max(top_clusters * 3, 4)))[:top_clusters]
    prefix = slug(entity_name)
    for cluster in clusters:
        cluster.cluster_id = f"{prefix}#{cluster.cluster_id}"
    return EntityPack(
        entity_name=entity_name,
        entity_type=entity_type,
        clusters=clusters,
        rows=result.rows,
        diagnostics={
            "passed": result.diagnostics.entities_passed,
            "scanned": result.diagnostics.articles_scanned,
        },
    )


def fetch_macro_packs(
    ctx,
    window: tuple[str, str],
    macro_names: list[str],
    *,
    top_clusters: int = 2,
    client: Any = None,
    max_workers: int = 6,
) -> list[EntityPack]:
    packs: list[EntityPack] = []
    names = [item for item in macro_names if item]
    workers = min(max_workers, max(1, len(names)))

    def work(name: str) -> EntityPack:
        return fetch_entity_pack(ctx, name, "macro", window, top_clusters=top_clusters, client=client)

    if workers <= 1:
        for name in names:
            packs.append(work(name))
        return packs
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, name): name for name in names}
        for future in as_completed(futures):
            packs.append(future.result())
    packs.sort(key=lambda item: item.entity_name)
    return packs


def fetch_sector_pack(
    ctx,
    sector_name: str,
    window: tuple[str, str],
    today: tuple[str, str],
    *,
    top_clusters: int = 8,
    client: Any = None,
    gate: GateConfig | None = None,
) -> EntityPack:
    pack = fetch_entity_pack(ctx, sector_name, "sector", window, top_clusters=top_clusters, client=client, gate=gate)
    pack.rows = _tag_rows(pack.rows, window, today)
    return pack


def evidence_from_clusters(
    clusters: list[Cluster],
    *,
    per_cluster: int = 4,
    default_entity: str = "",
) -> list[EvidenceArticle]:
    return pick_evidence(clusters, per_cluster=per_cluster)


def merge_evidence(*groups: list[EvidenceArticle]) -> list[EvidenceArticle]:
    seen: set[str] = set()
    merged: list[EvidenceArticle] = []
    for group in groups:
        for item in group:
            key = item.url or item.title
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def packs_to_section(
    ctx,
    packs: list[EntityPack],
    window: tuple[str, str],
    today: tuple[str, str],
    *,
    per_cluster: int = 4,
    max_clusters: int = 24,
) -> SectionRetrieval:
    clusters: list[Cluster] = []
    rows: list[dict[str, Any]] = []
    diag: dict[str, Any] = {"entities": {}}
    for pack in packs:
        clusters.extend(pack.clusters)
        rows.extend(pack.rows)
        diag["entities"][pack.entity_name] = pack.diagnostics
    clusters = rank_clusters(clusters)[:max_clusters]
    evidence = evidence_from_clusters(clusters, per_cluster=per_cluster)
    evidence, dropped = enforce_prompt_budget(evidence, ctx.config.max_prompt_chars)
    diag["dropped_for_budget"] = len(dropped)
    diag["packs"] = len(packs)
    return SectionRetrieval(rows, clusters, evidence, window, today, diag)


def week_index_movers(ctx) -> tuple[IndexSeries | None, IndexSeries | None]:
    """Best week performer and worst among negative week moves."""
    specs = load_catalog(include_weak=ctx.config.include_weak_index)
    serieses: list[IndexSeries] = []
    for spec in specs:
        series = fetch_ohlc(spec, ctx.trading_date)
        if series is not None and series.week_change_pct is not None:
            serieses.append(series)
    if not serieses:
        return None, None
    best = max(serieses, key=lambda item: item.week_change_pct or -1e9)
    negatives = [item for item in serieses if (item.week_change_pct or 0) < 0]
    worst = min(negatives, key=lambda item: item.week_change_pct or 0) if negatives else None
    return best, worst


def sector_names_for_pulse(ctx) -> tuple[list[str], list[str], dict[str, Any]]:
    best, worst = week_index_movers(ctx)
    meta: dict[str, Any] = {"best_index": None, "worst_index": None}
    best_names: list[str] = []
    worst_names: list[str] = []
    if best is not None:
        meta["best_index"] = {
            "display": best.spec.display,
            "week_change_pct": best.week_change_pct,
            "sectors": best.spec.news_sectors,
        }
        best_names = list(best.spec.news_sectors)
    if worst is not None:
        meta["worst_index"] = {
            "display": worst.spec.display,
            "week_change_pct": worst.week_change_pct,
            "sectors": worst.spec.news_sectors,
        }
        worst_names = list(worst.spec.news_sectors)
    return best_names, worst_names, meta


def fetch_market_driver(ctx, client: Any | None = None) -> SectionRetrieval:
    from ai_insight.common.retrieval_plan import plan_window

    week, today = plan_window(ctx, "market_driver_digest")
    packs = fetch_macro_packs(ctx, week, list(MARKET_DRIVER_MACROS), top_clusters=2, client=client)
    return packs_to_section(ctx, packs, week, today, per_cluster=4, max_clusters=ctx.config.max_clusters)


def fetch_fii_dii(ctx, client: Any | None = None) -> SectionRetrieval:
    from ai_insight.common.retrieval_plan import plan_window

    week, today = plan_window(ctx, "fii_dii_flow_narrative")
    flow_pack = fetch_entity_pack(ctx, "Macro - FII DII Flows", "macro", week, top_clusters=2, client=client)
    best_names, worst_names, _pulse_meta = sector_names_for_pulse(ctx)
    pulse_names = list(dict.fromkeys([*best_names, *worst_names]))
    sector_packs = [
        fetch_entity_pack(ctx, name, "sector", week, top_clusters=2, client=client)
        for name in pulse_names[:4]
    ]
    macro_extra = fetch_macro_packs(ctx, week, list(MARKET_DRIVER_PRIORITY[:6]), top_clusters=1, client=client)
    packs = [flow_pack, *sector_packs, *macro_extra]
    return packs_to_section(ctx, packs, week, today, per_cluster=4, max_clusters=20)


def fetch_sector_pulse_sectors(
    ctx,
    sector_names: list[str],
    *,
    client: Any | None = None,
    top_clusters: int = 6,
) -> SectionRetrieval:
    from ai_insight.common.retrieval_plan import plan_window

    week, today = plan_window(ctx, "sector_leaderboard")
    packs = [
        fetch_sector_pack(ctx, name, week, today, top_clusters=top_clusters, client=client)
        for name in sector_names
        if name in SECTOR_QUERIES
    ]
    return packs_to_section(ctx, packs, week, today, per_cluster=4, max_clusters=12)


def fetch_sector_index(ctx, sector_names: list[str], client: Any | None = None) -> SectionRetrieval:
    from ai_insight.common.retrieval_plan import plan_window

    week, today = plan_window(ctx, "sector_index_insights")
    packs: list[EntityPack] = []
    for name in sector_names:
        if name not in SECTOR_QUERIES:
            ctx.log.line("INDEX_NEWS", f"skip unknown sector key {name!r}")
            continue
        pack = fetch_sector_pack(ctx, name, week, today, top_clusters=12, client=client, gate=SECTOR_INDEX_GATE)
        if not pack.rows:
            pack = fetch_sector_pack(ctx, name, week, today, top_clusters=12, client=client, gate=RELAXED_GATE)
        ctx.log.line(
            "INDEX_NEWS",
            f"sector={name} passed={pack.diagnostics.get('passed', 0)} clusters={len(pack.clusters)}",
        )
        packs.append(pack)
    return packs_to_section(ctx, packs, week, today, per_cluster=3, max_clusters=24)


__all__ = [
    "EntityPack",
    "MARKET_DRIVER_MACROS",
    "MARKET_DRIVER_PRIORITY",
    "evidence_from_clusters",
    "fetch_fii_dii",
    "fetch_market_driver",
    "fetch_macro_packs",
    "fetch_sector_index",
    "fetch_sector_pulse_sectors",
    "merge_evidence",
    "sector_names_for_pulse",
    "week_index_movers",
]