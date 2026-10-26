"""Telemetry collector for the ask pipeline.

Normalizes LLM usage from any provider (Anthropic, Gemini, DeepSeek) into
a common format and tracks phase/tool timing for SSE events.
"""

from __future__ import annotations

import json
import time
from typing import Any

from news_rag.insight.contracts import (
    LLMUsageRecord,
    RequestTelemetry,
)


def new_telemetry() -> RequestTelemetry:
    """Create a fresh telemetry instance for one ask request."""
    return RequestTelemetry()


def normalize_llm_usage(
    raw_usage: dict[str, Any] | None,
    *,
    provider: str = "",
    model: str = "",
    stage: str = "",
    total_ms: float = 0.0,
    ttft_ms: float | None = None,
) -> LLMUsageRecord:
    """Normalize usage dicts from different LLM providers into a common shape.

    Handles Anthropic (input_tokens, output_tokens, cache_read_input_tokens),
    Gemini (promptTokenCount, candidatesTokenCount, cachedContentTokenCount),
    and DeepSeek / OpenAI-compatible (prompt_tokens, completion_tokens).
    """
    u = raw_usage or {}

    # --- input tokens ---
    input_tokens = (
        u.get("input_tokens")              # Anthropic
        or u.get("prompt_tokens")           # OpenAI / DeepSeek
        or u.get("promptTokenCount")        # Gemini
        or 0
    )

    # --- output tokens ---
    output_tokens = (
        u.get("output_tokens")             # Anthropic
        or u.get("completion_tokens")       # OpenAI / DeepSeek
        or u.get("candidatesTokenCount")    # Gemini
        or 0
    )

    # --- cached input ---
    cached = (
        u.get("cache_read_input_tokens")    # Anthropic
        or u.get("cachedContentTokenCount") # Gemini
        or u.get("cached_tokens")           # generic
    )
    cached_input = int(cached) if cached is not None else None

    uncached = None
    if cached_input is not None:
        uncached = max(0, int(input_tokens) - cached_input)

    # source: did the API return usage or did we estimate?
    usage_source = "api" if u else "estimated"

    return LLMUsageRecord(
        stage=stage,
        provider=provider,
        model=model,
        input_tokens=int(input_tokens),
        output_tokens=int(output_tokens),
        cached_input_tokens=cached_input,
        uncached_input_tokens=uncached,
        ttft_ms=ttft_ms,
        total_ms=total_ms,
        usage_source=usage_source,
    )


def sse_event(
    event: str,
    data: dict[str, Any],
    telemetry: RequestTelemetry,
) -> str:
    """Format one SSE event line with request_id, trace_id, seq."""
    payload = {
        "request_id": telemetry.request_id,
        "trace_id": telemetry.trace_id,
        "seq": telemetry.next_seq(),
        **data,
    }
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


# Convenience event builders
def event_request_started(telemetry: RequestTelemetry, question: str) -> str:
    return sse_event("request_started", {"question": question[:500]}, telemetry)


def event_phase_started(telemetry: RequestTelemetry, phase: str) -> str:
    telemetry.start_phase(phase)
    return sse_event("phase_started", {"phase": phase}, telemetry)


def event_phase_completed(
    telemetry: RequestTelemetry, phase: str, **detail: Any
) -> str:
    telemetry.end_phase(phase, **detail)
    rec = next((p for p in reversed(telemetry.phases) if p.name == phase), None)
    d: dict[str, Any] = {"phase": phase}
    if rec:
        d["duration_ms"] = rec.duration_ms
    d.update(detail)
    return sse_event("phase_completed", d, telemetry)


def event_tool_started(telemetry: RequestTelemetry, tool: str, wave: int = 1) -> str:
    return sse_event("tool_started", {"tool": tool, "wave": wave}, telemetry)


def event_tool_completed(
    telemetry: RequestTelemetry,
    tool: str,
    *,
    wave: int = 1,
    ok: bool = True,
    duration_ms: float = 0.0,
    fund: str = "",
) -> str:
    telemetry.add_tool(tool, wave=wave, ok=ok, duration_ms=duration_ms, fund=fund)
    return sse_event("tool_completed", {
        "tool": tool, "wave": wave, "ok": ok, "duration_ms": duration_ms,
    }, telemetry)


def event_answer_delta(telemetry: RequestTelemetry, text: str) -> str:
    if telemetry.answer_ttft_ms is None:
        telemetry.answer_ttft_ms = round(
            (time.time() - telemetry.started_at) * 1000, 1
        )
    return sse_event("answer_delta", {"text": text}, telemetry)


def event_quality_check(
    telemetry: RequestTelemetry, state: str, **detail: Any
) -> str:
    telemetry.quality_state = state
    return sse_event("quality_check", {"state": state, **detail}, telemetry)


def event_fallback(telemetry: RequestTelemetry, reason: str) -> str:
    telemetry.fallback_used = True
    return sse_event("fallback", {"reason": reason}, telemetry)


def event_answer_completed(
    telemetry: RequestTelemetry, answer: str, result: dict[str, Any]
) -> str:
    telemetry.finalize()
    payload = {
        **result,
        "telemetry": telemetry.to_sse_telemetry(),
    }
    return f"event: done\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def event_request_failed(telemetry: RequestTelemetry, error: str) -> str:
    telemetry.finalize()
    telemetry.quality_state = "error"
    return sse_event("request_failed", {"error": error[:500]}, telemetry)
