"""Call DeepSeek or Google Gemini for structured news insight."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

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


def call_insight_llm(
    *,
    system_prompt: str,
    user_content: str,
    query_log: QueryLogger | None = None,
) -> LlmCallResult:
    settings = get_settings()
    provider = llm_provider(settings)
    if provider == "gemini":
        return _call_gemini(settings, system_prompt, user_content, query_log=query_log)
    return _call_deepseek(settings, system_prompt, user_content, query_log=query_log)


def _call_deepseek(
    settings: Settings,
    system_prompt: str,
    user_content: str,
    *,
    query_log: QueryLogger | None,
) -> LlmCallResult:
    api_key = (settings.deepseek_api_key or "").strip()
    if not api_key:
        raise RuntimeError("Set DEEPSEEK_API_KEY in .env")

    url = settings.deepseek_base_url.rstrip("/") + "/chat/completions"
    model = settings.deepseek_model
    max_tokens = settings.llm_max_tokens
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.25,
    }
    if query_log is not None:
        query_log.write(
            f"llm request provider=deepseek url={url} model={model} "
            f"max_tokens={max_tokens} system_chars={len(system_prompt)} "
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

    return LlmCallResult(
        raw_text=extract_assistant_text(data),
        provider="deepseek",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        duration_sec=duration,
        http_status=response.status_code,
    )


def _call_gemini(
    settings: Settings,
    system_prompt: str,
    user_content: str,
    *,
    query_log: QueryLogger | None,
) -> LlmCallResult:
    api_key = (settings.gemini_api_key or "").strip().strip('"')
    if not api_key:
        raise RuntimeError("Set GEMINI_API_KEY in .env")

    model = settings.gemini_model.strip()
    base = settings.gemini_base_url.rstrip("/")
    url = f"{base}/models/{model}:generateContent"
    max_tokens = settings.llm_max_tokens
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_content}]}],
        "generationConfig": {
            "temperature": 0.25,
            "maxOutputTokens": max_tokens,
        },
    }
    if query_log is not None:
        query_log.write(
            f"llm request provider=gemini url={url} model={model} "
            f"max_output_tokens={max_tokens} system_chars={len(system_prompt)} "
            f"user_chars={len(user_content)}"
        )

    started = time.perf_counter()
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            url,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            json=payload,
        )
        duration = time.perf_counter() - started
        if query_log is not None and response.status_code >= 400:
            query_log.log_error(
                "llm",
                f"provider=gemini http_status={response.status_code} body={response.text[:500]}",
            )
        if response.status_code == 404:
            raise httpx.HTTPStatusError(
                "Gemini model not found or retired for your API key. "
                f"Try GEMINI_MODEL=gemini-3.5-flash-lite (current: {model!r}). "
                "List models: GET .../v1beta/models with x-goog-api-key.",
                request=response.request,
                response=response,
            )
        response.raise_for_status()
        data = response.json()

    usage = data.get("usageMetadata") or {}
    input_tokens = int(usage.get("promptTokenCount") or 0)
    output_tokens = int(usage.get("candidatesTokenCount") or 0)
    total_raw = usage.get("totalTokenCount")
    total_tokens = int(total_raw) if total_raw is not None else None

    return LlmCallResult(
        raw_text=extract_gemini_text(data),
        provider="gemini",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        duration_sec=duration,
        http_status=response.status_code,
    )
