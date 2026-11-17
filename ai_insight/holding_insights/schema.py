"""JSON schema for holding insight LLM response."""

from __future__ import annotations

from typing import Any

LLM_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["skip", "insight", "headline"],
    "properties": {
        "skip": {"type": "boolean"},
        "insight": {"type": ["string", "null"]},
        "headline": {"type": ["string", "null"]},
        "reason_if_skipped": {"type": ["string", "null"]},
    },
}