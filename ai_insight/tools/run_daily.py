"""Wait for the news ingest, then run each insight in its own process."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

from ai_insight.common.config import load_config
from ai_insight.common.notify import notify_failure
from ai_insight.common.trading_calendar import is_trading_day
from ai_insight.fii_dii_flow_narrative.collector import prefetch_fii_dii
from ai_insight.common.store import save_json
from ai_insight.common.time_ist import ist_now

MODULES = [
    "sector_leaderboard",
    "sector_index_insights",
    "market_driver_digest",
    "fii_dii_flow_narrative",
    "additional_insights",
]


def ingest_ready(summary_path: Path, cron_log: Path, *, now: datetime | None = None) -> tuple[bool, str]:
    """True when today's run_summary.json finished after 11:40 UTC, or the cron log already closed the slot."""
    clock = now or datetime.now(timezone.utc)
    slot = clock.date().isoformat()
    if cron_log.is_file():
        lines = cron_log.read_text(encoding="utf-8", errors="replace").splitlines()
        today = [line for line in lines if slot in line or clock.strftime("%Y-%m-%d") in line]
        if today and "daily skipped" in today[-1]:
            return False, "ingest skipped"
        if today and ("daily success" in today[-1] or "daily failed" in today[-1]):
            return True, today[-1]
    if summary_path.is_file():
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        finished = str(payload.get("finished_at") or "")
        if finished.startswith(slot) or finished[:10] == clock.astimezone(timezone.utc).date().isoformat():
            return True, "run_summary " + finished
    return False, "waiting"


def run_daily(*, dry_run: bool = False, simulate_failure: str = "", max_wait_sec: float = 6 * 3600, poll_sec: float = 60) -> int:
    cfg = load_config()
    root = Path(os.environ.get("NEWS_RAG_DIR") or Path(__file__).resolve().parents[2])
    summary = root / "data" / "news_runs_daily" / "run_summary.json"
    cron_log = root / "data" / "news_runs_daily" / "cron" / "cron.log"
    deadline = time.time() + max_wait_sec
    warning = ""
    while True:
        ready, detail = ingest_ready(summary, cron_log)
        if ready or dry_run:
            if not ready:
                warning = "ingest had not finished; " + detail
            break
        if time.time() >= deadline:
            warning = "ingest did not finish before the wait limit"
            break
        time.sleep(poll_sec)
    child_env = os.environ.copy()
    if warning:
        child_env["INSIGHTS_INGEST_WARNING"] = warning
    day = ist_now().date().isoformat()
    if not dry_run and is_trading_day(date.fromisoformat(day), holidays_path=cfg.holidays_path):
        try:
            prefetch_fii_dii(date.fromisoformat(day), config=cfg)
        except Exception:
            pass
    results = []
    for name in MODULES:
        if dry_run:
            results.append({"insight": name, "status": "dry_run", "code": 0, "duration_sec": 0})
            continue
        if name == simulate_failure:
            results.append({"insight": name, "status": "failed", "code": 1, "duration_sec": 0})
            notify_failure(f"{name} simulated failure")
            continue
        started = time.perf_counter()
        command = [sys.executable, "-m", f"ai_insight.{name}.run", "--date", day, "--force"]
        completed = subprocess.run(command, check=False, env=child_env)
        code = int(completed.returncode)
        status = "ok" if code == 0 else "failed"
        if code != 0:
            notify_failure(f"{name} exited {code}")
        results.append({"insight": name, "status": status, "code": code, "duration_sec": round(time.perf_counter() - started, 1)})
    summary_path = cfg.data_dir / "logs" / f"run_{day}.json"
    save_json(summary_path, {"date": day, "warning": warning, "insights": results})
    print(json.dumps({"date": day, "failed": sum(1 for row in results if row["status"] == "failed")}, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ai_insight.tools.run_daily")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--simulate-failure", default="")
    parser.add_argument("--max-wait-sec", type=float, default=6 * 3600)
    parser.add_argument("--poll-sec", type=float, default=60)
    args = parser.parse_args(argv)
    return run_daily(dry_run=args.dry_run, simulate_failure=args.simulate_failure, max_wait_sec=args.max_wait_sec, poll_sec=args.poll_sec)


if __name__ == "__main__":
    raise SystemExit(main())
