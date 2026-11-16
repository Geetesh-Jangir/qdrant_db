"""Facts models and the JSON schema the theme model must match."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ai_insight.common.schemas import SectorLeaderboardFactsBase

INSIGHT_ID = "sector_leaderboard"


class StoryScore(BaseModel):
    cluster_id: str
    title: str
    url: str
    source: str
    published_at: str
    text: str
    weight: float
    magnitude: float
    sign: int
    direction: str


class SectorScore(BaseModel):
    name: str
    display: str
    score: float
    n_stories: int
    stories: list[StoryScore] = Field(default_factory=list)


class Themes(BaseModel):
    best_theme: str = ""
    worst_theme: str = ""
    cited_cluster_ids: list[str] = Field(default_factory=list)


class SectorFacts(SectorLeaderboardFactsBase):
    sectors_with_news: int = 0
    eligible_count: int = 0
    ranking: list[dict[str, Any]] = Field(default_factory=list)
    evidence: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    gate: dict[str, Any] = Field(default_factory=dict)


def llm_schema(best_ids: list[str], worst_ids: list[str], sides: set[str]) -> dict[str, Any]:
    """Only the sides that exist are required. Cited ids must be from the evidence."""
    properties: dict[str, Any] = {}
    required: list[str] = ["cited_cluster_ids"]
    if "best" in sides:
        properties["best_theme"] = {"type": "string", "minLength": 1, "maxLength": 160}
        required.append("best_theme")
    if "worst" in sides:
        properties["worst_theme"] = {"type": "string", "minLength": 1, "maxLength": 160}
        required.append("worst_theme")
    allowed = list(dict.fromkeys([*best_ids, *worst_ids]))
    properties["cited_cluster_ids"] = {
        "type": "array",
        "items": {"type": "string", "enum": allowed},
        "minItems": 1,
        "maxItems": 4,
        "uniqueItems": True,
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": required,
    }
