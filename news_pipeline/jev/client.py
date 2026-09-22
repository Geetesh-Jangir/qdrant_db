"""HTTP client for Jev. Questions are booleans, choices, and scores."""

from __future__ import annotations

import logging
import time

import httpx

from news_pipeline.config import (
    DIRECTION_OPTIONS,
    EVENT_OPTIONS,
    IMPACT_LEVELS,
    RELEVANCE_LEVELS,
    Settings,
)
from news_pipeline.run_log import get_run_logger

logger = logging.getLogger(__name__)


class JevError(RuntimeError):
    pass


class JevClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.jev_base_url or not settings.jev_api_key:
            raise JevError("Set JEV_BASE_URL and JEV_API_KEY")
        self._model = settings.jev_model
        self._input_price = settings.jev_input_cost_per_million_usd
        self._last_call_usage: dict = {}
        self._client = httpx.Client(
            timeout=90.0,
            headers={
                "Authorization": f"Bearer {settings.jev_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        self._url = settings.jev_base_url

    def close(self) -> None:
        self._client.close()

    def evaluate(
        self,
        state: dict,
        questions: dict,
        *,
        stage: str = "jev",
        detail: str = "",
    ) -> dict:
        if not questions:
            self._last_call_usage = {}
            return {}
        payload = {"model": self._model, "state": state, "questions": questions}
        started = time.perf_counter()
        try:
            response = self._client.post(self._url, json=payload)
        except httpx.HTTPError as exc:
            raise JevError(f"Jev request failed: {exc}") from exc
        if response.status_code >= 400:
            body = response.text[:300]
            raise JevError(f"Jev returned {response.status_code}: {body}")
        data = response.json()
        answers = data.get("answers")
        if not isinstance(answers, dict):
            raise JevError("Jev response did not include answers")
        input_tokens, output_tokens = _parse_token_usage(data)
        duration = time.perf_counter() - started
        self._last_call_usage = {
            "calls": 1,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "price_per_million_input_usd": self._input_price,
        }
        run_log = get_run_logger()
        if run_log is not None:
            run_log.record_llm_call(
                stage=stage,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_sec=duration,
                detail=detail,
            )
        return answers

    def last_call_usage(self) -> dict:
        return dict(self._last_call_usage)

    def __enter__(self) -> "JevClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def _parse_token_usage(data: dict) -> tuple[int, int]:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return 0, 0
    input_raw = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    output_raw = usage.get("output_tokens", usage.get("completion_tokens", 0))
    try:
        input_tokens = int(input_raw or 0)
    except (TypeError, ValueError):
        input_tokens = 0
    try:
        output_tokens = int(output_raw or 0)
    except (TypeError, ValueError):
        output_tokens = 0
    return max(0, input_tokens), max(0, output_tokens)


def title_questions(rows: list[dict], entity: dict) -> dict:
    """One noul per title. The question key is the local article id."""
    kind = entity["type"]
    name = entity["name"]
    questions = {}
    for row in rows:
        if kind == "holding":
            instructions = (
                f"Title: {row['title']}. "
                f"Is this headline specifically about {name} and material enough to change the stock outlook? "
                "False for a price recap, a technical call, a generic market wrap, or a different company."
            )
        else:
            instructions = (
                f"Title: {row['title']}. "
                f"Is this headline about the {name} sector as a whole, or about policy that moves that sector? "
                "False when the headline is only about one company, or when it is a price recap."
            )
        questions[row["question_id"]] = {
            "type": "noul",
            "instructions": instructions,
            "criteria": {
                "true": "Specifically about this name and material to the outlook",
                "false": "Unrelated, a lookalike, a price recap, or a generic wrap",
            },
        }
    return questions


def article_questions(matches: list[dict]) -> dict:
    questions = {}
    for index, match in enumerate(matches):
        name = match["name"]
        prefix = f"e{index}"
        if match["type"] == "holding":
            about = (
                f"Is the article about {name} itself, not a different company with a similar name? "
                "The article body is in state.article."
            )
        else:
            about = (
                f"Is the article about the {name} sector as a whole or about policy for that sector? "
                "False when it is only a single-company story. The article body is in state.article."
            )
        questions[f"{prefix}_about"] = {
            "type": "noul",
            "instructions": about,
            "criteria": {
                "true": "The body is about this name",
                "false": "The body is about something else",
            },
        }
        questions[f"{prefix}_relevance"] = {
            "type": "score",
            "instructions": f"How relevant is this article to {name}? Use the scale in criteria.",
            "criteria": list(RELEVANCE_LEVELS),
        }
        questions[f"{prefix}_impact"] = {
            "type": "score",
            "instructions": f"How much could this article change the outlook for {name}?",
            "criteria": list(IMPACT_LEVELS),
        }
        questions[f"{prefix}_direction"] = {
            "type": "choice",
            "instructions": f"What is the direction of this article for {name}?",
            "criteria": {
                "positive": "Clearly supportive for the name",
                "negative": "Clearly harmful for the name",
                "neutral": "A fact with no clear positive or negative lean",
                "unclear": "The direction cannot be told from the article",
            },
        }
        questions[f"{prefix}_event"] = {
            "type": "choice",
            "instructions": f"What kind of event is this for {name}?",
            "criteria": {
                "results": "Earnings, profit, revenue, or guidance",
                "order": "A contract, order win, or tender",
                "deal": "M&A, stake sale, investment, or partnership",
                "regulatory": "Regulator, law, tax, ban, or approval",
                "operations": "Plant, product, management, or operations",
                "macro": "Rates, crude, currency, policy, or flows",
                "opinion": "Column, recommendation, or target-price note",
                "price_recap": "Price move with no new fact",
            },
        }
        questions[f"{prefix}_stock"] = _scope_question(name, "this company or stock")
        questions[f"{prefix}_sector"] = _scope_question(name, "the broader sector, not one company only")
        questions[f"{prefix}_macro"] = _scope_question(name, "the macro backdrop such as RBI, crude, the rupee, the Fed, the budget, or flows")
    return questions


def _scope_question(name: str, scope: str) -> dict:
    return {
        "type": "noul",
        "instructions": f"Does this article affect {scope}? Judge it in relation to {name}.",
        "criteria": {"true": "Yes, it affects that scope", "false": "No, it does not"},
    }


def read_noul(answer: dict | None) -> float:
    if not isinstance(answer, dict):
        return 0.0
    raw = answer.get("noul", answer.get("probability", 0.0))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value


def read_score(answer: dict | None, levels: int) -> int:
    if not isinstance(answer, dict):
        return 0
    raw = answer.get("score", 0)
    try:
        value = int(round(float(raw)))
    except (TypeError, ValueError):
        return 0
    if value < 0:
        return 0
    if value > levels - 1:
        return levels - 1
    return value


def read_choice(answer: dict | None, allowed: tuple[str, ...], default: str) -> str:
    if not isinstance(answer, dict):
        return default
    choice = answer.get("choice") or default
    if choice not in allowed:
        return default
    return str(choice)


def score_match(answers: dict, index: int) -> dict:
    prefix = f"e{index}"
    return {
        "about_this_name": round(read_noul(answers.get(f"{prefix}_about")), 4),
        "relevance": read_score(answers.get(f"{prefix}_relevance"), len(RELEVANCE_LEVELS)),
        "impact": read_score(answers.get(f"{prefix}_impact"), len(IMPACT_LEVELS)),
        "direction": read_choice(answers.get(f"{prefix}_direction"), DIRECTION_OPTIONS, "unclear"),
        "event_type": read_choice(answers.get(f"{prefix}_event"), EVENT_OPTIONS, "operations"),
        "affects_stock": round(read_noul(answers.get(f"{prefix}_stock")), 4),
        "affects_sector": round(read_noul(answers.get(f"{prefix}_sector")), 4),
        "affects_macro": round(read_noul(answers.get(f"{prefix}_macro")), 4),
    }
