"""Market driver digest schema."""

from __future__ import annotations

from typing import Any

INSIGHT_ID = "market_driver_digest"
PROMPT_VERSION = "v1"
INDEX_ENTITIES = {"Macro - Nifty 50", "Macro - Sensex", "Macro - Bank Nifty"}

DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["headline", "body", "primary_driver", "secondary_driver", "implication", "cited_cluster_ids", "confidence"],
    "properties": {
        "headline": {"type": "string"},
        "body": {"type": "string"},
        "primary_driver": {"type": "string"},
        "secondary_driver": {"type": ["string", "null"]},
        "implication": {"type": ["string", "null"]},
        "cited_cluster_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "observations": {"type": "array", "items": {"type": "string"}},
    },
}
