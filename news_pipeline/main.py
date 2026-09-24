"""Run one daily news pass and write a JSON summary."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from news_pipeline.fresh_start import apply_fresh_start
from news_pipeline.graph.build import build_graph
from news_pipeline.qdrant_target import qdrant_summary, validate_qdrant_settings
from news_pipeline.run_log import finish_run_logger, get_run_logger, start_run_logger
from news_pipeline.scrape.workspace import clear_scrape_workspace
from news_pipeline.services import get_settings, get_store
from news_pipeline.textutil import to_iso, utc_now

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    settings = get_settings()
    validate_qdrant_settings(settings)
    if not settings.jev_base_url or not settings.jev_api_key:
        raise SystemExit("Set JEV_BASE_URL and JEV_API_KEY in .env")

    started = utc_now()
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    summary_dir = settings.path(settings.run_summary_dir)
    summary_dir.mkdir(parents=True, exist_ok=True)

    fresh_start = apply_fresh_start(settings)

    log_path = summary_dir / f"{run_id}.log"
    start_run_logger(run_id, log_path, settings.jev_input_cost_per_million_usd)
    run_log = get_run_logger()
    qdrant_info = qdrant_summary(settings)
    if run_log is not None:
        run_log.write(
            "qdrant target "
            f"host={qdrant_info['url_host']} "
            f"collection={qdrant_info['collection']} "
            f"cloud={qdrant_info['cloud']} "
            f"news_corpus_mode={settings.news_corpus_mode}"
        )
    if run_log is not None and fresh_start.get("enabled"):
        run_log.write(
            "fresh start "
            f"scrape_files_removed={fresh_start.get('scrape_files_removed', 0)} "
            f"run_artifacts_removed={fresh_start.get('run_artifacts_removed', 0)} "
            f"qdrant_collection_reset={fresh_start.get('qdrant_collection_reset', False)}"
        )
    elif not settings.fresh_start_each_run:
        cleared = clear_scrape_workspace(settings)
        if run_log is not None and cleared:
            run_log.write(f"scrape workspace cleared files={cleared} dir={settings.scrape_workspace_dir}")

    initial = {
        "run_id": run_id,
        "started_at": to_iso(started),
        "entities": [],
        "candidates": [],
        "known_merges": [],
        "canonical_merges": [],
        "counts": {},
        "errors": [],
    }
    result = initial
    telemetry = None
    try:
        store = get_store()
        store.ensure_collection()
        if run_log is not None:
            run_log.write(f"qdrant collection ready points_count={store.points_count()}")
        result = build_graph().invoke(initial)
    except Exception as exc:
        logger.exception("news pipeline failed")
        result = {
            **initial,
            "errors": list(initial["errors"]) + [{"stage": "run", "error": str(exc)}],
        }
        telemetry = finish_run_logger()
        _write_summary(summary_dir / f"{run_id}.json", result, started, telemetry, fresh_start, qdrant_info)
        raise SystemExit(1) from exc
    finally:
        leftover = clear_scrape_workspace(settings)
        if leftover:
            logger.info("removed leftover scrape files=%s", leftover)
            run_log = get_run_logger()
            if run_log is not None:
                run_log.write(f"scrape workspace final cleanup files={leftover}")

    telemetry = finish_run_logger()
    qdrant_info["points_count_after_run"] = get_store().points_count()
    path = _write_summary(summary_dir / f"{run_id}.json", result, started, telemetry, fresh_start, qdrant_info)
    counts = result.get("counts") or {}
    logger.info("run complete summary=%s upserted=%s", path, counts.get("upserted", 0))
    if telemetry:
        logger.info(
            "run log=%s total_seconds=%s llm_calls=%s input_tokens=%s input_cost_usd=%s",
            telemetry.get("log_file"),
            telemetry.get("total_seconds"),
            telemetry.get("llm_calls"),
            telemetry.get("input_tokens"),
            telemetry.get("input_cost_usd"),
        )


def _write_summary(
    path,
    result: dict,
    started: datetime,
    telemetry: dict | None,
    fresh_start: dict | None,
    qdrant_info: dict | None,
) -> str:
    finished = datetime.now(timezone.utc)
    payload = {
        "pipeline": "full",
        "run_id": result.get("run_id"),
        "started_at": to_iso(started),
        "finished_at": to_iso(finished),
        "counts": result.get("counts") or {},
        "errors": result.get("errors") or [],
    }
    if fresh_start:
        payload["fresh_start"] = fresh_start
    if qdrant_info:
        payload["qdrant"] = qdrant_info
    if telemetry:
        payload["telemetry"] = telemetry
    else:
        step_timings = result.get("step_timings_sec")
        llm_usage = result.get("llm_usage")
        if step_timings or llm_usage:
            payload["telemetry"] = {
                "step_timings_sec": step_timings or {},
                "llm_usage": llm_usage or {},
            }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return str(path)
