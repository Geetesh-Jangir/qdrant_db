"""Shared data contracts for the ask pipeline.

ExecutionPlan — what the slot router or planner produces.
EvidencePack  — joined evidence the composer reads.
RequestTelemetry — timing / usage records for SSE + logs.
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AnswerMode(str, Enum):
    DATA_ONLY = "DATA_ONLY"
    NEWS_ONLY = "NEWS_ONLY"
    INSIGHT_FUSION = "INSIGHT_FUSION"


class ScopeKind(str, Enum):
    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    NEEDS_CLARIFICATION = "needs_clarification"


class QueryClass(str, Enum):
    SIMPLE = "simple"
    STANDARD = "standard"
    COMPLEX = "complex"


# ---------------------------------------------------------------------------
# ExecutionPlan
# ---------------------------------------------------------------------------

class ToolCall(BaseModel):
    """One capability invocation in a wave."""
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    wave: int = 1            # 1 or 2
    required: bool = True
    why: str = ""


class Wave2Policy(BaseModel):
    """Deterministic rules for whether Wave 2 fires."""
    trigger: str = "none"        # none | negative_return | material_sector | always
    threshold: float | None = None
    max_calls: int = 1


class ExecutionPlan(BaseModel):
    """Output of the slot router or structured planner."""
    # Intake
    guardrail_passed: bool = True
    can_answer_directly: bool = False
    direct_reply: str = ""
    scope_kind: ScopeKind = ScopeKind.IN_SCOPE

    # Understanding
    intent: str = "lookup"
    goal: str = ""
    answer_mode: AnswerMode = AnswerMode.DATA_ONLY
    query_class: QueryClass = QueryClass.STANDARD

    # Entities (resolved)
    entities: list[dict[str, Any]] = Field(default_factory=list)
    funds: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    stocks: list[str] = Field(default_factory=list)
    drivers: list[dict[str, str]] = Field(default_factory=list)
    random_fund_count: int = 0
    random_fund_name_contains: str = ""

    # Time
    time_range: dict[str, Any] = Field(default_factory=dict)
    window_days: int = 30
    window_label: str = "1 month"

    # Tool calls grouped by wave
    tool_calls: list[ToolCall] = Field(default_factory=list)
    wave_2_policy: Wave2Policy = Field(default_factory=Wave2Policy)

    # Presentation
    response_shape: str = "sections"  # short_answer | bullets | paragraph | table | sections
    max_words: int = 220
    lead_with: str = ""
    presentation_notes: str = ""
    asked_facts: list[str] = Field(default_factory=list)
    concept_brief: str = ""
    requires_compose: bool = False
    asks_for_advice: bool = False
    asks_not_supported: list[str] = Field(default_factory=list)
    sub_queries: list[dict[str, Any]] = Field(default_factory=list)
    reasoning_depth: str = "standard"  # quick | standard | deep

    # Routing metadata
    routed_by: str = ""     # "slot_router" or "planner"
    confidence: float = 1.0
    # Planner's own reading of the question (count + portfolio slice). Not regex.
    planner_count: int = 0
    planner_portfolio_slice: str = ""

    @property
    def wave1_calls(self) -> list[ToolCall]:
        return [c for c in self.tool_calls if c.wave == 1]

    @property
    def wave2_calls(self) -> list[ToolCall]:
        return [c for c in self.tool_calls if c.wave == 2]

    @property
    def tool_names(self) -> list[str]:
        return [c.tool for c in self.tool_calls]

    @property
    def answer_style(self) -> str:
        return self.response_shape

    @property
    def direction(self) -> str:
        return "any"

    @property
    def layer1(self) -> list[dict[str, Any]]:
        return [{"tool": c.tool, "args": c.arguments, "required": c.required, "why": c.why} for c in self.wave1_calls]

    @property
    def layer2_news(self) -> dict[str, Any]:
        w2_news = next((c for c in self.wave2_calls if c.tool == "search_financial_news"), None)
        if w2_news:
            return {"needed": True, "depth": "detailed", "targets": [w2_news.arguments.get("scope", "holdings")]}
        return {"needed": False, "depth": "none", "targets": []}

    def summary(self) -> dict[str, Any]:
        return {
            "scope": self.scope_kind.value,
            "intent": self.intent,
            "answer_mode": self.answer_mode.value,
            "query_class": self.query_class.value,
            "funds": self.funds,
            "sectors": self.sectors,
            "stocks": self.stocks,
            "drivers": self.drivers,
            "window_days": self.window_days,
            "tools": self.tool_names,
            "wave1": [c.tool for c in self.wave1_calls],
            "wave2": [c.tool for c in self.wave2_calls],
            "wave2_policy": self.wave_2_policy.trigger,
            "routed_by": self.routed_by,
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------
# EvidencePack
# ---------------------------------------------------------------------------

class EvidenceRow(BaseModel):
    """One piece of evidence joined by canonical entity id."""
    entity_id: str = ""
    entity_type: str = ""   # fund | sector | stock | index | macro
    entity_name: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    news_summaries: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class EvidencePack(BaseModel):
    """Joined evidence the composer reads — one EVIDENCE block instead of parallel DATA/NEWS."""
    rows: list[EvidenceRow] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    token_budget: int = 12000
    data_pack: dict[str, Any] = Field(default_factory=dict)
    news_grouped: dict[str, Any] = Field(default_factory=dict)
    performance_digest: dict[str, Any] = Field(default_factory=dict)
    display_tables: dict[str, str] = Field(default_factory=dict)
    display_table_policy: dict[str, Any] = Field(default_factory=dict)
    coverage: dict[str, Any] = Field(default_factory=dict)
    missing: list[str] = Field(default_factory=list)

    def compact(self) -> dict[str, Any]:
        """Serialise for the composer prompt, respecting the token budget."""
        import json

        from news_rag.insight.pack_sanitize import (
            merge_holding_pp_into_performance,
            sanitize_data_pack_for_composer,
        )
        from news_rag.insight.pack_trim import trim_news_grouped

        data_pack, pp_internal = sanitize_data_pack_for_composer(self.data_pack)
        performance = merge_holding_pp_into_performance(self.performance_digest, pp_internal)

        out: dict[str, Any] = {}
        if performance:
            out["PERFORMANCE"] = performance
        if self.display_tables:
            out["DISPLAY"] = self.display_tables
        if data_pack:
            out["DATA"] = data_pack
        news = self.news_grouped
        if news:
            out["NEWS"] = news
        if self.missing:
            out["MISSING"] = self.missing
        if self.coverage:
            out["COVERAGE"] = self.coverage
        if self.limitations:
            out["LIMITATIONS"] = self.limitations
        text = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
        budget_chars = self.token_budget * 4
        if len(text) > budget_chars and "NEWS" in out:
            for cap in (18, 12, 8):
                out["NEWS"] = trim_news_grouped(news, max_articles=cap)
                text = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
                if len(text) <= budget_chars:
                    break
            if len(text) > budget_chars:
                out["NEWS"] = trim_news_grouped(news, max_articles=6)
        return out


# ---------------------------------------------------------------------------
# RequestTelemetry
# ---------------------------------------------------------------------------

class PhaseRecord(BaseModel):
    """Timing for one pipeline phase."""
    name: str
    started_at: float = 0.0
    ended_at: float = 0.0
    duration_ms: float = 0.0
    status: str = "pending"   # pending | running | done | error | skipped
    detail: dict[str, Any] = Field(default_factory=dict)


class ToolRecord(BaseModel):
    """One tool invocation record."""
    tool: str
    wave: int = 1
    ok: bool = True
    duration_ms: float = 0.0
    error: str = ""
    fund: str = ""
    result_count: int = 0


class LLMUsageRecord(BaseModel):
    """Normalized LLM usage from any provider."""
    stage: str = ""         # plan | compose | judge | slot_router
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int | None = None
    uncached_input_tokens: int | None = None
    ttft_ms: float | None = None   # time to first token
    total_ms: float = 0.0
    usage_source: str = ""   # "api" | "estimated"


class RequestTelemetry(BaseModel):
    """Complete telemetry for one ask request."""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    seq: int = 0
    started_at: float = Field(default_factory=time.time)
    ended_at: float = 0.0

    # Phases
    phases: list[PhaseRecord] = Field(default_factory=list)
    tools: list[ToolRecord] = Field(default_factory=list)
    llm_usage: list[LLMUsageRecord] = Field(default_factory=list)

    # Summary fields for the done event
    wall_ms: float = 0.0
    answer_ttft_ms: float | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cached_input_tokens: int = 0
    tool_count: int = 0
    quality_state: str = ""   # passed | failed | skipped
    fallback_used: bool = False
    routed_by: str = ""
    answer_mode: str = ""

    def next_seq(self) -> int:
        self.seq += 1
        return self.seq

    def start_phase(self, name: str) -> PhaseRecord:
        record = PhaseRecord(name=name, started_at=time.time(), status="running")
        self.phases.append(record)
        return record

    def end_phase(self, name: str, *, status: str = "done", **detail: Any) -> None:
        for rec in reversed(self.phases):
            if rec.name == name and rec.status == "running":
                rec.ended_at = time.time()
                rec.duration_ms = round((rec.ended_at - rec.started_at) * 1000, 1)
                rec.status = status
                rec.detail.update(detail)
                return

    def add_tool(self, tool: str, *, wave: int = 1, ok: bool = True,
                 duration_ms: float = 0.0, error: str = "", fund: str = "",
                 result_count: int = 0) -> None:
        for t in self.tools:
            if t.tool == tool and t.wave == wave and t.fund == fund:
                t.ok = ok
                if duration_ms > 0:
                    t.duration_ms = duration_ms
                if error:
                    t.error = error
                return
        self.tools.append(ToolRecord(
            tool=tool, wave=wave, ok=ok, duration_ms=duration_ms,
            error=error, fund=fund, result_count=result_count,
        ))
        self.tool_count = len(self.tools)

    def add_llm_usage(self, **kwargs: Any) -> None:
        self.llm_usage.append(LLMUsageRecord(**kwargs))

    def finalize(self) -> None:
        self.ended_at = time.time()
        self.wall_ms = round((self.ended_at - self.started_at) * 1000, 1)
        self.total_input_tokens = sum(u.input_tokens for u in self.llm_usage)
        self.total_output_tokens = sum(u.output_tokens for u in self.llm_usage)
        self.cached_input_tokens = sum(
            u.cached_input_tokens or 0 for u in self.llm_usage
        )
        self.tool_count = len(self.tools)

    def to_sse_telemetry(self) -> dict[str, Any]:
        """Compact telemetry for the SSE done event."""
        return {
            "request_id": self.request_id,
            "wall_ms": self.wall_ms,
            "answer_ttft_ms": self.answer_ttft_ms,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "cached_input_tokens": self.cached_input_tokens,
            "prompt_cached": bool(self.cached_input_tokens and self.cached_input_tokens > 0),
            "tool_count": self.tool_count,
            "quality_state": self.quality_state,
            "fallback_used": self.fallback_used,
            "routed_by": self.routed_by,
            "answer_mode": self.answer_mode,
            "phases": [
                {"name": p.name, "duration_ms": p.duration_ms, "status": p.status}
                for p in self.phases
            ],
            "tools": [
                {"tool": t.tool, "wave": t.wave, "ok": t.ok, "duration_ms": t.duration_ms}
                for t in self.tools
            ],
        }
