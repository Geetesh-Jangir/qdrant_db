"""LLM call and response validation for holding insights."""

from __future__ import annotations

import logging
import re
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
HEADLINE_WORD_MIN = 5
HEADLINE_WORD_MAX = 16


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
        out["headline"] = None
        out["insight"] = None
    else:
        out.setdefault("reason_if_skipped", None)
        out.setdefault("headline", None)
    return out


def short_stock_name(name: str) -> str:
    for suffix in (" Limited", " Ltd.", " Ltd", " Inc.", " Corporation"):
        if name.endswith(suffix):
            return name[: -len(suffix)].strip()
    return name.strip()


def _pct_in_text(text: str) -> list[float]:
    return [float(m.group(1)) for m in re.finditer(r"(-?\d+(?:\.\d+)?)\s*%", text)]


def _pct_matches_week_change(p: float, week_change_pct: float) -> bool:
    """Match signed % or common 'down 4.3%' style (unsigned % + direction words)."""
    target = float(week_change_pct)
    tol = 0.25
    if abs(p - target) <= tol or abs(p - round(target, 2)) <= tol:
        return True
    mag = abs(p)
    atm = abs(target)
    return abs(mag - atm) <= tol or abs(mag - abs(round(target, 2))) <= tol


def _headline_week_matches(headline: str, week_change_pct: float | None) -> bool:
    if week_change_pct is None:
        return True
    hl = headline.lower()
    pcts = _pct_in_text(headline)
    if not pcts:
        return False
    target = float(week_change_pct)
    if not any(_pct_matches_week_change(p, target) for p in pcts):
        return False
    if target > 0.05:
        return "up" in hl or "higher" in hl or "gain" in hl or "rise" in hl or "rally" in hl
    if target < -0.05:
        return "down" in hl or "lower" in hl or "fall" in hl or "drop" in hl or "slip" in hl
    return "flat" in hl or "unchanged" in hl or "sideways" in hl or "up" in hl or "down" in hl


def parse_insight_lines(
    data: dict[str, Any],
    *,
    week_change_pct: float | None = None,
) -> tuple[bool, list[str] | None, str | None, str | None]:
    """Return ok, insight_lines, headline, failure_reason."""
    if data.get("skip"):
        reason = str(data.get("reason_if_skipped") or "skipped")
        return False, None, None, reason
    blob = str(data.get("insight") or "").strip()
    if not blob:
        return False, None, None, "empty_insight"
    headline = _as_paragraph(str(data.get("headline") or ""))
    if not headline:
        return False, None, None, "empty_headline"
    hw = _word_count(headline)
    if hw < HEADLINE_WORD_MIN or hw > HEADLINE_WORD_MAX:
        return False, None, None, f"expected_headline_{HEADLINE_WORD_MIN}_{HEADLINE_WORD_MAX}_words_got_{hw}"
    if not _headline_week_matches(headline, week_change_pct):
        return False, None, None, "headline_week_pct_mismatch"
    paragraph = _as_paragraph(blob)
    words = _word_count(paragraph)
    if words < INSIGHT_WORD_MIN:
        return False, None, None, f"expected_{INSIGHT_WORD_MIN}_{INSIGHT_WORD_MAX}_words_got_{words}"
    if words > INSIGHT_WORD_MAX:
        if words <= INSIGHT_WORD_SOFT_MAX:
            trimmed = _shrink_paragraph(paragraph, INSIGHT_WORD_MAX)
            tw = _word_count(trimmed)
            if INSIGHT_WORD_MIN <= tw <= INSIGHT_WORD_MAX:
                return True, [trimmed], headline, None
        return False, None, None, f"expected_{INSIGHT_WORD_MIN}_{INSIGHT_WORD_MAX}_words_got_{words}"
    return True, [paragraph], headline, None


def _usage_from_result(result: Any, *, calls: int) -> dict[str, Any]:
    usage = getattr(result, "usage", None)
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "llm_calls": calls,
        "model": str(getattr(usage, "model", "") or ""),
    }


def call_holding_llm(
    user_prompt: str,
    *,
    week_change_pct: float | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    if dry_run:
        return {
            "skip": False,
            "headline": "Example Bank up 1.2% on margin hopes from rate repricing",
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
            max_tokens=220,
            config=cfg,
            call=_call,
            kind="holding_insight",
        )
        ok, lines, headline, reason = parse_insight_lines(
            _normalize_response(result.data),
            week_change_pct=week_change_pct,
        )
        usage = _usage_from_result(result, calls=1)
        if ok:
            return {
                "skip": False,
                "headline": headline,
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