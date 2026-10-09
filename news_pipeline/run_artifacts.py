"""Write per-run JSON artifacts (funnel, publisher stats, failure slices)."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from news_pipeline.config import Settings
from news_pipeline.day_report import write_day_report
from news_pipeline.entity_funnel import get_entity_funnel
from news_pipeline.failure_ledger import day_failure_slices_for_run, flush, write_day_slices
from news_pipeline.publisher_stats import get_publisher_stats
from news_pipeline.run_context import get_run_context


def finalize_run_artifacts(
    settings: Settings,
    summary_dir: Path,
    counts: dict[str, Any] | None = None,
    run_id: str = "",
) -> None:
    flush(settings)
    write_day_slices(settings, summary_dir)
    google_slice, source_slice = day_failure_slices_for_run()
    get_entity_funnel().write(summary_dir / "entity_funnel.json")
    get_publisher_stats().write(summary_dir / "publisher_stats.json")
    write_day_report(
        summary_dir / "day_report.json",
        counts=counts or {},
        google_failures=google_slice,
        source_failures=source_slice,
    )
    if run_id:
        publish_stable_run_files(summary_dir, run_id)


def publish_stable_run_files(summary_dir: Path, run_id: str) -> None:
    """Stable names beside {run_id}.* so day folders are easy to download."""
    ctx = get_run_context()
    detailed_json = summary_dir / f"{run_id}.json"
    detailed_log = summary_dir / f"{run_id}.log"
    if detailed_json.is_file():
        shutil.copy2(detailed_json, summary_dir / "run_summary.json")
        if ctx.calendar_day:
            shutil.copy2(detailed_json, summary_dir / f"{ctx.calendar_day}_run_summary.json")
    if detailed_log.is_file():
        shutil.copy2(detailed_log, summary_dir / "run.log")
        if ctx.calendar_day:
            shutil.copy2(detailed_log, summary_dir / f"{ctx.calendar_day}.log")
