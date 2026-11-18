"""Facts and the draft JSON schema for the flow narrative."""

from __future__ import annotations

from typing import Any

INSIGHT_ID = "fii_dii_flow_narrative"
PROMPT_VERSION = "v3"
NO_DRIVER = "News flow doesn't point to one clear driver today."

MACRO_WHY = (
    "Macro - Rupee / USD",
    "Macro - Bond Yields",
    "Macro - FII DII Flows",
    "Macro - Crude Oil",
    "Macro - RBI Repo Rate",
    "Macro - Geopolitical Risk",
    "Macro - Tariffs & Trade",
)

DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["headline", "body", "chosen_cluster_ids", "confidence", "no_clear_driver", "implication"],
    "properties": {
        "headline": {"type": "string"},
        "body": {"type": "string"},
        "chosen_cluster_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "no_clear_driver": {"type": "boolean"},
        "implication": {"type": ["string", "null"]},
        "observations": {"type": "array", "items": {"type": "string"}},
    },
}
