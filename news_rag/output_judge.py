"""Output quality judge — JSON LLM scores. Jev is disabled on the ask path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from news_rag.config import get_settings
from news_rag.llm_client import call_json_llm, contract_model, llm_api_key_configured
from news_rag.llm_text import parse_json_from_text
from news_rag.prompts import build_judge_prompt

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

NO_DATA_MSG = "We do not have information related to this query in our data."

JUDGE_FALLBACK_PROMPT = build_judge_prompt()

JUDGE_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answers_query": {"type": "number"},
        "grounded": {"type": "number"},
        "on_topic": {"type": "number"},
        "no_advice": {"type": "number"},
        "no_extra": {"type": "number"},
        "insight_depth": {"type": "number"},
        "causal_discipline": {"type": "number"},
        "has_final_summary": {"type": "boolean"},
        "has_disclaimer": {"type": "boolean"},
        "window_stated": {"type": "boolean"},
        "no_outlets_or_dates": {"type": "boolean"},
        "news_recap_flag": {"type": "boolean"},
        "fix_instructions": {"type": "string"},
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
    telemetry: Any = None,
) -> JudgeResult:
    """Score the draft using Jev (with prompt caching enabled) if configured, else JSON LLM."""
    import time
    settings = get_settings()
    thr = _thresholds()

    # 1. Try Jev with prompt caching enabled if configured
    try:
        from news_pipeline.config import Settings as PipelineSettings
        from news_pipeline.jev.client import JevClient, read_noul

        pipe = PipelineSettings()
        if (pipe.jev_base_url or "").strip() and (pipe.jev_api_key or "").strip():
            with JevClient(pipe) as jev:
                state = {
                    "question": question[:1500],
                    "draft": draft[:3000],
                    "context": context_summary[:4000],
                }
                questions = {
                    "answers_query": {
                        "type": "noul",
                        "instructions": "Does the draft fully answer the user's question?",
                        "criteria": {"true": "Fully answers", "false": "Misses key asks"},
                    },
                    "grounded": {
                        "type": "noul",
                        "instructions": "Are all claims and numbers supported strictly by the context summary?",
                        "criteria": {"true": "Fully grounded", "false": "Adds outside or ungrounded facts"},
                    },
                    "no_extra": {
                        "type": "noul",
                        "instructions": "Does the draft avoid unrelated commentary or unasked information?",
                        "criteria": {"true": "Focused", "false": "Adds unrequested filler"},
                    },
                    "no_advice": {
                        "type": "noul",
                        "instructions": "Is the draft free of investment buy/sell advice or stock price predictions?",
                        "criteria": {"true": "No advice", "false": "Contains buy/sell/predict advice"},
                    },
                }
                t0_jev = time.perf_counter()
                answers = jev.evaluate(
                    state, questions, stage="ask_judge", detail="output_judge", enable_prompt_cache=True
                )
                dur_jev = round((time.perf_counter() - t0_jev) * 1000, 1)
                scores = {
                    "answers_query": read_noul(answers.get("answers_query")),
                    "grounded": read_noul(answers.get("grounded")),
                    "on_topic": read_noul(answers.get("answers_query")),
                    "no_extra": read_noul(answers.get("no_extra")),
                    "no_advice": read_noul(answers.get("no_advice")),
                }
                passed = all(scores[k] >= thr for k in ("answers_query", "grounded")) and scores["no_advice"] >= 0.9
                if telemetry is not None:
                    usage = jev.last_call_usage()
                    telemetry.add_llm_usage(
                        stage="judge",
                        provider="jev",
                        model=pipe.jev_model,
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        cached_input_tokens=usage.get("cached_tokens", 0),
                        total_ms=dur_jev,
                        usage_source="api",
                    )
                if query_log is not None:
                    query_log.write(f"JUDGE jev scores={scores} pass={passed}")
                return JudgeResult(passed=passed, scores=scores, attempt=1, raw=answers, usable=True)
    except Exception as exc:
        if query_log is not None:
            query_log.write(f"JUDGE jev_fallback_to_llm error={exc}")

    # 2. JSON LLM Judge fallback (prompt caching enabled on Messages API)
    if not llm_api_key_configured(settings):
        return JudgeResult(passed=False, scores={}, attempt=1, raw={"error": "no_judge"}, usable=False)

    user = (
        f"Question:\n{question}\n\nContext summary:\n{context_summary[:6000]}\n\nDraft:\n{draft}"
    )
    if query_log is not None:
        query_log.write(
            "JUDGE_START scoring draft vs question and evidence_text "
            f"(draft_chars={len(draft)} context_chars={len(context_summary)})"
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
        if telemetry is not None and res is not None:
            telemetry.add_llm_usage(
                stage="judge",
                provider=res.provider,
                model=res.model,
                input_tokens=res.input_tokens,
                output_tokens=res.output_tokens,
                cached_input_tokens=getattr(res, "cached_tokens", 0),
                total_ms=round(res.duration_sec * 1000, 1),
                usage_source="api",
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
            "insight_depth": float(parsed.get("insight_depth") or parsed.get("on_topic") or 0),
            "causal_discipline": float(parsed.get("causal_discipline") or parsed.get("grounded") or 0),
        }
        usable = _scores_usable(scores, truncated=bool(res.truncated)) and bool(parsed)
        passed = bool(parsed.get("pass"))
        if not passed:
            passed = (
                scores["answers_query"] >= max(thr, 0.7)
                and scores["grounded"] >= max(thr, 0.8)
                and scores.get("no_advice", 0) >= 1.0
                and scores.get("insight_depth", 0) >= 0.6
                and scores.get("causal_discipline", 0) >= 0.7
                and not bool(parsed.get("news_recap_flag"))
            )
        if scores.get("no_extra", 0) < 0.7:
            passed = False
        if parsed.get("no_outlets_or_dates") is False:
            passed = False
        if not usable:
            passed = False
        if query_log is not None:
            trunc_note = " truncated_scores_untrusted=true" if res.truncated and not usable else ""
            query_log.write(
                f"JUDGE_RESULT scores={scores} pass={passed} usable={usable}{trunc_note}"
            )
        return JudgeResult(passed=passed, scores=scores, attempt=1, raw=parsed, usable=usable)
    except Exception as exc:
        if query_log is not None:
            query_log.write(f"JUDGE error fail_closed={exc}")
        return JudgeResult(passed=False, scores={}, attempt=1, raw={"error": str(exc)}, usable=False)
