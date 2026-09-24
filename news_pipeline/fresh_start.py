"""Wipe ephemeral files and optional Qdrant data before each run."""

from __future__ import annotations

import logging
from pathlib import Path

from news_pipeline.config import Settings
from news_pipeline.scrape.workspace import clear_scrape_workspace
from news_pipeline.services import get_store

logger = logging.getLogger(__name__)

_RUN_ARTIFACT_SUFFIXES = (".json", ".log")


def apply_fresh_start(settings: Settings) -> dict:
    """Return counts of what was removed. No-op when fresh_start_each_run is false."""
    if not settings.fresh_start_each_run:
        return {"enabled": False}

    scrape_files = clear_scrape_workspace(settings)
    run_files = _clear_run_artifacts(settings)
    qdrant_reset = False
    if settings.fresh_start_clear_qdrant and not settings.news_corpus_mode:
        get_store().reset_collection()
        qdrant_reset = True

    summary = {
        "enabled": True,
        "scrape_files_removed": scrape_files,
        "run_artifacts_removed": run_files,
        "qdrant_collection_reset": qdrant_reset,
    }
    logger.info("fresh start %s", summary)
    return summary


def _clear_run_artifacts(settings: Settings) -> int:
    root = settings.path(settings.run_summary_dir)
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
        return 0
    removed = 0
    for path in _iter_run_artifacts(root):
        path.unlink(missing_ok=True)
        removed += 1
    return removed


def _iter_run_artifacts(root: Path):
    for path in root.iterdir():
        if path.is_file() and path.suffix.lower() in _RUN_ARTIFACT_SUFFIXES:
            yield path
