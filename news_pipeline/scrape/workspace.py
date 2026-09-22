"""Ephemeral on-disk scrape artifacts. Cleared each run so text is not reused from stale files."""

from __future__ import annotations

import hashlib
import logging
import shutil
from pathlib import Path

from news_pipeline.config import Settings

logger = logging.getLogger(__name__)

_ARTIFACT_SUFFIXES = (".json", ".html", ".txt")


def workspace_dir(settings: Settings) -> Path:
    return settings.path(settings.scrape_workspace_dir)


def url_artifact_stem(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return digest[:32]


def clear_scrape_workspace(settings: Settings) -> int:
    """Delete all cached scrape files. Returns number of files removed."""
    root = workspace_dir(settings)
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
        return 0
    removed = sum(1 for path in root.rglob("*") if path.is_file())
    shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    if removed:
        logger.info("cleared scrape workspace %s files=%s", root, removed)
    return removed


def remove_scrape_artifacts(settings: Settings, url: str) -> int:
    """Remove on-disk copies for one URL after it is stored in Qdrant."""
    root = workspace_dir(settings)
    if not root.exists():
        return 0
    stem = url_artifact_stem(url)
    removed = 0
    for suffix in _ARTIFACT_SUFFIXES:
        path = root / f"{stem}{suffix}"
        if path.is_file():
            path.unlink()
            removed += 1
    legacy = root / stem
    if legacy.is_dir():
        shutil.rmtree(legacy)
        removed += 1
    return removed


def remove_scrape_artifacts_many(settings: Settings, urls: list[str]) -> int:
    total = 0
    for url in urls:
        total += remove_scrape_artifacts(settings, url)
    return total
