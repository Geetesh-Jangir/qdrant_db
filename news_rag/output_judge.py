"""Output quality judge — Jev scores or JSON LLM fallback, fail closed."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from news_rag.config import get_settings
from news_rag.llm_client import call_json_llm, contract_model, llm_api_key_configured
from news_rag.llm_text import parse_json_from_text

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

NO_DATA_MSG = "We do not have information related to this query in our data."

JUDGE_FALLBACK_PROMPT = """Score the draft answer against the question and context (0.0 to 1.0 each).
Return JSON only:
{"answers_query":0.9,"grounded":0.9,"on_topic":0.9,"no_advice":1.0,"no_extra":0.9,"pass":true}
pass is true only if ALL scores >= 0.65 and no_extra >= 0.7."""


@dataclass
class JudgeResult:
    passed: bool
    scores: dict[str, float]
    attempt: int
    raw: dict[str, Any]


def _thresholds() -> float:
    return get_settings().judge_min_score


def judge_answer(
    question: str,
    draft: str,
    context_summary: str,
    *,
    query_log: QueryLogger | None = None,
) -> JudgeResult:
    """Fail closed on errors."""
    settings = get_settings()
    thr = _thresholds()
    try:
        from news_pipeline.config import Settings as PipelineSettings
        from news_pipeline.jev.client import JevClient

        pipe = PipelineSettings()
        if pipe.jev_base_url and pipe.jev_api_key:
            with JevClient(pipe) as jev:
                state = {
                    "question": question[:1500],
                    "draft": draft[:3000],
                    "context": context_summary[:4000],
                }
                questions = {
                    "answers_query": {
                        "type": "score",
                        "instructions": "Does the draft answer every part of the question?",
                        "criteria": {"1": "Fully answers", "0": "Misses key asks"},
                    },
                    "grounded": {
                        "type": "score",
                        "instructions": "Are claims supported by the context only?",
                        "criteria": {"1": "Fully grounded", "0": "Adds outside facts"},
                    },
                    "no_extra": {
                        "type": "score",
                        "instructions": "Does the draft avoid extra NAV/holdings/news the user did not ask for?",
                        "criteria": {"1": "Minimal", "0": "Adds unrelated facts"},
                    },
                    "no_advice": {
                        "type": "score",
                        "instructions": "No buy/sell/prediction advice?",
                        "criteria": {"1": "Compliant", "0": "Contains advice"},
                    },
                }
                answers = jev.evaluate(state, questions, stage="ask_judge", detail="output_judge")
                scores = {
                    "answers_query": _norm_score(answers.get("answers_query")),
                    "grounded": _norm_score(answers.get("grounded")),
                    "on_topic": _norm_score(answers.get("answers_query")),
                    "no_extra": _norm_score(answers.get("no_extra")),
                    "no_advice": _norm_score(answers.get("no_advice")),
                }
                passed = all(scores[k] >= thr for k in scores) and scores["no_extra"] >= 0.7
                if query_log is not None:
                    query_log.write(f"JUDGE jev scores={scores} pass={passed}")
                return JudgeResult(passed=passed, scores=scores, attempt=1, raw=answers)
    except Exception as exc:
        logger.debug("jev judge unavailable: %s", exc)
        if query_log is not None:
            query_log.write(f"JUDGE jev_skipped={exc}")

    if not llm_api_key_configured(settings):
        return JudgeResult(passed=False, scores={}, attempt=1, raw={"error": "no_judge"})

    user = (
        f"Question:\n{question}\n\nContext summary:\n{context_summary[:6000]}\n\nDraft:\n{draft}"
    )
    try:
        res = call_json_llm(
            system_prompt=JUDGE_FALLBACK_PROMPT,
            user_content=user,
            model_override=contract_model(settings),
            max_tokens=300,
            temperature=0.0,
            query_log=query_log,
        )
        parsed = parse_json_from_text(res.raw_text) or {}
        scores = {
            "answers_query": float(parsed.get("answers_query") or 0),
            "grounded": float(parsed.get("grounded") or 0),
            "on_topic": float(parsed.get("on_topic") or parsed.get("answers_query") or 0),
            "no_extra": float(parsed.get("no_extra") or 0),
            "no_advice": float(parsed.get("no_advice") or 0),
        }
        passed = bool(parsed.get("pass")) and all(scores[k] >= thr for k in scores if k != "no_advice")
        if scores.get("no_extra", 0) < 0.7:
            passed = False
        if query_log is not None:
            query_log.write(f"JUDGE llm scores={scores} pass={passed}")
        return JudgeResult(passed=passed, scores=scores, attempt=1, raw=parsed)
    except Exception as exc:
        if query_log is not None:
            query_log.write(f"JUDGE error fail_closed={exc}")
        return JudgeResult(passed=False, scores={}, attempt=1, raw={"error": str(exc)})


def _norm_score(val: Any) -> float:
    if val is None:
        return 0.0
    try:
        f = float(val)
    except (TypeError, ValueError):
        return 0.0
    if f > 1.0:
        f = f / 4.0 if f <= 4.0 else 1.0
    return max(0.0, min(1.0, f))
