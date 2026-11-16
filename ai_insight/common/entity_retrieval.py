"""Entity-scoped Qdrant reads: cluster per macro/sector, pick top articles per cluster."""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal

from news_pipeline.config import MACRO_ENTITIES, SECTOR_BELLWETHERS, SECTOR_QUERIES

from ai_insight.common.clustering import Cluster, cluster_rows, rank_clusters
from ai_insight.common.evidence import EvidenceArticle, enforce_prompt_budget, pick_evidence
from ai_insight.common.qdrant_access import GateConfig, fetch_entity_rows
from ai_insight.common.retrieval_plan import RELAXED_GATE, SectionRetrieval, _tag_rows
from ai_insight.common.sector_indices import IndexSeries, fetch_ohlc, load_catalog, news_sectors_for_index

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
SECTOR_RELAXED_GATE = GateConfig(min_relevance=2, min_impact=1, min_about=0.35)
HOLDING_READTHROUGH_GATE = GateConfig(min_relevance=2, min_impact=1, min_about=0.4)
_BELLWETHER_HOLDINGS_LIMIT = 5
_MIN_SECTOR_ROWS_BEFORE_HOLDINGS = 3


@lru_cache(maxsize=1)
def _qdrant_holding_names() -> frozenset[str]:
    """All instrument names in the holdings aggregate (not the pipeline holdings_limit subset)."""
    import csv

    from news_pipeline.config import Settings

    path = Settings().path(Settings().holdings_csv)
    names: set[str] = set()
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            raw = str(row.get("instrument_name") or "").strip()
            if raw:
                names.add(raw)
    return frozenset(names)


# Qdrant entity_names are case-sensitive; these match live corpus tags.
_SECTOR_QDRANT_HOLDINGS: dict[str, tuple[str, ...]] = {
    "It - Software": (
        "Tata Consultancy Services Limited",
        "Infosys Limited",
        "Wipro Ltd.",
        "Tech Mahindra Limited",
    ),
}

_BELLWETHER_SEARCH: dict[str, str] = {
    "tcs": "tata consultancy services",
    "infosys": "infosys",
    "hcl tech": "hcl technologies",
    "wipro": "wipro",
    "tech mahindra": "tech mahindra",
}


def _resolve_bellwether(label: str, corpus: set[str]) -> str | None:
    from lib.portfolio_scope import match_holding_to_corpus_entity
    from news_pipeline.sources.universe import canonical_key

    hit = match_holding_to_corpus_entity(label, corpus)
    if hit in corpus:
        lowered = hit.lower()
        if not any(bad in lowered for bad in ("future", "covered call", "eq -")):
            return hit
    needle = _BELLWETHER_SEARCH.get(label.casefold(), canonical_key(label))
    if not needle:
        return None

    def rank(name: str) -> tuple[int, int, int, str]:
        lowered = name.lower()
        if any(bad in lowered for bad in ("future", "covered call", " #", "eq -", " ~~")):
            return (3, 0, len(name), name)
        if re.search(r"\d", name):
            return (2, 0, len(name), name)
        if name.isupper() and len(name) > 12:
            return (2, 0, len(name), name)
        if lowered.startswith("eq "):
            return (2, 0, len(name), name)
        key = canonical_key(name)
        if needle in key or all(token in key for token in needle.split() if len(token) > 2):
            titleish = 1 if re.match(r"^[A-Z][a-z].*(Limited|Ltd\.?)$", name) else 0
            return (0, titleish, -len(name), name)
        return (1, 0, len(name), name)

    ordered = sorted(corpus, key=rank)
    if ordered and rank(ordered[0])[0] == 0:
        return ordered[0]
    return None


def bellwether_holdings(sector_name: str, *, limit: int = _BELLWETHER_HOLDINGS_LIMIT) -> list[str]:
    corpus = set(_qdrant_holding_names())
    fixed = _SECTOR_QDRANT_HOLDINGS.get(sector_name)
    if fixed:
        return [name for name in fixed if name in corpus][:limit]
    raw = str(SECTOR_BELLWETHERS.get(sector_name) or "").strip()
    if not raw:
        return []
    resolved: list[str] = []
    for part in raw.split(","):
        label = part.strip()
        if not label:
            continue
        name = _resolve_bellwether(label, corpus)
        if name and name not in resolved:
            resolved.append(name)
        if len(resolved) >= limit:
            break
    return resolved


