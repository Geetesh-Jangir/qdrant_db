"""LLM defaults for equity fund week (Haiku 5.5)."""

from __future__ import annotations

from ai_insight.common.config import load_config

DEFAULT_MODEL = "claude-haiku-5-5"


def equity_week_llm_kwargs(*, temperature: float | None = None) -> dict[str, object]:
    cfg = load_config()
    return {
        "model_override": (cfg.llm_model or DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "provider_override": (cfg.llm_provider or "anthropic").strip().lower() or "anthropic",
        "temperature": cfg.llm_temperature if temperature is None else temperature,
    }