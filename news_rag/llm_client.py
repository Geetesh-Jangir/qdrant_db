"""Call DeepSeek or Google Gemini for structured news insight."""

from __future__ import annotations

import contextvars
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

# After a Gemini quota 429 in this request, skip further Gemini calls (use DeepSeek if configured).
_gemini_skip_for_request: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "gemini_skip_for_request",
    default=False,
)
_gemini_cooldown_until: float = 0.0
_GEMINI_COOLDOWN_SEC = 300.0


def reset_llm_request_state() -> None:
    _gemini_skip_for_request.set(False)


def gemini_in_cooldown() -> bool:
    return time.monotonic() < _gemini_cooldown_until


def gemini_blocked(settings: Settings | None = None) -> bool:
    """True when Gemini should not be called (cooldown / quota in this request)."""
    settings = settings or get_settings()
    if llm_provider(settings) != "gemini":
        return False
    return gemini_in_cooldown() or _gemini_skip_for_request.get()


def _mark_gemini_quota_exceeded(query_log: QueryLogger | None, body: str) -> None:
    global _gemini_cooldown_until
    _gemini_skip_for_request.set(True)
    _gemini_cooldown_until = time.monotonic() + _GEMINI_COOLDOWN_SEC
    if query_log is not None:
        query_log.write(
            f"gemini_quota_exceeded skip_further_gemini_calls=true "
            f"cooldown_sec={_GEMINI_COOLDOWN_SEC:.0f}"
        )

from news_rag.config import Settings, get_settings
from news_rag.llm_text import extract_assistant_text, extract_gemini_text

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger


@dataclass
class LlmCallResult:
    raw_text: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int | None
    duration_sec: float
    http_status: int


