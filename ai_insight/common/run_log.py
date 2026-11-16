"""One readable log per insight run, plus a single-line history in runs.log."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

_LEGEND = (
    "HOW TO READ THIS LOG: lines here are a short timeline. "
    "Look for TRACE_DIR for the full run folder (run.log, run.jsonl, decision_trace.md, retrieval/LLM JSON). "
    "STEP lines are major stages. PASS/FAIL are prose checks. "
    "RUN_SUMMARY is the outcome. "
    "Prompts live in the .prompt.txt file beside this log when verbose, dry, degraded, or failed."
)


class RunLog:
    def __init__(
        self,
        *,
        insight_id: str,
        trading_date: str,
        run_id: str,
        log_dir: Path,
        verbose: bool = False,
    ) -> None:
        self.insight_id = insight_id
        self.trading_date = trading_date
        self.run_id = run_id
        self.verbose = verbose
        stamp = datetime.now(IST).strftime("%Y-%m-%d_%H%M%S")
        folder = Path(log_dir) / insight_id
        folder.mkdir(parents=True, exist_ok=True)
        self.path = folder / f"{stamp}_{run_id}.log"
        self.prompt_path = self.path.with_suffix(".prompt.txt")
        self._runs = Path(log_dir) / "runs.log"
        _write(self.path, _LEGEND + "\n")

    def line(self, tag: str, message: str) -> None:
        _append(self.path, f"{_clock()} {tag:<12} {message}\n")

    def warning(self, message: str) -> None:
        self.line("WARNING", message)

    def step(self, number: int, total: int, name: str, message: str) -> None:
        self.line(f"STEP {number}/{total}", f"{name:<12} {message}")

    def prompt(self, text: str) -> None:
        _append(self.prompt_path, text.rstrip() + "\n\n")

    def summary(
        self,
        *,
        status: str,
        duration_sec: float,
        tokens: int,
        source_count: int,
        saved_path: str = "",
    ) -> None:
        text = (
            f"status={status} insight={self.insight_id} date={self.trading_date} "
            f"duration={duration_sec:.1f}s tokens={tokens} sources={source_count} "
            f"log={self.path}"
        )
        if saved_path:
            text += f" file={saved_path}"
        self.line("RUN_SUMMARY", text)
        self._runs.parent.mkdir(parents=True, exist_ok=True)
        _append(self._runs, f"{_clock()} {text}\n")


def _clock() -> str:
    return datetime.now(IST).strftime("%Y-%m-%dT%H:%M:%S+05:30")


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _append(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
