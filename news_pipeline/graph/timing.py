"""Wrap graph nodes to record per-step wall time in the run log and pipeline state."""

from __future__ import annotations

import time
from collections.abc import Callable

from news_pipeline.graph.state import PipelineState
from news_pipeline.run_log import get_run_logger


def timed_node(name: str, fn: Callable[[PipelineState], dict]) -> Callable[[PipelineState], dict]:
    def wrapper(state: PipelineState) -> dict:
        run_log = get_run_logger()
        if run_log is not None:
            run_log.write(f"step started name={name}")
        started = time.perf_counter()
        result = fn(state)
        elapsed = time.perf_counter() - started
        run_log = get_run_logger()
        if run_log is not None:
            run_log.record_step(name, elapsed)
        step_timings = dict(state.get("step_timings_sec") or {})
        step_timings[name] = round(elapsed, 3)
        merged = {**result, "step_timings_sec": step_timings}
        usage = result.get("llm_usage")
        if usage is not None:
            merged["llm_usage"] = merge_llm_usage(state.get("llm_usage"), usage)
        elif state.get("llm_usage"):
            merged["llm_usage"] = dict(state.get("llm_usage") or {})
        return merged

    return wrapper


def merge_llm_usage(base: dict | None, patch: dict | None) -> dict:
    left = dict(base or {})
    right = dict(patch or {})
    calls = int(left.get("calls", 0)) + int(right.get("calls", 0))
    input_tokens = int(left.get("input_tokens", 0)) + int(right.get("input_tokens", 0))
    output_tokens = int(left.get("output_tokens", 0)) + int(right.get("output_tokens", 0))
    price = right.get("price_per_million_input_usd", left.get("price_per_million_input_usd", 0.042))
    cost = (input_tokens / 1_000_000) * float(price)
    return {
        "calls": calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_usd": round(cost, 6),
        "price_per_million_input_usd": float(price),
    }
