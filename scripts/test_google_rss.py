"""Test Google News RSS from the current host (e.g. GitHub Actions). No Jev or Qdrant."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Allow `python scripts/test_google_rss.py` on CI without PYTHONPATH.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_pipeline.config import Settings
from news_pipeline.run_log import clip_log_text, finish_run_logger, get_run_logger, start_run_logger
from news_pipeline.sources.google_news import fetch_entity_items
from news_pipeline.sources.universe import load_universe
from news_pipeline.textutil import to_iso, utc_now

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def main() -> None:
    settings = Settings()
    started = utc_now()
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    summary_dir = settings.path(settings.run_summary_dir)
    summary_dir.mkdir(parents=True, exist_ok=True)
    log_path = summary_dir / f"{run_id}.log"
    json_path = summary_dir / f"{run_id}.json"

    try:
        _run_test(settings, started, run_id, summary_dir, log_path, json_path)
    except Exception as exc:
        crash = {
            "run_id": run_id,
            "status": "crashed",
            "error": str(exc),
        }
        log_path.write_text(f"crash error={exc}\n", encoding="utf-8")
        json_path.write_text(json.dumps(crash, indent=2), encoding="utf-8")
        print(json.dumps(crash, indent=2))
        raise


def _run_test(settings, started, run_id, summary_dir, log_path, json_path) -> None:
    start_run_logger(run_id, log_path, settings.jev_input_cost_per_million_usd)
    run_log = get_run_logger()
    if run_log is not None:
        run_log.write("google_rss_test started (no jev/qdrant)")

    entities = load_universe(settings)
    if run_log is not None:
        run_log.write(f"entities={len(entities)}")

    successes = 0
    failures = 0
    total_items = 0
    errors: list[dict] = []

    for entity in entities:
        name = entity["name"]
        try:
            rows = fetch_entity_items(entity, settings)
            successes += 1
            total_items += len(rows)
            if run_log is not None:
                run_log.write(f"fetch entity={name} type={entity['type']} ok items={len(rows)}")
        except Exception as exc:
            failures += 1
            message = str(exc)
            errors.append({"entity": name, "error": message.split("\n", 1)[0]})
            if run_log is not None:
                run_log.write(
                    f"fetch entity={name} type={entity['type']} FAIL error={clip_log_text(message)}"
                )

    telemetry = finish_run_logger()
    if failures > 0 and successes == 0:
        status = "all_fetch_failed"
    elif failures > 0:
        status = "partial_failure"
    else:
        status = "ok"
    summary = {
        "pipeline": "rss-only",
        "run_id": run_id,
        "started_at": to_iso(started),
        "finished_at": to_iso(utc_now()),
        "status": status,
        "entities": len(entities),
        "fetch_ok": successes,
        "fetch_fail": failures,
        "google_items": total_items,
        "errors": errors[:20],
        "telemetry": telemetry,
    }
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    # Exit 0 so CI uploads artifacts; read status / errors in the JSON log.


if __name__ == "__main__":
    main()
