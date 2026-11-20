"""Facts and the draft JSON schema for the flow narrative."""

from __future__ import annotations

from typing import Any

INSIGHT_ID = "fii_dii_flow_narrative"
PROMPT_VERSION = "v9.4"
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

# Legacy multi-section keys (normalize only).
LEGACY_FLOW_SECTIONS: tuple[str, ...] = (
    "what_happened",
    "what_explains_it",
    "market_and_mf_impact",
    "what_matters_next",
    "bottom_line",
    "flow_snapshot",
    "driving_flows",
    "market_response",
    "mutual_fund_implications",
    "risks_and_watch",
    "where_money_may_have_gone",
    "why_flows_may_look_this_way",
    "what_market_showed",
    "investor_relevance",
    "what_to_watch",
)

DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "headline",
        "paragraph",
        "observations",
        "chosen_cluster_ids",
        "confidence",
        "no_clear_driver",
    ],
    "properties": {
        "headline": {"type": "string"},
        "paragraph": {"type": "string", "minLength": 1},
        "observations": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "minItems": 2,
            "maxItems": 3,
        },
        "chosen_cluster_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "no_clear_driver": {"type": "boolean"},
    },
}