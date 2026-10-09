"""Run news ingest for each calendar day in an inclusive range."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

from news_pipeline.config import repo_root
from news_pipeline.news_dates import (
    NewsDateRangeError,
    iter_inclusive_days,
    parse_one_date,
    single_day_news_date_range,
)


def _checkpoint_path(start: date, end: date) -> Path:
    root = repo_root() / "data" / "news_backfill"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"checkpoint_{start.isoformat()}_{end.isoformat()}.json"


def _load_checkpoint(path: Path) -> dict:
    if not path.is_file():
        return {"completed": [], "failed": None}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"completed": [], "failed": None}


def _save_checkpoint(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    start_raw = os.environ.get("BACKFILL_START", "1/10/2026").strip()
    end_raw = os.environ.get("BACKFILL_END", "3/10/2026").strip()
    pause_sec = int(os.environ.get("BACKFILL_PAUSE_SEC", "600") or "600")

    try:
        start = parse_one_date(start_raw)
        end = parse_one_date(end_raw)
        days = iter_inclusive_days(start, end)
    except NewsDateRangeError as exc:
        raise SystemExit(f"Invalid backfill dates: {exc}") from exc

    checkpoint = _checkpoint_path(start, end)
    state = _load_checkpoint(checkpoint)
    completed = set(state.get("completed") or [])

    pending = [d for d in days if d.isoformat() not in completed]
    if not pending and state.get("failed"):
        pending = [date.fromisoformat(state["failed"]["date"])]

    if not pending:
        print("backfill_days nothing to do (all days completed)", flush=True)
        return

    root = repo_root()
    python = sys.executable

    for index, day in enumerate(pending):
        iso = day.isoformat()
        env = os.environ.copy()
        env["NEWS_DATE_RANGE"] = single_day_news_date_range(day)
        env["NEWS_RUN_SUBDIR"] = iso
        print(f"backfill_days starting day={iso} range={env['NEWS_DATE_RANGE']}", flush=True)
        result = subprocess.run(
            [python, "-m", "news_pipeline"],
            cwd=str(root),
            env=env,
            check=False,
        )
        if result.returncode != 0:
            state["failed"] = {"date": iso, "returncode": result.returncode}
            _save_checkpoint(checkpoint, state)
            raise SystemExit(result.returncode)

        completed.add(iso)
        state["completed"] = sorted(completed)
        state["failed"] = None
        _save_checkpoint(checkpoint, state)
        print(f"backfill_days finished day={iso}", flush=True)

        if index < len(pending) - 1:
            print(f"backfill_days sleeping pause_sec={pause_sec}", flush=True)
            time.sleep(pause_sec)

    print("backfill_days all days complete", flush=True)


if __name__ == "__main__":
    main()
