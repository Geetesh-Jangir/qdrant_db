"""Write per-run JSON artifacts (funnel, publisher stats, failure slices)."""

from __future__ import annotations

from pathlib import Path

from news_pipeline.config import Settings
from news_pipeline.entity_funnel import get_entity_funnel
from news_pipeline.failure_ledger import flush, write_day_slices
from news_pipeline.publisher_stats import get_publisher_stats


def finalize_run_artifacts(settings: Settings, summary_dir: Path) -> None:
    flush(settings)
    write_day_slices(settings, summary_dir)
    get_entity_funnel().write(summary_dir / "entity_funnel.json")
    get_publisher_stats().write(summary_dir / "publisher_stats.json")
