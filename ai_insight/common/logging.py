"""Per-run artifacts: a readable log, a JSONL log, and the files that explain a decision."""

from __future__ import annotations

import json
import os
import re
import time
import traceback
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
_current: ContextVar["RunArtifacts | None"] = ContextVar("insight_run_artifacts", default=None)

_SECRET = re.compile(
    r"(sk-ant-[A-Za-z0-9_\-]+|Bearer\s+[A-Za-z0-9._\-]+|api_key=[^&\s]+|api-key:\s*\S+)",
    re.I,
)


def current_artifacts() -> "RunArtifacts | None":
    return _current.get()


def log_external(**fields: Any) -> None:
    artifacts = current_artifacts()
    if artifacts is not None:
        artifacts.external_call(**fields)


class RunArtifacts:
    def __init__(
        self,
        insight_id: str,
        trading_date: str,
        run_id: str,
        root: Path,
        retention_days: int = 60,
    ) -> None:
        self.insight_id = insight_id
        self.trading_date = trading_date
        self.run_id = run_id
        self.root = Path(root)
        self.dir = self.root / trading_date / insight_id / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.dir / "run.log"
        self.jsonl_path = self.dir / "run.jsonl"
        self._step = "setup"
        self._decisions: list[str] = []
        self._llm_seq = 0
        self._ledger: list[dict[str, Any]] = []
        self._token = _current.set(self)
        self._extra_secrets = _env_secrets()
        prune_logs(self.root, retention_days)
        self.info("run started", step="setup")

    def close(self) -> None:
        _current.reset(self._token)

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        previous = self._step
        self._step = name
        started = time.perf_counter()
        self.info(f"--- {name} ---", step=name)
        try:
            yield
        except Exception as exc:
            self.error(
                f"{type(exc).__name__}: {exc}",
                step=name,
                inputs_summary=traceback.format_exc()[-2000:],
            )
            raise
        finally:
            elapsed = round((time.perf_counter() - started) * 1000, 1)
            self.info(f"step done {name}", step=name, duration_ms=elapsed)
            self._step = previous

    def info(self, message: str, **fields: Any) -> None:
        self._write("INFO", message, fields)

    def warning(self, message: str, **fields: Any) -> None:
        self._write("WARNING", message, fields)

    def error(self, message: str, **fields: Any) -> None:
        self._write("ERROR", message, fields)

    def decision(self, line: str) -> None:
        self._decisions.append(line)
        self.info(line, step="decision")

    def write_json(self, name: str, payload: Any) -> Path:
        path = self.dir / name
        path.write_text(
            json.dumps(_redact(payload, self._extra_secrets), ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return path

    def llm_call(
        self,
        kind: str,
        request: dict[str, Any],
        response: Any,
        usage: Any,
        latency_ms: float,
        retries: int,
        error: str = "",
        *,
        label: str = "",
        section: str = "",
        log_full_prompt: bool = False,
    ) -> int:
        self._llm_seq += 1
        seq = self._llm_seq
        use = _usage(usage)
        row = {
            "seq": seq,
            "section": section or self.insight_id,
            "label": label or kind,
            "kind": kind,
            "model": use.get("model", ""),
            "input_tokens": int(use.get("input_tokens") or 0),
            "output_tokens": int(use.get("output_tokens") or 0),
            "latency_ms": latency_ms,
            "retries": retries,
            "error": error,
        }
        self._ledger.append(row)
        ledger_path = self.dir / "llm_calls.jsonl"
        with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        if log_full_prompt:
            self.write_json(f"llm_{seq:03d}_{kind}_request.json", request)
            self.write_json(
                f"llm_{seq:03d}_{kind}_response.json",
                {"response": response, "usage": use, "error": error, "latency_ms": latency_ms, "retries": retries},
            )
        else:
            meta_req = {
                "kind": kind,
                "label": label,
                "model": request.get("model"),
                "max_tokens": request.get("max_tokens"),
                "user_chars": len(str(request.get("user") or "")),
                "system_chars": len(str(request.get("system") or "")),
            }
            self.write_json(f"llm_{seq:03d}_{kind}_request.json", meta_req)
            self.write_json(
                f"llm_{seq:03d}_{kind}_response.json",
                {
                    "usage": use,
                    "error": error,
                    "latency_ms": latency_ms,
                    "retries": retries,
                    "output_chars": len(str((response or {}).get("raw_text") or "")) if isinstance(response, dict) else 0,
                },
            )
        self.info(f"llm {kind}", step=f"llm_{kind}", duration_ms=latency_ms, retries=retries, error=error, seq=seq)
        return seq

    def external_call(
        self,
        service: str,
        url: str,
        status: Any,
        latency_ms: float,
        retries: int = 0,
        data_date: str = "",
        trading_date: str = "",
    ) -> None:
        self.info(
            f"external {service}",
            step="external",
            service=service,
            url=url,
            status=status,
            duration_ms=latency_ms,
            retries=retries,
            data_date=data_date,
            trading_date=trading_date,
            date_matched=bool(data_date) and data_date == (trading_date or self.trading_date),
        )

    def write_usage(self, summary: dict[str, Any]) -> None:
        by_kind: dict[str, dict[str, int]] = {}
        for row in self._ledger:
            kind = str(row.get("kind") or "unknown")
            bucket = by_kind.setdefault(kind, {"calls": 0, "input_tokens": 0, "output_tokens": 0})
            bucket["calls"] += 1
            bucket["input_tokens"] += int(row.get("input_tokens") or 0)
            bucket["output_tokens"] += int(row.get("output_tokens") or 0)
        payload = {
            "calls": len(self._ledger),
            "input_tokens": sum(int(row.get("input_tokens") or 0) for row in self._ledger),
            "output_tokens": sum(int(row.get("output_tokens") or 0) for row in self._ledger),
            "by_kind": by_kind,
            "calls_detail": list(self._ledger),
            **summary,
        }
        self.write_json("usage.json", payload)

    def write_manifest(self, extra: dict[str, Any]) -> None:
        payload = {
            "insight_id": self.insight_id,
            "trading_date": self.trading_date,
            "run_id": self.run_id,
            "run_dir": str(self.dir),
            **extra,
        }
        self.write_json("manifest.json", payload)

    def finalize(self, summary: dict[str, Any]) -> None:
        self.write_usage(summary)
        lines = [
            f"# {self.insight_id} {self.trading_date} {self.run_id}",
            "",
            *[f"- {line}" for line in self._decisions],
            "",
            "Summary: " + json.dumps(summary, default=str),
            "",
        ]
        (self.dir / "decision_trace.md").write_text("\n".join(lines), encoding="utf-8")
        text = (
            f"status={summary.get('status')} duration={summary.get('duration_sec')} "
            f"llm_calls={summary.get('llm_calls')} tokens_in={summary.get('tokens_in')} "
            f"tokens_out={summary.get('tokens_out')} sources={summary.get('sources')} "
            f"validation={summary.get('validation')} freshness={summary.get('freshness')}"
        )
        self.info(text, step="summary", duration_ms=float(summary.get("duration_ms") or 0))

    def _write(self, level: str, message: str, fields: dict[str, Any]) -> None:
        now = datetime.now(IST)
        step = str(fields.pop("step", None) or self._step)
        duration = fields.pop("duration_ms", None)
        safe_message = _redact_text(message, self._extra_secrets)
        safe_fields = _redact(fields, self._extra_secrets)
        clock = now.strftime("%Y-%m-%dT%H:%M:%S+05:30")
        extra = " ".join(f"{key}={value}" for key, value in safe_fields.items())
        line = f"{clock} {level:<7} {step:<16} {safe_message}"
        if extra:
            line += " | " + extra
        if duration is not None:
            line += f" | duration_ms={duration}"
        with self.log_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
        record = {
            "run_id": self.run_id,
            "insight_id": self.insight_id,
            "trading_date": self.trading_date,
            "step": step,
            "level": level,
            "ts_ist": clock,
            "duration_ms": duration,
            "message": safe_message,
            **{key: value for key, value in safe_fields.items()},
        }
        with self.jsonl_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def prune_logs(root: Path, keep_days: int) -> None:
    if keep_days < 1 or not root.is_dir():
        return
    cutoff = (datetime.now(IST) - timedelta(days=keep_days)).date()
    for child in root.iterdir():
        if not child.is_dir() or len(child.name) != 10:
            continue
        try:
            day = datetime.strptime(child.name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if day < cutoff:
            _rmtree(child)


def _rmtree(path: Path) -> None:
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink(missing_ok=True)
        elif child.is_dir():
            child.rmdir()
    path.rmdir()


def _env_secrets() -> list[str]:
    found: list[str] = []
    for key, value in os.environ.items():
        if any(part in key.upper() for part in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
            text = str(value or "").strip()
            if len(text) >= 8:
                found.append(text)
    return found


def _redact(value: Any, secrets: list[str]) -> Any:
    if isinstance(value, str):
        return _redact_text(value, secrets)
    if isinstance(value, dict):
        return {str(key): _redact(item, secrets) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, secrets) for item in value]
    return value


def _redact_text(text: str, secrets: list[str]) -> str:
    cleaned = _SECRET.sub("[redacted]", text)
    for secret in secrets:
        if secret and secret in cleaned:
            cleaned = cleaned.replace(secret, "[redacted]")
    return cleaned


def _usage(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    if isinstance(usage, dict):
        return usage
    return {
        "provider": getattr(usage, "provider", ""),
        "model": getattr(usage, "model", ""),
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
        "attempts": getattr(usage, "attempts", 0),
        "retries": getattr(usage, "retries", 0),
    }
