"""Haiku JSON calls. Full articles are passed through with no length cap.

Insights disable provider fallback. A failed Haiku call stays a failure.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

import jsonschema

from ai_insight.common.config import CommonConfig, load_config

logger = logging.getLogger(__name__)


class LlmSchemaError(RuntimeError):
    """The model replied twice and neither reply matched the schema."""


class LlmUnavailable(RuntimeError):
    """Haiku did not return a usable reply. No other provider is tried."""


@dataclass
class LlmUsage:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    duration_sec: float = 0.0
    attempts: int = 0
    retries: int = 0


@dataclass
class LlmJsonResult:
    data: dict[str, Any]
    usage: LlmUsage
    raw_text: str = ""
    request: dict[str, Any] = field(default_factory=dict)
    kind: str = "draft"


def generate_json(
    system: str,
    user: str,
    json_schema: dict[str, Any],
    max_tokens: int = 500,
    *,
    config: CommonConfig | None = None,
    call: Callable[..., Any] | None = None,
    kind: str = "draft",
) -> LlmJsonResult:
    cfg = config or load_config()
    invoke = call or _default_call
    validator = jsonschema.Draft202012Validator(json_schema)
    usage = LlmUsage(provider=cfg.llm_provider, model=cfg.llm_model)
    prompt = user
    last_error = "empty reply"
    started = time.perf_counter()
    request = {
        "system": system,
        "user": user,
        "schema": json_schema,
        "max_tokens": max_tokens,
        "temperature": cfg.llm_temperature,
        "model": cfg.llm_model,
        "provider": cfg.llm_provider,
        "kind": kind,
    }
    raw_text = ""
    for attempt in range(1, 3):
        usage.attempts = attempt
        result = _invoke_with_retry(invoke, cfg, system, prompt, json_schema, max_tokens, usage)
        raw_text = str(getattr(result, "raw_text", "") or "")
        _add_usage(usage, result)
        provider = str(getattr(result, "provider", "") or "")
        if provider and provider != cfg.llm_provider:
            raise LlmUnavailable(
                f"reply came from {provider}, expected {cfg.llm_provider}; fallback is disabled"
            )
        parsed = getattr(result, "parsed", None)
        if not isinstance(parsed, dict):
            last_error = "reply was not a JSON object"
        else:
            errors = list(validator.iter_errors(parsed))
            if not errors:
                usage.provider = provider or usage.provider
                usage.model = str(getattr(result, "model", "") or usage.model)
                usage.duration_sec = round(time.perf_counter() - started, 3)
                return LlmJsonResult(parsed, usage, raw_text=raw_text, request=request, kind=kind)
            last_error = errors[0].message
        prompt = user + "\n\nThe previous reply failed validation: " + last_error + "\nReturn one JSON object that matches the schema."
    raise LlmSchemaError(last_error)


def format_articles_block(clusters: list[Any]) -> str:
    """Full article text, one block per cluster. Nothing is cut."""
    blocks: list[str] = []
    for cluster in clusters:
        lines = [f"CLUSTER {cluster.cluster_id} | {cluster.label}"]
        for row in cluster.articles:
            article = row.get("article") or {}
            lines.append(
                "\n".join(
                    [
                        f"TITLE: {article.get('title') or ''}",
                        f"URL: {article.get('url') or ''}",
                        f"SOURCE: {article.get('source') or ''}",
                        f"PUBLISHED: {article.get('published_at') or ''}",
                        "ARTICLE:",
                        str(article.get("scraped_text") or article.get("full_text") or ""),
                    ]
                )
            )
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _default_call(**kwargs: Any) -> Any:
    from news_rag.llm_client import call_json_llm

    kwargs.setdefault("allow_fallback", False)
    return call_json_llm(**kwargs)


def _invoke_with_retry(invoke, cfg: CommonConfig, system, prompt, json_schema, max_tokens, usage: LlmUsage):
    tries = max(1, int(cfg.llm_retries))
    last: BaseException | None = None
    for attempt in range(1, tries + 1):
        try:
            return _run_bounded(
                lambda: invoke(
                    system_prompt=system,
                    user_content=prompt,
                    model_override=cfg.llm_model,
                    provider_override=cfg.llm_provider,
                    max_tokens=max_tokens,
                    temperature=cfg.llm_temperature,
                    response_schema=json_schema,
                    stage="insight",
                    allow_fallback=False,
                ),
                cfg.llm_timeout_sec,
            )
        except LlmUnavailable:
            raise
        except Exception as exc:
            last = exc
            usage.retries += 1
            logger.warning("insight LLM attempt %s/%s failed: %s", attempt, tries, exc)
            if attempt >= tries:
                break
            time.sleep(min(8.0, 2 ** (attempt - 1)))
    raise LlmUnavailable(f"{type(last).__name__}: {last}") from last


def _add_usage(usage: LlmUsage, result: Any) -> None:
    usage.input_tokens += int(getattr(result, "input_tokens", 0) or 0)
    usage.output_tokens += int(getattr(result, "output_tokens", 0) or 0)
    usage.cached_tokens += int(getattr(result, "cached_tokens", 0) or 0)


def _run_bounded(fn: Callable[[], Any], timeout_sec: float) -> Any:
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(fn)
    try:
        return future.result(timeout=timeout_sec)
    except TimeoutError as exc:
        raise TimeoutError(f"timed out after {timeout_sec:g}s") from exc
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
