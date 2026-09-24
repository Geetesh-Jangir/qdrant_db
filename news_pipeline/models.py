"""Payload written to Qdrant. One point per canonical URL."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EntityScore(BaseModel):
    name: str
    type: Literal["holding", "sector"]
    industry: str = ""
    title_relevance: float
    about_this_name: float
    relevance: int = Field(ge=0, le=4)
    impact: int = Field(ge=0, le=3)
    direction: Literal["positive", "negative", "neutral", "unclear"]
    event_type: Literal[
        "results",
        "order",
        "deal",
        "regulatory",
        "operations",
        "macro",
        "opinion",
        "price_recap",
    ]
    affects_stock: float
    affects_sector: float
    affects_macro: float


class StoredArticle(BaseModel):
    url: str
    title: str
    source: str
    scraped_text: str
    published_at: str
    scraped_at: str
    entity_names: list[str]
    industry_names: list[str] = Field(default_factory=list)
    primary_industry: str = ""
    holding_names: list[str] = Field(default_factory=list)
    sector_names: list[str] = Field(default_factory=list)
    entities: list[EntityScore]
    max_relevance: int
    max_impact: int
    direction: str
    event_type: str