def _sectorize_holding_rows(rows: list[dict[str, Any]], sector_name: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        entity = dict(item.get("entity") or {})
        entity["bellwether"] = str(entity.get("name") or "")
        entity["name"] = sector_name
        item["entity"] = entity
        out.append(item)
    return out


def _merge_pack_clusters(pack: EntityPack, extra_rows: list[dict[str, Any]], *, top_clusters: int, prefix: str) -> EntityPack:
    if not extra_rows:
        return pack
    merged = list(pack.rows) + list(extra_rows)
    clusters = rank_clusters(cluster_rows(merged, top_clusters=max(top_clusters * 3, 4)))[:top_clusters]
    for cluster in clusters:
        cluster.cluster_id = f"{prefix}#{cluster.cluster_id}"
    diag = dict(pack.diagnostics)
    diag["holding_rows"] = len(extra_rows)
    return EntityPack(
        entity_name=pack.entity_name,
        entity_type=pack.entity_type,
        clusters=clusters,
        rows=merged,
        diagnostics=diag,
    )


def fetch_sector_news_pack(
    ctx,
    sector_name: str,
    window: tuple[str, str],
    today: tuple[str, str],
    *,
    top_clusters: int = 12,
    client: Any | None = None,
    gate: GateConfig | None = None,
) -> EntityPack:
    """Sector entities first; bellwether holdings when sector tags are weak (common for Nifty IT)."""
    gate = gate or SECTOR_INDEX_GATE
    pack = fetch_sector_pack(ctx, sector_name, window, today, top_clusters=top_clusters, client=client, gate=gate)
    if not pack.rows:
        pack = fetch_entity_pack(
            ctx,
            sector_name,
            "sector",
            window,
            top_clusters=top_clusters,
            client=client,
            gate=SECTOR_RELAXED_GATE,
        )
        pack.rows = _tag_rows(pack.rows, window, today)
    holdings = bellwether_holdings(sector_name)
    if holdings and len(pack.rows) < _MIN_SECTOR_ROWS_BEFORE_HOLDINGS:
        hold = fetch_entity_rows("holding", window, holdings, gate=HOLDING_READTHROUGH_GATE, client=client, log=ctx.log)
        extra = _sectorize_holding_rows(_tag_rows(hold.rows, window, today), sector_name)
        prefix = slug(sector_name)
        pack = _merge_pack_clusters(pack, extra, top_clusters=top_clusters, prefix=prefix)
        pack.diagnostics = {**pack.diagnostics, "holdings_passed": hold.diagnostics.entities_passed}
    if not pack.rows:
        pack = fetch_sector_pack(ctx, sector_name, window, today, top_clusters=top_clusters, client=client, gate=SECTOR_RELAXED_GATE)
    return pack


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
            "sectors": news_sectors_for_index(best.spec),
        }
        best_names = list(news_sectors_for_index(best.spec))
    if worst is not None:
        meta["worst_index"] = {
            "display": worst.spec.display,
            "week_change_pct": worst.week_change_pct,
            "sectors": news_sectors_for_index(worst.spec),
        }
        worst_names = list(news_sectors_for_index(worst.spec))
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
        fetch_sector_news_pack(ctx, name, week, today, top_clusters=top_clusters, client=client)
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
        pack = fetch_sector_news_pack(ctx, name, week, today, top_clusters=12, client=client)
        ctx.log.line(
            "INDEX_NEWS",
            f"sector={name} rows={len(pack.rows)} clusters={len(pack.clusters)} "
            f"holdings={pack.diagnostics.get('holdings_passed', 0)}",
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
    "bellwether_holdings",
    "fetch_sector_index",
    "fetch_sector_news_pack",
    "fetch_sector_pulse_sectors",
    "merge_evidence",
    "sector_names_for_pulse",
    "week_index_movers",
    "HOLDING_READTHROUGH_GATE",
    "SECTOR_INDEX_GATE",
    "SECTOR_RELAXED_GATE",
]