def llm_provider(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    name = (settings.rag_llm_provider or "deepseek").strip().lower()
    if name in ("gemini", "google"):
        return "gemini"
    return "deepseek"


def llm_model(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if llm_provider(settings) == "gemini":
        return settings.gemini_model
    return settings.deepseek_model


def composer_model(settings: Settings | None = None) -> str:
    """Final ask answer only. Planner, digest, and judge keep gemini_model."""
    settings = settings or get_settings()
    if llm_provider(settings) != "gemini":
        return llm_model(settings)
    name = (settings.gemini_composer_model or "").strip()
    return name or "gemini-3.8-flash"


def router_model(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if (settings.rag_router_model or "").strip():
        return settings.rag_router_model.strip()
    return llm_model(settings)


def contract_model(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if (settings.rag_contract_model or "").strip():
        return settings.rag_contract_model.strip()
    return router_model(settings)


def llm_api_key_configured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if llm_provider(settings) == "gemini":
        return bool((settings.gemini_api_key or "").strip())
    return bool((settings.deepseek_api_key or "").strip())


def missing_llm_key_message(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if llm_provider(settings) == "gemini":
        return "GEMINI_API_KEY not configured"
    return "DEEPSEEK_API_KEY not configured"


def _effective_provider(settings: Settings) -> str:
    primary = llm_provider(settings)
    if primary == "gemini" and gemini_blocked(settings):
        if (settings.deepseek_api_key or "").strip():
            return "deepseek"
    return primary


def _is_gemini_quota_response(status: int, body: str) -> bool:
    """Any HTTP 429 from Gemini is treated as rate-limit / quota (body text varies)."""
    if status == 429:
        return True
    lower = (body or "").lower()
    return "quota" in lower or "rate limit" in lower or "resource_exhausted" in lower


def call_insight_llm(
    *,
    system_prompt: str,
    user_content: str,
    query_log: QueryLogger | None = None,
    model_override: str | None = None,
) -> LlmCallResult:
    settings = get_settings()
    provider = _effective_provider(settings)
    gemini_model = (model_override or "").strip() or settings.gemini_model
    if provider == "gemini":
        try:
            return _call_gemini(
                settings,
                system_prompt,
                user_content,
                model=gemini_model,
                max_tokens=settings.llm_max_tokens,
                temperature=0.25,
                query_log=query_log,
            )
        except Exception as exc:
            if settings.deepseek_api_key and settings.deepseek_api_key.strip():
                if query_log is not None:
                    query_log.write(f"gemini_failed_falling_back_to_deepseek error={exc}")
                if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                    if _is_gemini_quota_response(exc.response.status_code, exc.response.text or ""):
                        _mark_gemini_quota_exceeded(query_log, exc.response.text or "")
                return _call_deepseek(
                    settings,
                    system_prompt,
                    user_content,
                    model=settings.deepseek_model,
                    max_tokens=settings.llm_max_tokens,
                    temperature=0.25,
                    query_log=query_log,
                )
            if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                if exc.response.status_code == 429:
                    raise RuntimeError(
                        "Gemini returned HTTP 429 (rate limit or daily quota). "
                        "Wait a few minutes, avoid rapid repeated asks, "
                        "or set DEEPSEEK_API_KEY for automatic fallback while RAG_LLM_PROVIDER=gemini."
                    ) from exc
            raise
    else:
        try:
            return _call_deepseek(
                settings,
                system_prompt,
                user_content,
                model=settings.deepseek_model,
                max_tokens=settings.llm_max_tokens,
                temperature=0.25,
                query_log=query_log,
            )
        except Exception as exc:
            if settings.gemini_api_key and settings.gemini_api_key.strip():
                if query_log is not None:
                    query_log.write(f"deepseek_failed_falling_back_to_gemini error={exc}")
                return _call_gemini(
                    settings,
                    system_prompt,
                    user_content,
                    model=settings.gemini_model,
                    max_tokens=settings.llm_max_tokens,
                    temperature=0.25,
                    query_log=query_log,
                )
            raise


def call_json_llm(
    *,
    system_prompt: str,
    user_content: str,
    model_override: str | None = None,
    max_tokens: int = 600,
    temperature: float = 0.0,
    query_log: QueryLogger | None = None,
) -> LlmCallResult:
    settings = get_settings()
    provider = _effective_provider(settings)
    chosen_model = model_override or router_model(settings)
    if provider == "gemini":
        try:
            return _call_gemini(
                settings,
                system_prompt,
                user_content,
                model=chosen_model,
                max_tokens=max_tokens,
                temperature=temperature,
                response_json=True,
                query_log=query_log,
            )
        except Exception as exc:
            if settings.deepseek_api_key and settings.deepseek_api_key.strip():
                if query_log is not None:
                    query_log.write(f"gemini_json_failed_falling_back_to_deepseek error={exc}")
                if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                    if _is_gemini_quota_response(exc.response.status_code, exc.response.text):
                        _mark_gemini_quota_exceeded(query_log, exc.response.text)
                return _call_deepseek(
                    settings,
                    system_prompt,
                    user_content,
                    model=settings.deepseek_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_json=True,
                    query_log=query_log,
                )
            if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                if exc.response.status_code == 429:
                    raise RuntimeError(
                        "Gemini returned HTTP 429 (rate limit or daily quota). "
                        "Wait a few minutes, avoid rapid repeated asks, "
                        "or set DEEPSEEK_API_KEY for automatic fallback while RAG_LLM_PROVIDER=gemini."
                    ) from exc
            raise
    else:
        try:
            return _call_deepseek(
                settings,
                system_prompt,
                user_content,
                model=chosen_model,
                max_tokens=max_tokens,
                temperature=temperature,
                response_json=True,
                query_log=query_log,
            )
        except Exception as exc:
            if settings.gemini_api_key and settings.gemini_api_key.strip():
                if query_log is not None:
                    query_log.write(f"deepseek_json_failed_falling_back_to_gemini error={exc}")
                return _call_gemini(
                    settings,
                    system_prompt,
                    user_content,
                    model=settings.gemini_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    response_json=True,
                    query_log=query_log,
                )
            raise


def _call_deepseek(
    settings: Settings,
    system_prompt: str,
    user_content: str,
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.25,
    response_json: bool = False,
    query_log: QueryLogger | None,
) -> LlmCallResult:
    api_key = (settings.deepseek_api_key or "").strip()
    if not api_key:
        raise RuntimeError("Set DEEPSEEK_API_KEY in .env")

    url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
    chosen_model = model or settings.deepseek_model
    chosen_max_tokens = max_tokens or settings.llm_max_tokens
    payload: dict[str, Any] = {
        "model": chosen_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": chosen_max_tokens,
        "temperature": temperature,
    }
    if response_json:
        payload["response_format"] = {"type": "json_object"}

    if query_log is not None:
        query_log.write(
            f"llm request provider=deepseek url={url} model={chosen_model} "
            f"max_tokens={chosen_max_tokens} system_chars={len(system_prompt)} "
            f"user_chars={len(user_content)}"
        )

    started = time.perf_counter()
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        duration = time.perf_counter() - started
        if query_log is not None and response.status_code >= 400:
            query_log.log_error(
                "llm",
                f"provider=deepseek http_status={response.status_code} body={response.text[:500]}",
            )
        response.raise_for_status()
        data = response.json()

    usage = data.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("completion_tokens") or 0)
    total_raw = usage.get("total_tokens")
    total_tokens = int(total_raw) if total_raw is not None else None

    result = LlmCallResult(
        raw_text=extract_assistant_text(data),
        provider="deepseek",
        model=chosen_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        duration_sec=duration,
        http_status=response.status_code,
    )
    if query_log is not None:
        query_log.record_llm_call(
            provider=result.provider,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            duration_sec=result.duration_sec,
            http_status=result.http_status,
        )
    return result


def _call_gemini(
    settings: Settings,
    system_prompt: str,
    user_content: str,
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.25,
    response_json: bool = False,
    query_log: QueryLogger | None,
) -> LlmCallResult:
    api_key = (settings.gemini_api_key or "").strip().strip('"')
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY in .env")

    chosen_model = (model or settings.gemini_model).strip()
    base = settings.gemini_base_url.rstrip("/")
    url = f"{base}/models/{chosen_model}:generateContent"
    chosen_max_tokens = max_tokens or settings.llm_max_tokens
    
    gen_config: dict[str, Any] = {
        "temperature": temperature,
        "maxOutputTokens": chosen_max_tokens,
    }
    if response_json:
        gen_config["responseMimeType"] = "application/json"

    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_content}]}],
        "generationConfig": gen_config,
    }
    if query_log is not None:
        query_log.write(
            f"llm request provider=gemini url={url} model={chosen_model} "
            f"max_output_tokens={chosen_max_tokens} system_chars={len(system_prompt)} "
            f"user_chars={len(user_content)}"
        )

    started = time.perf_counter()
    has_fallback = bool((settings.deepseek_api_key or "").strip())
    max_retries = 1 if has_fallback else 3
    backoffs = [1.0] if has_fallback else [2.0, 4.0, 8.0]
    for attempt in range(max_retries + 1):
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": api_key,
                },
                json=payload,
            )
            duration = time.perf_counter() - started
            if response.status_code == 429 and attempt < max_retries:
                backoff = backoffs[attempt] if attempt < len(backoffs) else 5.0
                if query_log is not None:
                    query_log.write(f"gemini_rate_limited attempt={attempt+1} sleep={backoff:.1f}s")
                time.sleep(backoff)
                continue

            if query_log is not None and response.status_code >= 400:
                query_log.log_error(
                    "llm",
                    f"provider=gemini http_status={response.status_code} body={response.text[:500]}",
                )
            if _is_gemini_quota_response(response.status_code, response.text):
                _mark_gemini_quota_exceeded(query_log, response.text)
            if response.status_code == 404:
                raise httpx.HTTPStatusError(
                    "Gemini model not found or retired for your API key. "
                    f"Try GEMINI_MODEL=gemini-3.5-flash-lite (current: {chosen_model!r}). "
                    "List models: GET .../v1beta/models with x-goog-api-key.",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
            data = response.json()
            break

    usage = data.get("usageMetadata") or {}
    input_tokens = int(usage.get("promptTokenCount") or 0)
    output_tokens = int(usage.get("candidatesTokenCount") or 0)
    total_raw = usage.get("totalTokenCount")
    total_tokens = int(total_raw) if total_raw is not None else None

    result = LlmCallResult(
        raw_text=extract_gemini_text(data),
        provider="gemini",
        model=chosen_model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        duration_sec=duration,
        http_status=response.status_code,
    )
    if query_log is not None:
        query_log.record_llm_call(
            provider=result.provider,
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            total_tokens=result.total_tokens,
            duration_sec=result.duration_sec,
            http_status=result.http_status,
        )
    return result

