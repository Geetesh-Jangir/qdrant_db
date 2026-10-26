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

    # Insight LLM: anthropic (default), gemini, or deepseek. Gemini is the fallback when primary fails.
    rag_llm_provider: str = Field(
        default="anthropic",
        validation_alias=AliasChoices("RAG_LLM_PROVIDER", "rag_llm_provider"),
    )
    # Agent-1: cheap JSON router after fast paths (flash-lite). Set false for rules-only.
    rag_use_llm_router: bool = Field(
        default=True,
        validation_alias=AliasChoices("RAG_USE_LLM_ROUTER", "rag_use_llm_router"),
    )

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    # Reasoning tokens count against max_tokens and truncate small JSON stages (brief, judge).
    # Keep off for structured-JSON stages; set DEEPSEEK_THINKING=true only for free-form answers.
    deepseek_thinking: bool = Field(
        default=False,
        validation_alias=AliasChoices("DEEPSEEK_THINKING", "deepseek_thinking"),
    )

    anthropic_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "anthropic_api_key"),
    )
    anthropic_model: str = Field(
        default="claude-haiku-5-5",
        validation_alias=AliasChoices("ANTHROPIC_MODEL", "anthropic_model"),
    )
    # Haiku 5.5 thinks by default and thinking tokens eat max_tokens (replies cut off before any text).
    anthropic_thinking: bool = Field(
        default=False,
        validation_alias=AliasChoices("ANTHROPIC_THINKING", "anthropic_thinking"),
    )
    # low | medium | high (thinking can only be disabled at high or below)
    anthropic_effort: str = Field(
        default="medium",
        validation_alias=AliasChoices("ANTHROPIC_EFFORT", "anthropic_effort"),
    )
    anthropic_base_url: str = Field(
        default="https://api.anthropic.com",
        validation_alias=AliasChoices("ANTHROPIC_BASE_URL", "anthropic_base_url"),
    )

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_composer_model: str = "gemini-3.5-flash-lite"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # Dedicated cheap model for query routing and answer contract planning (default: flash-lite)
    rag_router_model: str = ""
    rag_contract_model: str = ""
    router_max_tokens: int = 600
    ask_agent_max_tokens: int = 2500
    ask_agent_max_rounds: int = 3
    contract_max_tokens: int = 800

    llm_max_tokens: int = Field(
        default=2000,
        validation_alias=AliasChoices("LLM_MAX_TOKENS", "DEEPSEEK_MAX_TOKENS"),
    )
    # None or 0 = no HTTP timeout on LLM requests (wait until the provider responds).
    llm_http_timeout_sec: float | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_HTTP_TIMEOUT_SEC", "llm_http_timeout_sec"),
    )

    app_token: str = ""
    entity_cache_hours: float = 4.0
    default_window_days: int = 7
    retrieve_vector_limit: int = 60
    retrieve_impact_limit: int = 60
    retrieve_max_articles: int = 30
    snippet_chars: int = 2500
    insight_max_bullets: int = 5
    insight_bullet_max_chars: int = 0  # 0 = no character cap on insight bullets (fund brief path)
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

    fund_fuzzy_accept: float = 88.0
    fund_fuzzy_reject: float = 75.0
    fund_fuzzy_ambiguous_gap: float = 5.0
    retrieve_min_vector_score: float = 0.35
    tool_timeout_sec: float = 25.0
    judge_min_score: float = 0.65
    # Ignored: v1 ask path removed. Kept so old .env values do not break startup.
    ask_pipeline_v2: bool = Field(
        default=True,
        validation_alias=AliasChoices("ASK_PIPELINE_V2", "ask_pipeline_v2"),
    )

    # ── New ask pipeline: bounded two-wave orchestration ──
    max_tool_waves: int = Field(
        default=2,
        validation_alias=AliasChoices("MAX_TOOL_WAVES", "max_tool_waves"),
    )
    max_targeted_recovery_calls: int = Field(
        default=1,
        validation_alias=AliasChoices("MAX_TARGETED_RECOVERY_CALLS", "max_targeted_recovery_calls"),
    )
    max_repair_passes: int = Field(
        default=1,
        validation_alias=AliasChoices("MAX_REPAIR_PASSES", "max_repair_passes"),
    )
    max_extra_actions: int = Field(
        default=2,
        validation_alias=AliasChoices("MAX_EXTRA_ACTIONS", "max_extra_actions"),
    )
    # Per-query-class deadline budgets (ms)
    request_deadline_simple_ms: int = Field(
        default=8000,
        validation_alias=AliasChoices("REQUEST_DEADLINE_SIMPLE_MS", "request_deadline_simple_ms"),
    )
    request_deadline_standard_ms: int = Field(
        default=20000,
        validation_alias=AliasChoices("REQUEST_DEADLINE_STANDARD_MS", "request_deadline_standard_ms"),
    )
    request_deadline_complex_ms: int = Field(
        default=45000,
        validation_alias=AliasChoices("REQUEST_DEADLINE_COMPLEX_MS", "request_deadline_complex_ms"),
    )
    # Per-phase timeouts (ms)
    planner_timeout_ms: int = Field(
        default=6000,
        validation_alias=AliasChoices("PLANNER_TIMEOUT_MS", "planner_timeout_ms"),
    )
    composer_timeout_ms: int = Field(
        default=12000,
        validation_alias=AliasChoices("COMPOSER_TIMEOUT_MS", "composer_timeout_ms"),
    )
    judge_timeout_ms: int = Field(
        default=8000,
        validation_alias=AliasChoices("JUDGE_TIMEOUT_MS", "judge_timeout_ms"),
    )
    tool_timeout_ms: int = Field(
        default=10000,
        validation_alias=AliasChoices("TOOL_TIMEOUT_MS", "tool_timeout_ms"),
    )
    max_concurrent_tools: int = Field(
        default=8,
        validation_alias=AliasChoices("MAX_CONCURRENT_TOOLS", "max_concurrent_tools"),
    )
    # Cache TTLs (seconds)
    fund_cache_ttl: int = Field(
        default=300,
        validation_alias=AliasChoices("FUND_CACHE_TTL", "fund_cache_ttl"),
    )
    news_cache_ttl: int = Field(
        default=180,
        validation_alias=AliasChoices("NEWS_CACHE_TTL", "news_cache_ttl"),
    )
    news_top_k: int = Field(
        default=6,
        validation_alias=AliasChoices("NEWS_TOP_K", "news_top_k"),
    )
    # Prompt versioning for cache-friendly prefixes
    prompt_version: str = Field(
        default="v3.0",
        validation_alias=AliasChoices("PROMPT_VERSION", "prompt_version"),
    )
    # Slot router confidence threshold (above → deterministic, below → planner LLM)
    slot_router_confidence: float = Field(
        default=0.8,
        validation_alias=AliasChoices("SLOT_ROUTER_CONFIDENCE", "slot_router_confidence"),
    )

    insight_fan_out_cap: int = Field(
        default=8,
        validation_alias=AliasChoices("INSIGHT_FAN_OUT_CAP", "insight_fan_out_cap"),
    )
    insight_driven_by_share_pct: float = Field(
        default=35.0,
        validation_alias=AliasChoices("INSIGHT_DRIVEN_BY_SHARE_PCT", "insight_driven_by_share_pct"),
    )
    insight_use_llm_interpret: bool = Field(
        default=True,
        validation_alias=AliasChoices("INSIGHT_USE_LLM_INTERPRET", "insight_use_llm_interpret"),
    )
    insight_use_llm_news_reader: bool = Field(
        default=True,
        validation_alias=AliasChoices("INSIGHT_USE_LLM_NEWS_READER", "insight_use_llm_news_reader"),
    )
    insight_use_llm_analyst: bool = Field(
        default=True,
        validation_alias=AliasChoices("INSIGHT_USE_LLM_ANALYST", "insight_use_llm_analyst"),
    )
    insight_llm_article_chars: int = Field(
        default=6000,
        validation_alias=AliasChoices("INSIGHT_LLM_ARTICLE_CHARS", "insight_llm_article_chars"),
    )
    insight_composer_max_articles: int = Field(
        default=8,
        validation_alias=AliasChoices("INSIGHT_COMPOSER_MAX_ARTICLES", "insight_composer_max_articles"),
    )
    # Bodies kept for the composer after the news reader has already digested the rest.
    insight_composer_body_articles: int = Field(
        default=4,
        validation_alias=AliasChoices("INSIGHT_COMPOSER_BODY_ARTICLES", "insight_composer_body_articles"),
    )
    insight_pulse_vector_limit: int = Field(
        default=24,
        validation_alias=AliasChoices("INSIGHT_PULSE_VECTOR_LIMIT", "insight_pulse_vector_limit"),
    )
    insight_json_tool_use: bool = Field(
        default=True,
        validation_alias=AliasChoices("INSIGHT_JSON_TOOL_USE", "insight_json_tool_use"),
    )
    insight_brief_tiering: bool = Field(
        default=True,
        validation_alias=AliasChoices("INSIGHT_BRIEF_TIERING", "insight_brief_tiering"),
    )
    insight_prune_market_facets: bool = Field(
        default=True,
        validation_alias=AliasChoices("INSIGHT_PRUNE_MARKET_FACETS", "insight_prune_market_facets"),
    )
    insight_sector_candidate_cap: int = Field(
        default=50,
        validation_alias=AliasChoices("INSIGHT_SECTOR_CANDIDATE_CAP", "insight_sector_candidate_cap"),
    )
    insight_analyst_mode: str = Field(
        default="auto",
        validation_alias=AliasChoices("INSIGHT_ANALYST_MODE", "insight_analyst_mode"),
    )
    # Plan-driven node graph: one planner call chooses tools, window, news depth and answer style.
    insight_graph_pipeline: bool = Field(
        default=True,
        validation_alias=AliasChoices("INSIGHT_GRAPH_PIPELINE", "insight_graph_pipeline"),
    )
    insight_graph_news_chars: int = Field(
        default=1400,
        validation_alias=AliasChoices("INSIGHT_GRAPH_NEWS_CHARS", "insight_graph_news_chars"),
    )
    insight_verify_retry: bool = Field(
        default=True,
        validation_alias=AliasChoices("INSIGHT_VERIFY_RETRY", "insight_verify_retry"),
    )
    insight_use_news_digest: bool = Field(
        default=True,
        validation_alias=AliasChoices("INSIGHT_USE_NEWS_DIGEST", "insight_use_news_digest"),
    )
    rag_warmup_embeddings: bool = Field(
        default=True,
        validation_alias=AliasChoices("RAG_WARMUP_EMBEDDINGS", "rag_warmup_embeddings"),
    )
    max_concurrent_tools: int = Field(
        default=4,
        validation_alias=AliasChoices("MAX_CONCURRENT_TOOLS", "max_concurrent_tools"),
    )
    request_deadline_simple_ms: float = Field(
        default=20000.0,
        validation_alias=AliasChoices("REQUEST_DEADLINE_SIMPLE_MS", "request_deadline_simple_ms"),
    )
    request_deadline_standard_ms: float = Field(
        default=40000.0,
        validation_alias=AliasChoices("REQUEST_DEADLINE_STANDARD_MS", "request_deadline_standard_ms"),
    )
    request_deadline_complex_ms: float = Field(
        default=60000.0,
        validation_alias=AliasChoices("REQUEST_DEADLINE_COMPLEX_MS", "request_deadline_complex_ms"),
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
