"""Per-calendar-day rollup: pipeline counts, publisher totals, failure counts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from news_pipeline.publisher_stats import get_publisher_stats
from news_pipeline.run_context import get_run_context


def write_day_report(
    path: Path,
    counts: dict[str, Any],
    google_failures: list[dict],
    source_failures: list[dict],
) -> None:
    ctx = get_run_context()
    pub_payload = get_publisher_stats().build_payload()
    google_by_kind: dict[str, int] = {}
    for row in google_failures:
        kind = str(row.get("kind") or "unknown")
        google_by_kind[kind] = google_by_kind.get(kind, 0) + 1

    source_by_reason: dict[str, int] = {}
    for row in source_failures:
        reason = str(row.get("drop_reason") or row.get("last_error") or "unknown")
        source_by_reason[reason] = source_by_reason.get(reason, 0) + 1

    payload = {
        "run_id": ctx.run_id,
        "calendar_day": ctx.calendar_day,
        "news_date_range": ctx.news_date_range,
        "pipeline_counts": dict(counts),
        "google_news": {
            "publisher_urls_kept_after_resolve": pub_payload["totals"]["urls_received"],
            "failure_records_this_run": len(google_failures),
            "failures_by_kind": google_by_kind,
        },
        "scrape": {
            "urls_scraped_ok": pub_payload["totals"]["urls_scraped"],
            "urls_scrape_errors": pub_payload["totals"]["urls_scrape_errors"],
            "scrape_errors_by_reason": _merge_publisher_error_reasons(pub_payload["publishers"]),
        },
        "publishers": pub_payload["publishers"],
        "publisher_totals": pub_payload["totals"],
        "source_failure_records_this_run": len(source_failures),
        "source_failures_by_reason": source_by_reason,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _merge_publisher_error_reasons(publishers: list[dict]) -> dict[str, int]:
    merged: dict[str, int] = {}
    for row in publishers:
        for reason, count in (row.get("error_reasons") or {}).items():
            merged[reason] = merged.get(reason, 0) + int(count)
    return merged
