"""One historical news backfill at a time, with a live log the web page can poll."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from collections import deque
from datetime import datetime, timezone
from news_pipeline.config import repo_root
from news_pipeline.news_dates import NewsDateRangeError, iter_inclusive_days, parse_one_date

_MAX_LOG_LINES = 800
_lock = threading.Lock()
_proc: subprocess.Popen | None = None
_log: deque[str] = deque(maxlen=_MAX_LOG_LINES)
_status = "idle"
_params: dict | None = None
_started_at: str | None = None
_finished_at: str | None = None
_returncode: int | None = None


def _append(line: str) -> None:
    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    _log.append(f"{stamp}  {line.rstrip()}")


def snapshot() -> dict:
    with _lock:
        return {
            "status": _status,
            "params": _params,
            "started_at": _started_at,
            "finished_at": _finished_at,
            "returncode": _returncode,
            "log": list(_log),
        }


def _reader(proc: subprocess.Popen) -> None:
    global _status, _finished_at, _returncode, _proc
    assert proc.stdout is not None
    for raw in proc.stdout:
        with _lock:
            _append(raw)
    code = proc.wait()
    with _lock:
        _returncode = code
        _finished_at = datetime.now(timezone.utc).isoformat()
        if _status == "stopping":
            _status = "stopped"
            _append("backfill stopped")
        elif code == 0:
            _status = "done"
            _append("backfill finished successfully")
        else:
            _status = "failed"
            _append(f"backfill exited with code {code}")
        if _proc is proc:
            _proc = None


def start(
    *,
    start_date: str,
    end_date: str,
    holdings: int,
    sectors: int,
    pause_sec: int,
) -> dict:
    global _proc, _status, _params, _started_at, _finished_at, _returncode
    try:
        start_d = parse_one_date(start_date)
        end_d = parse_one_date(end_date)
        days = iter_inclusive_days(start_d, end_d)
    except NewsDateRangeError as exc:
        raise ValueError(str(exc)) from exc
    if holdings < 1 or holdings > 2000:
        raise ValueError("holdings must be between 1 and 2000")
    if sectors < 0 or sectors > 80:
        raise ValueError("sectors must be between 0 and 80")
    if pause_sec < 0 or pause_sec > 86400:
        raise ValueError("pause must be between 0 and 86400 seconds")

    root = repo_root()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root)
    env["PYTHONUNBUFFERED"] = "1"
    env["BACKFILL_START"] = start_d.strftime("%d/%m/%Y")
    env["BACKFILL_END"] = end_d.strftime("%d/%m/%Y")
    env["BACKFILL_PAUSE_SEC"] = str(pause_sec)
    env["HOLDINGS_LIMIT"] = str(holdings)
    env["SECTORS_LIMIT"] = str(sectors)
    env["NEWS_CORPUS_MODE"] = "true"
    env["RETENTION_DAYS"] = "0"
    env["FRESH_START_EACH_RUN"] = "false"
    env["FRESH_START_CLEAR_QDRANT"] = "false"

    with _lock:
        if _proc is not None and _proc.poll() is None:
            raise RuntimeError("a backfill is already running")
        _log.clear()
        _params = {
            "start": start_d.isoformat(),
            "end": end_d.isoformat(),
            "days": len(days),
            "holdings": holdings,
            "sectors": sectors,
            "pause_sec": pause_sec,
        }
        _started_at = datetime.now(timezone.utc).isoformat()
        _finished_at = None
        _returncode = None
        _status = "running"
        _append(
            f"starting {len(days)} day(s) {start_d.isoformat()} through {end_d.isoformat()} "
            f"holdings={holdings} sectors={sectors} pause={pause_sec}s"
        )
        proc = subprocess.Popen(
            [sys.executable, "-u", "-m", "news_pipeline.backfill_days"],
            cwd=str(root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=os.name != "nt",
        )
        _proc = proc
        threading.Thread(target=_reader, args=(proc,), name="backfill-log", daemon=True).start()
    return snapshot()


def stop() -> dict:
    global _status
    with _lock:
        proc = _proc
        if proc is None or proc.poll() is not None:
            return snapshot()
        _status = "stopping"
        _append("stop requested")
        pid = proc.pid
    if os.name != "nt":
        import signal

        try:
            os.killpg(pid, signal.SIGTERM)
        except OSError:
            proc.terminate()
    else:
        proc.terminate()
    return snapshot()

