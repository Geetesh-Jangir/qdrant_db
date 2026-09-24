"""RAG app settings — separate from news_pipeline; reads repo .env or news_rag/.env."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parents[1]

# Must match news ingest (BGE small + query prefix).
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT / ".env"), str(_ROOT / "news_rag" / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "news_articles"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    deepseek_max_tokens: int = 2000

    app_token: str = ""
    entity_cache_hours: float = 4.0
    default_window_days: int = 7
    retrieve_vector_limit: int = 15
    retrieve_impact_limit: int = 15
    retrieve_max_articles: int = 8
    snippet_chars: int = 1500
    insight_max_bullets: int = 3
    insight_bullet_max_chars: int = 220
    insight_summary_max_words: int = 55
    min_relevance: int = 2
    embedding_model: str = EMBEDDING_MODEL
    embedding_cache_dir: str = "data/embedding_models"
    rag_query_log_dir: str = "data/rag_query_logs"

    def embedding_cache_path(self) -> Path:
        path = _ROOT / self.embedding_cache_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    def rag_query_log_path(self) -> Path:
        path = _ROOT / self.rag_query_log_dir
        path.mkdir(parents=True, exist_ok=True)
        return path


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
