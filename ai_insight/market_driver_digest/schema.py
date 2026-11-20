"""Market driver digest schema."""

from __future__ import annotations

from typing import Any

INSIGHT_ID = "market_driver_digest"
PROMPT_VERSION = "v9"
INDEX_ENTITIES = {"Macro - Nifty 50", "Macro - Sensex", "Macro - Bank Nifty"}

# JSON field order → assembled body paragraphs (Market Today only).
MARKET_INSIGHT_SECTIONS: tuple[str, ...] = (
    "market_snapshot",
    "what_happened",
    "why_may_have_happened",
    "impacted_how",
    "investor_relevance",
    "what_to_watch",
)

_SECTION_PROPERTIES: dict[str, Any] = {key: {"type": "string"} for key in MARKET_INSIGHT_SECTIONS}

DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "headline",
        *MARKET_INSIGHT_SECTIONS,
        "cited_cluster_ids",
        "confidence",
    ],
    "properties": {
        "headline": {"type": "string"},
        **_SECTION_PROPERTIES,
        "cited_cluster_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "observations": {"type": "array", "items": {"type": "string"}},
    },
}