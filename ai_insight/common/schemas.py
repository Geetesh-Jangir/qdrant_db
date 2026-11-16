"""Shared insight envelope and the facts base each insight extends."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Status = Literal["ok", "degraded", "skipped", "failed"]
Prominence = Literal["normal", "high"]
Tone = Literal["positive", "negative", "neutral"]
VizType = Literal["diverging_bars", "flow_bars", "index_move", "trend_line", "ohlc_week", "none"]
RunMode = Literal["scheduled", "live"]
MarketPhase = Literal["open", "closed", ""]


class Chip(BaseModel):
    label: str
    value: str
    tone: Tone = "neutral"


class Source(BaseModel):
    title: str = ""
    url: str = ""
    source: str = ""
    published_at: str = ""


class Viz(BaseModel):
    type: VizType = "index_move"
    data: dict[str, Any] = Field(default_factory=dict)


class UsageMeta(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    attempts: int = 0


class Meta(BaseModel):
    model: str = ""
    prompt_version: str = "v1"
    window_utc: list[str] = Field(default_factory=list)
    cluster_ids: list[str] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)
    run_id: str = ""
    usage: UsageMeta = Field(default_factory=UsageMeta)
    freshness: str = ""
    freshness_warning: str = ""
    llm_calls: list[dict[str, Any]] = Field(default_factory=list)
    trend_coverage: dict[str, Any] = Field(default_factory=dict)
    run_mode: RunMode = "scheduled"
    market_phase: MarketPhase = ""


class Envelope(BaseModel):
    insight_id: str
    trading_date: str
    as_of_ist: str
    status: Status
    skip_reason: str | None = None
    prominence: Prominence = "normal"
    headline: str = ""
    body: str = ""
    chips: list[Chip] = Field(default_factory=list)
    viz: Viz = Field(default_factory=Viz)
    sources: list[Source] = Field(default_factory=list)
    facts: dict[str, Any] = Field(default_factory=dict)
    meta: Meta = Field(default_factory=Meta)

    @field_validator("trading_date")
    @classmethod
    def _date(cls, value: str) -> str:
        if len(value) != 10 or value[4] != "-" or value[7] != "-":
            raise ValueError("trading_date must be YYYY-MM-DD")
        return value

    @field_validator("as_of_ist")
    @classmethod
    def _ist_offset(cls, value: str) -> str:
        if "+05:30" not in value:
            raise ValueError("as_of_ist must include the +05:30 offset")
        return value

    @field_validator("insight_id")
    @classmethod
    def _insight_id(cls, value: str) -> str:
        if not value or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_" for ch in value):
            raise ValueError("insight_id must be lowercase letters, digits, or underscore")
        return value

    @model_validator(mode="after")
    def _skipped_needs_reason(self) -> Envelope:
        if self.status == "skipped" and not (self.skip_reason or "").strip():
            raise ValueError("skipped insights need a skip_reason")
        return self


def numeric_leaves(node: Any, path: str = "") -> list[tuple[str, float]]:
    """Signed numbers stored in facts, ignoring bools."""
    found: list[tuple[str, float]] = []

    def walk(value: Any, here: str) -> None:
        if isinstance(value, bool):
            return
        if isinstance(value, (int, float)):
            found.append((here, float(value)))
            return
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{here}.{key}" if here else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{here}[{index}]")

    walk(node, path)
    return found


class InsightBundle(BaseModel):
    """Several insights produced by one module, for example one card per sector index."""

    insight_id: str
    trading_date: str
    as_of_ist: str
    status: Status
    items: list[Envelope] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
    skip_reason: str | None = None

    @field_validator("trading_date")
    @classmethod
    def _bundle_date(cls, value: str) -> str:
        if len(value) != 10 or value[4] != "-" or value[7] != "-":
            raise ValueError("trading_date must be YYYY-MM-DD")
        return value


class FactsBase(BaseModel):
    trading_date: str
    window_utc: list[str] = Field(default_factory=list)

    def numeric_leaves(self) -> list[tuple[str, float]]:
        return numeric_leaves(self.model_dump())


class MarketDriverFactsBase(FactsBase):
    nifty_close: float | None = None
    nifty_change_pct: float | None = None
    top_theme: str = ""
    fii_net_crore: float | None = None
    dii_net_crore: float | None = None


class FiiDiiFactsBase(FactsBase):
    fii_net_crore: float | None = None
    dii_net_crore: float | None = None
    fii_streak_days: int | None = None
    dii_streak_days: int | None = None


class SectorLeaderboardFactsBase(FactsBase):
    positive_sector: str = ""
    negative_sector: str = ""
    positive_score: float | None = None
    negative_score: float | None = None
