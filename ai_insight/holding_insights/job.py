"""Background jobs for holding insights batch runs."""

from __future__ import annotations

import json
import os
import shutil
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_insight.holding_insights.config import holding_data_dir
from ai_insight.holding_insights.run import run_batch


class HoldingJobBusy(Exception):
    def __init__(self, job_id: str) -> None:
        super().__init__(job_id)
        self.job_id = job_id


@dataclass
class HoldingJobView:
    job_id: str
    status: str
    started_at: float
    finished_at: float | None = None
    limit: int = 0
    progress: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None


class HoldingInsightsJobManager:
    def __init__(self) -> None:
        self.root = holding_data_dir() / "jobs"
        self.runs = holding_data_dir() / "runs"
        self.root.mkdir(parents=True, exist_ok=True)
        self.runs.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def start(self, limit: int, *, dry_run: bool = False) -> HoldingJobView:
        with self._lock:
            active = self._active_job_id()
            if active:
                raise HoldingJobBusy(active)
            self._clear_stored_runs()
        job_id = uuid.uuid4().hex[:12]
        payload = {
            "job_id": job_id,
            "status": "running",
            "started_at": time.time(),
            "finished_at": None,
            "limit": limit,
            "dry_run": dry_run,
            "pid": os.getpid(),
        }
        _write(self.root / f"{job_id}.json", payload)
        _write(self.root / ".lock", {"job_id": job_id, "heartbeat": time.time()})
        thread = threading.Thread(target=self._run, args=(job_id, limit, dry_run), daemon=True)
        thread.start()
        return self.get(job_id)

    def get(self, job_id: str) -> HoldingJobView:
        path = self.root / f"{job_id}.json"
        if not path.is_file():
            raise KeyError(job_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        progress_path = self.root / job_id / "progress.json"
        progress = {}
        if progress_path.is_file():
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
        result = None
        run_path = self.runs / f"{job_id}.json"
        if run_path.is_file():
            result = json.loads(run_path.read_text(encoding="utf-8"))
        return HoldingJobView(
            job_id,
            str(payload.get("status") or "running"),
            float(payload.get("started_at") or 0),
            payload.get("finished_at"),
            int(payload.get("limit") or 0),
            progress,
            result,
        )

    def latest(self) -> HoldingJobView | None:
        files = sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime)
        files = [p for p in files if p.name != ".lock"]
        if not files:
            return None
        return self.get(files[-1].stem)

    def _clear_stored_runs(self) -> None:
        for path in self.runs.glob("*.json"):
            path.unlink(missing_ok=True)
        logs_root = holding_data_dir() / "stock_logs"
        if logs_root.is_dir():
            shutil.rmtree(logs_root, ignore_errors=True)
        logs_root.mkdir(parents=True, exist_ok=True)
        for path in self.root.glob("*.json"):
            path.unlink(missing_ok=True)
        for path in self.root.iterdir():
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

    def _active_job_id(self) -> str | None:
        lock = self.root / ".lock"
        if not lock.is_file():
            return None
        data = json.loads(lock.read_text(encoding="utf-8"))
        age = time.time() - float(data.get("heartbeat") or 0)
        if age > 3600:
            lock.unlink(missing_ok=True)
            return None
        job_id = str(data.get("job_id") or "")
        view = self.get(job_id) if (self.root / f"{job_id}.json").is_file() else None
        if view and view.status == "running":
            return job_id
        return None

    def _run(self, job_id: str, limit: int, dry_run: bool) -> None:
        path = self.root / f"{job_id}.json"
        prog_dir = self.root / job_id
        prog_dir.mkdir(parents=True, exist_ok=True)

        def on_progress(done: int, total: int, stock_id: str, phase: str) -> None:
            _write(
                prog_dir / "progress.json",
                {
                    "done": done,
                    "total": total,
                    "last_stock_id": stock_id,
                    "phase": phase,
                    "heartbeat": time.time(),
                },
            )
            _write(self.root / ".lock", {"job_id": job_id, "heartbeat": time.time()})

        try:
            outcome = run_batch(limit, dry_run=dry_run, job_id=job_id, on_progress=on_progress)
            _write(self.runs / f"{job_id}.json", outcome)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["status"] = "done"
            payload["finished_at"] = time.time()
            _write(path, payload)
        except Exception as exc:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["status"] = "failed"
            payload["error"] = str(exc)[:500]
            payload["finished_at"] = time.time()
            _write(path, payload)
        finally:
            (self.root / ".lock").unlink(missing_ok=True)


_manager: HoldingInsightsJobManager | None = None


def get_holding_job_manager() -> HoldingInsightsJobManager:
    global _manager
    if _manager is None:
        _manager = HoldingInsightsJobManager()
    return _manager


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)