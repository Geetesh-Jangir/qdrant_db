"""Per-run metadata for ledgers and stats."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RunContext:
    run_id: str = ""
    calendar_day: str = ""
    news_date_range: str = ""


_CONTEXT = RunContext()


def set_run_context(run_id: str, calendar_day: str, news_date_range: str) -> None:
    global _CONTEXT
    _CONTEXT = RunContext(
        run_id=run_id,
        calendar_day=calendar_day,
        news_date_range=news_date_range,
    )


def get_run_context() -> RunContext:
    return _CONTEXT
