"""Load the holdings and sectors that will be searched."""

from __future__ import annotations

import logging

from news_pipeline.graph.state import PipelineState
from news_pipeline.services import get_settings
from news_pipeline.sources.universe import load_universe as read_universe

logger = logging.getLogger(__name__)


def load_universe(state: PipelineState) -> dict:
    settings = get_settings()
    entities = read_universe(settings)
    counts = dict(state.get("counts") or {})
    counts["entities"] = len(entities)
    holdings = sum(1 for entity in entities if entity["type"] == "holding")
    sectors = len(entities) - holdings
    logger.info("load_universe holdings=%s sectors=%s", holdings, sectors)
    return {"entities": entities, "counts": counts}
