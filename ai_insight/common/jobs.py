"""One progress file per insight so parallel processes do not share a write."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


class JobProgress:
    def __init__(self, job_id: str, insight_id: str, root: Path) -> None:
        self.path = Path(root) / "jobs" / job_id / f"{insight_id}.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.insight_id = insight_id
        self.update("queued")

    def update(self, step: str, items_done: int | None = None, items_total: int | None = None, status: str = "running") -> None:
        _write(self.path, {
            "insight_id": self.insight_id,
            "status": status,
            "step": step,
            "items_done": items_done,
            "items_total": items_total,
            "updated_at": time.time(),
        })

    def finish(self, status: str, detail: str = "") -> None:
        current = {}
        if self.path.is_file():
            current = json.loads(self.path.read_text(encoding="utf-8"))
        current.update({"status": status, "step": detail or status, "finished_at": time.time()})
        _write(self.path, current)


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)
