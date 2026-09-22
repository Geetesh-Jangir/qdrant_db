"""Delete points whose publish time is older than the retention window."""

from __future__ import annotations

import logging

from news_pipeline.graph.state import PipelineState
from news_pipeline.services import get_settings, get_store

logger = logging.getLogger(__name__)


def drop_old_points(state: PipelineState) -> dict:
    settings = get_settings()
    deleted = get_store().delete_older_than(settings.retention_days)
    counts = dict(state.get("counts") or {})
    counts["deleted"] = deleted
    logger.info("drop_old_points deleted=%s", deleted)
    return {"counts": counts}
