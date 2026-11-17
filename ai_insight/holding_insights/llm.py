"""LLM call and response validation for holding insights."""

from __future__ import annotations

import logging
from typing import Any

from ai_insight.common.config import load_config
from ai_insight.common.llm import LlmSchemaError, LlmUnavailable, generate_json
from ai_insight.holding_insights.config import llm_allow_fallback
from ai_insight.holding_insights.prompt import SYSTEM_PROMPT
from ai_insight.holding_insights.schema import LLM_RESPONSE_SCHEMA

logger = logging.getLogger(__name__)

INSIGHT_WORD_MIN = 22
INSIGHT_WORD_MAX = 40
# If the model is slightly over budget, trim in-process (no second LLM call).
INSIGHT_WORD_SOFT_MAX = 72


def _as_paragraph(blob: str) -> str:
    return " ".join(blob.split())


def _word_count(text: str) -> int:
    return len(text.split())


def _shrink_paragraph(text: str, max_words: int) -> str:
    parts = text.split()
    while len(parts) > max_words:
        parts.pop()
    out = " ".join(parts).rstrip(".,;")
    if out and not out.endswith((".", "!", "?")):
        out += "."
    return out


def _normalize_response(data: dict[str, Any]) -> dict[str, Any]:
    out = dict(data)
    if out.get("skip"):
        out.setdefault("reason_if_skipped", "skipped")
    else:
        out.setdefault("reason_if_skipped", None)
    return out


def parse_insight_lines(data: dict[str, Any]) -> tuple[bool, list[str] | None, str | None]:
    if data.get("skip"):
        reason = str(data.get("reason_if_skipped") or "skipped")
        return False, None, reason
    blob = str(data.get("insight") or "").strip()
    if not blob:
        return False, None, "empty_insight"
    paragraph = _as_paragraph(blob)
    words = _word_count(paragraph)
    if words < INSIGHT_WORD_MIN:
        return False, None, f"expected_{INSIGHT_WORD_MIN}_{INSIGHT_WORD_MAX}_words_got_{words}"
    if words > INSIGHT_WORD_MAX:
        if words <= INSIGHT_WORD_SOFT_MAX:
            trimmed = _shrink_paragraph(paragraph, INSIGHT_WORD_MAX)
            tw = _word_count(trimmed)
            if INSIGHT_WORD_MIN <= tw <= INSIGHT_WORD_MAX:
                return True, [trimmed], None
        return False, None, f"expected_{INSIGHT_WORD_MIN}_{INSIGHT_WORD_MAX}_words_got_{words}"
    return True, [paragraph], None


def _usage_from_result(result: Any, *, calls: int) -> dict[str, Any]:
    usage = getattr(result, "usage", None)
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "llm_calls": calls,
        "model": str(getattr(usage, "model", "") or ""),
    }


def call_holding_llm(user_prompt: str, *, dry_run: bool = False) -> dict[str, Any]:
    if dry_run:
        return {
            "skip": False,
            "insight_lines": ["Line one. Line two. Line three."],
            "reason_if_skipped": None,
            "model_used": "dry_run",
            "raw_text": "",
            "retries": 0,
            "usage": {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0, "model": "dry_run"},
        }

    cfg = load_config()
    allow_fallback = llm_allow_fallback()

    def _call(**kwargs: Any) -> Any:
        from news_rag.llm_client import call_json_llm

        kwargs["allow_fallback"] = allow_fallback
        # Plain JSON in the reply body — tool_choice can hide large user prompts on Haiku.
        kwargs["response_schema"] = None
        kwargs["stage"] = "holding_insight"
        return call_json_llm(**kwargs)

    try:
        result = generate_json(
            SYSTEM_PROMPT,
            user_prompt,
            LLM_RESPONSE_SCHEMA,
            max_tokens=160,
            config=cfg,
            call=_call,
            kind="holding_insight",
        )
        ok, lines, reason = parse_insight_lines(_normalize_response(result.data))
        usage = _usage_from_result(result, calls=1)
        if ok:
            return {
                "skip": False,
                "insight_lines": lines,
                "reason_if_skipped": None,
                "model_used": result.usage.model or cfg.llm_model,
                "raw_text": result.raw_text,
                "retries": 0,
                "usage": usage,
            }
        return {
            "skip": True,
            "insight_lines": None,
            "reason_if_skipped": reason or "validation_failed",
            "model_used": result.usage.model or cfg.llm_model,
            "raw_text": result.raw_text,
            "retries": 0,
            "error": "llm_validation_failed",
            "usage": usage,
        }
    except (LlmSchemaError, LlmUnavailable) as exc:
        logger.warning("holding insight LLM failed: %s", exc)
        return {
            "skip": True,
            "insight_lines": None,
            "reason_if_skipped": str(exc)[:200],
            "model_used": cfg.llm_model,
            "raw_text": "",
            "retries": 0,
            "error": "llm_error",
            "usage": {"input_tokens": 0, "output_tokens": 0, "llm_calls": 0, "model": cfg.llm_model},
        }