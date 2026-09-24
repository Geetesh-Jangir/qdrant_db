"""LangGraph state for one daily run."""

from __future__ import annotations

from typing import TypedDict


class PipelineState(TypedDict):
    run_id: str
    started_at: str
    entities: list[dict]
    candidates: list[dict]
    counts: dict[str, int]
    errors: list[dict]


class PipelineState(PipelineState, total=False):
    step_timings_sec: dict[str, float]
    llm_usage: dict
    known_merges: list[dict]
    canonical_merges: list[dict]
