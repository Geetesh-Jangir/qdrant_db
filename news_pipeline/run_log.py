"""Per-run log file: step timings and cumulative Jev usage after each LLM call."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any

_active: "RunLogger | None" = None
_lock = threading.Lock()


def start_run_logger(run_id: str, log_path, input_cost_per_million: float) -> RunLogger:
    global _active
    logger = RunLogger(run_id, log_path, input_cost_per_million)
    with _lock:
        _active = logger
    logger.write(f"run started run_id={run_id}")
    return logger


def get_run_logger() -> RunLogger | None:
    return _active


def clip_log_text(text: str, limit: int = 240) -> str:
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def finish_run_logger() -> dict[str, Any] | None:
    global _active
    with _lock:
        logger = _active
        _active = None
    if logger is None:
        return None
    return logger.finish()


class RunLogger:
    def __init__(self, run_id: str, log_path, input_cost_per_million: float) -> None:
        self.run_id = run_id
        self.log_path = log_path
        self.input_cost_per_million = input_cost_per_million
        self.started_at = time.perf_counter()
        self.llm_calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.step_timings_sec: dict[str, float] = {}
        self._file_lock = threading.Lock()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("", encoding="utf-8")

    def write(self, message: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"{stamp} {message}\n"
        with self._file_lock:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line)

    def record_step(self, step: str, seconds: float) -> None:
        rounded = round(seconds, 3)
        self.step_timings_sec[step] = rounded
        cumulative = round(sum(self.step_timings_sec.values()), 3)
        self.write(f"step finished name={step} seconds={rounded} cumulative_steps_sec={cumulative}")

    def record_llm_call(
        self,
        *,
        stage: str,
        input_tokens: int,
        output_tokens: int,
        duration_sec: float,
        detail: str = "",
    ) -> None:
        self.llm_calls += 1
        self.input_tokens += max(0, input_tokens)
        self.output_tokens += max(0, output_tokens)
        call_cost = self._input_cost(input_tokens)
        total_cost = self._input_cost(self.input_tokens)
        extra = f" {detail}" if detail else ""
        self.write(
            "llm call "
            f"stage={stage}{extra} "
            f"input_tokens={input_tokens} output_tokens={output_tokens} "
            f"call_input_cost_usd={call_cost:.6f} "
            f"total_llm_calls={self.llm_calls} "
            f"total_input_tokens={self.input_tokens} "
            f"total_output_tokens={self.output_tokens} "
            f"total_input_cost_usd={total_cost:.6f} "
            f"duration_sec={round(duration_sec, 3)}"
        )

    def snapshot(self) -> dict[str, Any]:
        total_seconds = round(time.perf_counter() - self.started_at, 3)
        steps_total = round(sum(self.step_timings_sec.values()), 3)
        return {
            "log_file": str(self.log_path),
            "llm_calls": self.llm_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_cost_usd": round(self._input_cost(self.input_tokens), 6),
            "price_per_million_input_usd": self.input_cost_per_million,
            "step_timings_sec": dict(self.step_timings_sec),
            "steps_total_sec": steps_total,
            "total_seconds": total_seconds,
        }

    def finish(self) -> dict[str, Any]:
        snap = self.snapshot()
        self.write(
            "run finished "
            f"total_seconds={snap['total_seconds']} "
            f"steps_total_sec={snap['steps_total_sec']} "
            f"llm_calls={snap['llm_calls']} "
            f"input_tokens={snap['input_tokens']} "
            f"output_tokens={snap['output_tokens']} "
            f"total_input_cost_usd={snap['input_cost_usd']:.6f}"
        )
        return snap

    def _input_cost(self, input_tokens: int) -> float:
        return (input_tokens / 1_000_000) * self.input_cost_per_million
