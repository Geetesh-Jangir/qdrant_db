"""Sector index insight schema."""

from __future__ import annotations

from typing import Any

INSIGHT_ID = "sector_index_insights"
PROMPT_VERSION = "v1"

DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["headline", "body", "direction", "driver_cluster_ids", "explanation_confidence", "reason_unclear", "implication"],
    "properties": {
        "headline": {"type": "string"},
        "body": {"type": "string"},
        "direction": {"type": "string"},
        "driver_cluster_ids": {"type": "array", "items": {"type": "string"}},
        "explanation_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reason_unclear": {"type": "boolean"},
        "implication": {"type": ["string", "null"]},
        "observations": {"type": "array", "items": {"type": "string"}},
    },
}
