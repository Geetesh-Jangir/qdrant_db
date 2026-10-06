"""RAG app settings — separate from news_pipeline; reads repo .env or news_rag/.env."""

from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
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

    # Insight LLM: set RAG_LLM_PROVIDER=gemini or deepseek (default gemini).
    rag_llm_provider: str = "gemini"
    # Agent-1: cheap JSON router after fast paths (flash-lite). Set false for rules-only.
    rag_use_llm_router: bool = Field(
        default=True,
        validation_alias=AliasChoices("RAG_USE_LLM_ROUTER", "rag_use_llm_router"),
    )

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # Dedicated cheap model for query routing and answer contract planning (default: flash-lite)
    rag_router_model: str = ""
    rag_contract_model: str = ""
    router_max_tokens: int = 600
    contract_max_tokens: int = 800

    llm_max_tokens: int = Field(
        default=2000,
        validation_alias=AliasChoices("LLM_MAX_TOKENS", "DEEPSEEK_MAX_TOKENS"),
    )

    app_token: str = ""
    entity_cache_hours: float = 4.0
    default_window_days: int = 7
    retrieve_vector_limit: int = 60
    retrieve_impact_limit: int = 60
    retrieve_max_articles: int = 30
    snippet_chars: int = 2500
    insight_max_bullets: int = 5
    insight_bullet_max_chars: int = 600
    insight_summary_max_words: int = 300
    min_relevance: int = 2
    embedding_model: str = EMBEDDING_MODEL
    embedding_cache_dir: str = "data/embedding_models"
    huggingface_token: str = Field(
        default="",
        validation_alias=AliasChoices(
            "HUGGINGFACE_TOKEN",
            "HF_TOKEN",
            "HUGGINGFACE_HUB_TOKEN",
            "HUGGING_FACE_HUB_TOKEN",
        ),
    )
    rag_query_log_dir: str = "data/rag_query_logs"

    # Investor portfolio file is NOT used by /api/ask (hypothetical "my portfolio" in questions only).
    # Optional legacy hook for fund-brief; leave empty unless you explicitly opt in via PORTFOLIO_JSON.
    portfolio_json: str = ""
    funds_by_amc_md: str = "data/fund_holdings_aggregate/regular-growth-by-amc.md"
    allisin_sectors_holdings_json: str = "data/fund_holdings_aggregate/allisin_sectors_with_holdings.json"
    portfolio_allisin_holdings_json: str = "data/fund_holdings_aggregate/portfolio_allisin_holdings.json"
    portfolio_manifest_path: str = "data/fund_holdings_aggregate/portfolio_news_scope.json"
    portfolio_holding_min_pct: float = 2.0
    portfolio_sector_min_pct: float = 3.0
    aggregated_holdings_map: str = "data/fund_holdings_aggregate/aggregated_holdings_map.json"
    aggregated_holdings_csv: str = "data/fund_holdings_aggregate/aggregated_holdings.csv"
    sector_to_isin_weights_json: str = "data/fund_holdings_aggregate/sector_to_isin_weights.json"
    impact_ranking_regular_growth_only: bool = True

    # Legacy flag; /api/ask always uses the LLM ask engine.
    rag_use_ask_engine: bool = Field(
        default=True,
        validation_alias=AliasChoices("RAG_USE_ASK_ENGINE", "rag_use_ask_engine"),
    )
    rag_unified_compose: bool = Field(
        default=True,
        validation_alias=AliasChoices("RAG_UNIFIED_COMPOSE", "rag_unified_compose"),
    )
    fund_fuzzy_accept: float = 88.0
    fund_fuzzy_reject: float = 75.0
    fund_fuzzy_ambiguous_gap: float = 5.0
    retrieve_min_vector_score: float = 0.35
    tool_timeout_sec: float = 25.0
    judge_min_score: float = 0.65
    rag_warmup_embeddings: bool = Field(
        default=True,
        validation_alias=AliasChoices("RAG_WARMUP_EMBEDDINGS", "rag_warmup_embeddings"),
    )

    def embedding_cache_path(self) -> Path:
        path = _ROOT / self.embedding_cache_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    def rag_query_log_path(self) -> Path:
        path = _ROOT / self.rag_query_log_dir
        path.mkdir(parents=True, exist_ok=True)
        return path


def get_settings() -> Settings:
    return Settings()
