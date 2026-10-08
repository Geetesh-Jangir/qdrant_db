"""Output quality judge — JSON LLM scores. Jev is disabled on the ask path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from news_rag.config import get_settings
from news_rag.llm_client import call_json_llm, contract_model, llm_api_key_configured
from news_rag.llm_text import parse_json_from_text

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

NO_DATA_MSG = "We do not have information related to this query in our data."

JUDGE_FALLBACK_PROMPT = """Score the draft answer against the question and context (0.0 to 1.0 each).
Return JSON only:
{"answers_query":0.9,"grounded":0.9,"on_topic":0.9,"no_advice":1.0,"no_extra":0.9,"pass":true}
The planner may request NAV, holdings, and news — those are NOT "extra".
no_extra penalizes only unrelated facts the user did not ask for and the planner did not request.
pass is informational only; the answer is always shown to the user."""

JUDGE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answers_query": {"type": "number"},
        "grounded": {"type": "number"},
        "on_topic": {"type": "number"},
        "no_advice": {"type": "number"},
        "no_extra": {"type": "number"},
        "pass": {"type": "boolean"},
    },
    "required": ["answers_query", "grounded", "on_topic", "no_advice", "no_extra", "pass"],
}


@dataclass
class JudgeResult:
    passed: bool
    scores: dict[str, float]
    attempt: int
    raw: dict[str, Any]
    usable: bool = True


def _thresholds() -> float:
    return get_settings().judge_min_score


def _scores_usable(scores: dict[str, float], *, truncated: bool = False) -> bool:
    """Zeros after a truncated parse are not a real grounded score — do not retry the whole ask."""
    if not scores:
        return False
    grounded = scores.get("grounded")
    if grounded is None:
        return False
    if truncated and all(float(scores.get(k) or 0) == 0 for k in ("answers_query", "grounded", "on_topic")):
        return False
    return True


def judge_answer(
    question: str,
    draft: str,
    context_summary: str,
    *,
    query_log: QueryLogger | None = None,
) -> JudgeResult:
    """Score the draft. Ask never uses Jev (422 + extra HTTP). Fail closed on errors."""
    settings = get_settings()
    thr = _thresholds()

    # Jev is commented out for /api/ask: the client sent criteria as an object and
    # Jev 422'd, which forced a broken LLM fallback and a full agent retry.
    # from news_pipeline.config import Settings as PipelineSettings
    # from news_pipeline.jev.client import JevClient
    # pipe = PipelineSettings()
    # if pipe.jev_base_url and pipe.jev_api_key:
    #     ... jev.evaluate(...)

    if not llm_api_key_configured(settings):
        return JudgeResult(passed=False, scores={}, attempt=1, raw={"error": "no_judge"}, usable=False)

    user = (
        f"Question:\n{question}\n\nContext summary:\n{context_summary[:6000]}\n\nDraft:\n{draft}"
    )
    try:
        res = call_json_llm(
            system_prompt=JUDGE_FALLBACK_PROMPT,
            user_content=user,
            model_override=contract_model(settings),
            max_tokens=max(300, int(settings.contract_max_tokens or 800)),
            temperature=0.0,
            query_log=query_log,
            response_schema=JUDGE_RESPONSE_SCHEMA,
            stage="judge",
        )
        parsed = res.parsed if isinstance(res.parsed, dict) else (parse_json_from_text(res.raw_text) or {})
        if not isinstance(parsed, dict):
            parsed = {}
        scores = {
            "answers_query": float(parsed.get("answers_query") or 0),
            "grounded": float(parsed.get("grounded") or 0),
            "on_topic": float(parsed.get("on_topic") or parsed.get("answers_query") or 0),
            "no_extra": float(parsed.get("no_extra") or 0),
            "no_advice": float(parsed.get("no_advice") or 0),
        }
        usable = _scores_usable(scores, truncated=bool(res.truncated)) and bool(parsed)
        passed = bool(parsed.get("pass")) and all(scores[k] >= thr for k in scores if k != "no_advice")
        if scores.get("no_extra", 0) < 0.7:
            passed = False
        if not usable:
            passed = False
        if query_log is not None:
            query_log.write(f"JUDGE llm scores={scores} pass={passed} usable={usable}")
        return JudgeResult(passed=passed, scores=scores, attempt=1, raw=parsed, usable=usable)
    except Exception as exc:
        if query_log is not None:
            query_log.write(f"JUDGE error fail_closed={exc}")
        return JudgeResult(passed=False, scores={}, attempt=1, raw={"error": str(exc)}, usable=False)
