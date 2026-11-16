"""Environment-backed settings for insight jobs. Nothing here is cached."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = str(env.get(key) or "").strip()
    if not raw:
        return default
    return float(raw)


def _int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = str(env.get(key) or "").strip()
    if not raw:
        return default
    return int(raw)


def _freshness_flag(env: Mapping[str, str]) -> bool | None:
    raw = str(env.get("INSIGHTS_CHECK_FRESHNESS") or "").strip().lower()
    if not raw:
        return None
    return raw in {"1", "true", "yes", "on"}


def _bool(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw = str(env.get(key) or "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class CommonConfig:
    data_dir: Path
    holidays_path: Path
    log_dir: Path
    llm_provider: str = "anthropic"
    llm_model: str = "claude-haiku-5-5"
    llm_timeout_sec: float = 60.0
    llm_retries: int = 3
    llm_temperature: float = 0.2
    market_timeout_sec: float = 25.0
    max_ingest_age_hours: float = 24.0
    max_prompt_chars: int = 600_000
    log_retention_days: int = 60
    reverify: bool = False
    llm_verify: bool = False
    check_freshness: bool | None = None
    allow_price_only: bool = True
    show_additional: bool = True
    include_weak_index: bool = False
    streak_high_days: int = 3
    ratio_high: float = 1.5
    ratio_min_history: int = 5
    sector_parallel: int = 4
    live_parallel: int = 3
    live_max_minutes: int = 30
    live_cooldown_sec: int = 60
    cutoff_ist: str | None = None
    news_window_days: int = 7
    max_clusters: int = 12
    per_cluster_articles: int = 4
    body_max_words: int = 110
    body_max_sentences: int = 5
    log_full_prompts: bool = False


def load_config(env: Mapping[str, str] | None = None) -> CommonConfig:
    source: Mapping[str, str] = os.environ if env is None else env
    data_dir = Path(source.get("INSIGHTS_DATA_DIR") or (_REPO_ROOT / "data" / "ai_insights"))
    holidays = Path(source.get("INSIGHTS_HOLIDAYS_PATH") or (data_dir / "_data" / "nse_holidays.json"))
    log_dir = Path(source.get("INSIGHTS_LOG_DIR") or (data_dir / "logs"))
    cutoff = str(source.get("INSIGHTS_CUTOFF_IST") or "").strip() or None
    if cutoff is not None:
        parts = cutoff.split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError(f"INSIGHTS_CUTOFF_IST must be HH:MM, got {cutoff!r}")
    return CommonConfig(
        data_dir=data_dir,
        holidays_path=holidays,
        log_dir=log_dir,
        llm_provider=str(source.get("INSIGHTS_LLM_PROVIDER") or "anthropic").strip().lower(),
        llm_model=str(source.get("INSIGHTS_LLM_MODEL") or "claude-haiku-5-5").strip(),
        llm_timeout_sec=_float(source, "INSIGHTS_LLM_TIMEOUT_SEC", 60.0),
        llm_retries=_int(source, "INSIGHTS_LLM_RETRIES", 3),
        llm_temperature=_float(source, "INSIGHTS_LLM_TEMPERATURE", 0.2),
        market_timeout_sec=_float(source, "INSIGHTS_MARKET_TIMEOUT_SEC", 25.0),
        max_ingest_age_hours=_float(source, "INSIGHTS_MAX_INGEST_AGE_HOURS", 24.0),
        max_prompt_chars=_int(source, "INSIGHTS_MAX_PROMPT_CHARS", 600_000),
        log_retention_days=_int(source, "INSIGHTS_LOG_RETENTION_DAYS", 60),
        reverify=_bool(source, "INSIGHTS_REVERIFY", False),
        llm_verify=_bool(source, "INSIGHTS_LLM_VERIFY", False),
        check_freshness=_freshness_flag(source),
        allow_price_only=_bool(source, "INSIGHTS_ALLOW_PRICE_ONLY", True),
        show_additional=_bool(source, "INSIGHTS_SHOW_ADDITIONAL", True),
        include_weak_index=_bool(source, "INSIGHTS_INCLUDE_WEAK_INDEX", False),
        streak_high_days=_int(source, "INSIGHTS_STREAK_HIGH_DAYS", 3),
        ratio_high=_float(source, "INSIGHTS_RATIO_HIGH", 1.5),
        ratio_min_history=_int(source, "INSIGHTS_RATIO_MIN_HISTORY", 5),
        sector_parallel=_int(source, "INSIGHTS_SECTOR_PARALLEL", 4),
        live_parallel=_int(source, "INSIGHTS_LIVE_PARALLEL", 3),
        live_max_minutes=_int(source, "INSIGHTS_LIVE_MAX_MINUTES", 30),
        live_cooldown_sec=_int(source, "INSIGHTS_LIVE_COOLDOWN_SEC", 60),
        cutoff_ist=cutoff,
        news_window_days=_int(source, "INSIGHTS_NEWS_WINDOW_DAYS", 7),
        max_clusters=_int(source, "INSIGHTS_MAX_CLUSTERS", 12),
        per_cluster_articles=_int(source, "INSIGHTS_PER_CLUSTER_ARTICLES", 4),
        body_max_words=_int(source, "INSIGHTS_BODY_MAX_WORDS", 110),
        body_max_sentences=_int(source, "INSIGHTS_BODY_MAX_SENTENCES", 5),
        log_full_prompts=_bool(source, "INSIGHTS_LOG_FULL_PROMPTS", False),
    )
