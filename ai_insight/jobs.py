"""One live insights job at a time. Each insight is its own process."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable

from ai_insight.common.config import CommonConfig, load_config
from ai_insight.common.jobs import JobProgress
from ai_insight.common.runner import resolve_live_date
from ai_insight.fii_dii_flow_narrative.collector import prefetch_fii_dii

MODULES = [
    "sector_leaderboard",
    "market_driver_digest",
    "fii_dii_flow_narrative",
    "sector_index_insights",
    "additional_insights",
]


class JobBusy(Exception):
    def __init__(self, job_id: str) -> None:
        super().__init__(job_id)
        self.job_id = job_id


@dataclass
class JobView:
    job_id: str
    status: str
    started_at: float
    finished_at: float | None = None
    trading_date: str | None = None
    insight_ids: list[str] = field(default_factory=list)
    progress: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)


class JobManager:
    def __init__(self, config: CommonConfig | None = None, runner: Callable[..., int] | None = None) -> None:
        self.config = config or load_config()
        self.root = self.config.data_dir / "jobs"
        self.root.mkdir(parents=True, exist_ok=True)
        self.runner = runner or _subprocess

    def start(self, trading_date: date | None, insights: list[str] | None = None) -> JobView:
        active = self._active()
        if active is not None:
            raise JobBusy(active)
        latest = self.latest()
        if latest and latest.finished_at and time.time() - latest.finished_at < self.config.live_cooldown_sec and latest.status == "done":
            raise JobBusy(latest.job_id)
        job_id = uuid.uuid4().hex[:12]
        chosen = insights or list(MODULES)
        payload = {"job_id": job_id, "status": "running", "started_at": time.time(), "finished_at": None, "insights": chosen, "date": None if trading_date is None else trading_date.isoformat(), "pid": os.getpid()}
        _write(self.root / f"{job_id}.json", payload)
        _write(self.root / ".lock", {"job_id": job_id, "pid": os.getpid(), "heartbeat": time.time()})
        thread = threading.Thread(target=self._run, args=(job_id, trading_date, chosen), daemon=True)
        thread.start()
        return self.get(job_id)

    def get(self, job_id: str) -> JobView:
        path = self.root / f"{job_id}.json"
        if not path.is_file():
            raise KeyError(job_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        progress = {}
        folder = self.root / job_id
        if folder.is_dir():
            for item in folder.glob("*.json"):
                progress[item.stem] = json.loads(item.read_text(encoding="utf-8"))
        return JobView(
            job_id,
            payload.get("status") or "running",
            float(payload.get("started_at") or 0),
            payload.get("finished_at"),
            str(payload.get("date") or "") or None,
            list(payload.get("insights") or []),
            progress,
            payload.get("results") or {},
        )

    def latest(self) -> JobView | None:
        files = sorted(self.root.glob("*.json"), key=lambda item: item.stat().st_mtime)
        files = [item for item in files if item.name != ".lock"]
        if not files:
            return None
        return self.get(files[-1].stem)

    def _active(self) -> str | None:
        lock = self.root / ".lock"
        if not lock.is_file():
            return None
        payload = json.loads(lock.read_text(encoding="utf-8"))
        age = time.time() - float(payload.get("heartbeat") or 0)
        if age > self.config.live_max_minutes * 60:
            lock.unlink(missing_ok=True)
            return None
        job_id = str(payload.get("job_id") or "")
        view = self.get(job_id) if (self.root / f"{job_id}.json").is_file() else None
        if view and view.status == "running":
            return job_id
        return None

    def _run(self, job_id: str, trading_date: date | None, insights: list[str]) -> None:
        resolved = trading_date or resolve_live_date(holidays_path=self.config.holidays_path)
        day = resolved.isoformat()
        path = self.root / f"{job_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["date"] = day
        _write(path, payload)
        try:
            prefetch_fii_dii(resolved, config=self.config)
        except Exception:
            pass
        results: dict[str, str] = {}
        if max(1, self.config.live_parallel) <= 1:
            for name in insights:
                try:
                    results[name] = "ok" if self._one(job_id, name, day) == 0 else "failed"
                except Exception:
                    results[name] = "failed"
                    JobProgress(job_id, name, self.config.data_dir).finish("failed", "error")
        else:
            workers = max(1, self.config.live_parallel)
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(self._one, job_id, name, day): name for name in insights}
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        results[name] = "ok" if future.result() == 0 else "failed"
                    except Exception:
                        results[name] = "failed"
                        JobProgress(job_id, name, self.config.data_dir).finish("failed", "error")
        payload = json.loads(path.read_text(encoding="utf-8"))
        for name in insights:
            results.setdefault(name, "failed")
        payload["status"] = "done"
        payload["finished_at"] = time.time()
        payload["results"] = results
        _write(path, payload)
        (self.root / ".lock").unlink(missing_ok=True)

    def _one(self, job_id: str, name: str, day: str) -> int:
        progress = JobProgress(job_id, name, self.config.data_dir)
        progress.update("starting")
        code = self.runner(name, day, job_id, self.config.live_max_minutes * 60)
        progress.finish("done" if code == 0 else "failed")
        return code


def _subprocess(name: str, day: str, job_id: str, timeout: float) -> int:
    module = f"ai_insight.{name}.run"
    command = [sys.executable, "-m", module, "--live", "--force"]
    if day:
        command.extend(["--date", day])
    env = os.environ.copy()
    env["INSIGHTS_JOB_ID"] = job_id
    try:
        completed = subprocess.run(command, timeout=timeout, check=False, env=env)
        return int(completed.returncode)
    except subprocess.TimeoutExpired:
        return 1


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, path)
