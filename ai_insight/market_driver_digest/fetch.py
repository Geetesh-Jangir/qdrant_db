"""Digest news: broad macro packs plus pulse sector packs."""

from __future__ import annotations

from typing import Any

from news_pipeline.config import SECTOR_QUERIES

from ai_insight.common.clustering import Cluster, cluster_rows
from ai_insight.common.entity_retrieval import (
    MARKET_DRIVER_MACROS,
    fetch_entity_pack,
    fetch_macro_packs,
    packs_to_section,
)
from ai_insight.common.qdrant_access import fetch_entity_rows
from ai_insight.common.retrieval_plan import SectionRetrieval, plan_window


def fetch_macro_clusters(window: tuple[str, str], *, client: Any = None, log: Any = None) -> list[Cluster]:
    result = fetch_entity_rows("macro", window, client=client, log=log)
    return cluster_rows(result.rows, top_clusters=20)


def fetch_digest_news(ctx, client: Any | None, pulse_sector_names: list[str]) -> SectionRetrieval:
    """Macro corpus plus up to four sector packs for week pulse names."""
    week, today = plan_window(ctx, "market_driver_digest")
    macro_packs = fetch_macro_packs(ctx, week, list(MARKET_DRIVER_MACROS), top_clusters=2, client=client)
    sector_names = []
    for name in pulse_sector_names:
        if name in SECTOR_QUERIES and name not in sector_names:
            sector_names.append(name)
        if len(sector_names) >= 4:
            break
    sector_packs = [
        fetch_entity_pack(ctx, name, "sector", week, top_clusters=2, client=client)
        for name in sector_names
    ]
    all_packs = macro_packs + sector_packs
    max_clusters = max(ctx.config.max_clusters, 20)
    return packs_to_section(
        ctx,
        all_packs,
        week,
        today,
        per_cluster=4,
        max_clusters=max_clusters,
    )
