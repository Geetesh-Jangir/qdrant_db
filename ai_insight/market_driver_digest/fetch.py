"""Macro rows for the digest. The ranker decides which clusters explain the move."""

from __future__ import annotations

from typing import Any

from ai_insight.common.clustering import Cluster, cluster_rows
from ai_insight.common.qdrant_access import fetch_entity_rows


def fetch_macro_clusters(window: tuple[str, str], *, client: Any = None, log: Any = None) -> list[Cluster]:
    result = fetch_entity_rows("macro", window, client=client, log=log)
    return cluster_rows(result.rows, top_clusters=20)
