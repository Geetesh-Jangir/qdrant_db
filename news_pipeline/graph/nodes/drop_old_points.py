"""Delete points whose publish time is older than the retention window."""

from __future__ import annotations

import logging

from news_pipeline.graph.state import PipelineState
from news_pipeline.run_log import get_run_logger
from news_pipeline.services import get_settings, get_store

logger = logging.getLogger(__name__)


def drop_old_points(state: PipelineState) -> dict:
    settings = get_settings()
    run_log = get_run_logger()
    if run_log is not None:
        before = get_store().points_count()
        run_log.write(
            f"drop_old_points started retention_days={settings.retention_days} points_before={before}"
        )
    deleted = get_store().delete_older_than(settings.retention_days)
    counts = dict(state.get("counts") or {})
    counts["deleted"] = deleted
    if run_log is not None:
        after = get_store().points_count()
        run_log.write(f"drop_old_points finished deleted={deleted} points_after={after}")
    logger.info("drop_old_points deleted=%s", deleted)
    return {"counts": counts}
