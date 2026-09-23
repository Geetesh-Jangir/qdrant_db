"""Thresholds, publishers, sector queries, and environment settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Publisher:
    domain: str
    names: tuple[str, ...]


@dataclass(frozen=True)
class SectorQuery:
    query: str
    keywords: tuple[str, ...]


PUBLISHERS: tuple[Publisher, ...] = (
    Publisher("economictimes.indiatimes.com", ("economic times",)),
    Publisher("livemint.com", ("livemint", "mint")),
    Publisher("business-standard.com", ("business standard",)),
    Publisher("moneycontrol.com", ("moneycontrol",)),
    Publisher("thehindubusinessline.com", ("businessline", "hindu business line")),
    Publisher("financialexpress.com", ("financial express",)),
    Publisher("reuters.com", ("reuters",)),
    Publisher("bloomberg.com", ("bloomberg",)),
    Publisher("cnbctv18.com", ("cnbc-tv18", "cnbc tv18", "cnbctv18")),
    Publisher("ndtvprofit.com", ("ndtv profit",)),
)

# Google queries are phrases, not the raw sector label. Keywords are the
# alias gate for sector stories: the title or snippet must contain one of them.
SECTOR_QUERIES: dict[str, SectorQuery] = {
    "Banks": SectorQuery("RBI credit growth India", ("bank", "rbi", "npa", "credit growth", "lending")),
    "Pharmaceuticals & Biotechnology": SectorQuery("Indian pharma USFDA", ("pharma", "drug", "usfda", "biotech")),
    "It - Software": SectorQuery("Indian IT sector results", ("it sector", "it services", "software services", "software")),
    "Finance": SectorQuery("NBFC India RBI", ("nbfc", "finance company", "lending")),
    "Capital Markets": SectorQuery("Indian stock exchange SEBI", ("sebi", "stock exchange", "brokerage", "capital market")),
    "Automobiles": SectorQuery("auto sales India", ("automobile", "carmaker", "passenger vehicle", "auto sales")),
    "Auto Components": SectorQuery("auto ancillary India", ("auto component", "auto parts", "ancillary")),
    "Retailing": SectorQuery("Indian retail sector", ("retail", "retailer")),
    "Electrical Equipment": SectorQuery("electrical equipment India orders", ("electrical equipment", "transformer", "switchgear")),
    "Consumer Durables": SectorQuery("consumer durables India", ("consumer durable", "appliance")),
    "Industrial Products": SectorQuery("capital goods India orders", ("capital goods", "industrial product")),
    "Petroleum Products": SectorQuery("crude oil India OMC", ("crude", "oil marketing", "refinery", "petrol", "diesel")),
    "Telecom - Services": SectorQuery("telecom ARPU India", ("telecom", "arpu", "spectrum")),
    "Power": SectorQuery("power sector India electricity", ("power sector", "electricity", "discom")),
    "Healthcare Services": SectorQuery("Indian hospital sector", ("hospital", "healthcare", "diagnostic")),
    "Construction": SectorQuery("infrastructure order India construction", ("construction", "epc", "infrastructure order")),
    "Chemicals & Petrochemicals": SectorQuery("Indian chemical sector", ("chemical", "petrochemical")),
    "Realty": SectorQuery("Indian real estate sector", ("real estate", "realty", "property")),
    "Insurance": SectorQuery("Indian insurance sector", ("insurance", "insurer")),
    "Aerospace & Defense": SectorQuery("India defence orders", ("defence", "defense", "aerospace")),
    "Diversified Fmcg": SectorQuery("FMCG India demand", ("fmcg", "consumer goods")),
    "Financial Technology (fintech)": SectorQuery("India fintech", ("fintech", "payments")),
    "Transport Services": SectorQuery("aviation shipping India", ("airline", "aviation", "shipping", "logistics")),
    "Cement & Cement Products": SectorQuery("cement prices India", ("cement",)),
    "Food Products": SectorQuery("packaged food India", ("packaged food", "food product", "dairy")),
    "Ferrous Metals": SectorQuery("steel prices India", ("steel", "ferrous")),
    "Non - Ferrous Metals": SectorQuery("aluminium copper prices India", ("aluminium", "aluminum", "copper", "zinc")),
    "Leisure Services": SectorQuery("hotels travel India", ("hotel", "travel", "leisure")),
    "Beverages": SectorQuery("beverage sector India", ("beverage", "brewery", "spirits")),
    "Agricultural, Commercial & Construction Vehicles": SectorQuery(
        "tractor commercial vehicle India",
        ("tractor", "commercial vehicle", "cv sales"),
    ),
}

SECTOR_BLOCK_FRAGMENTS: tuple[str, ...] = (
    "mutual fund",
    "etf",
    "foreign security",
    "index future",
    "overseas",
    "reit",
    "invit",
    "precious metal",
    "others",
)

# Headlines shorten these names. Key is the canonical name key from universe.canonical_key.
EXTRA_ALIASES: dict[str, tuple[str, ...]] = {
    "state bank of india": ("SBI",),
    "oil and natural gas corporation": ("ONGC",),
    "life insurance corporation of india": ("LIC",),
    "bharat heavy electricals": ("BHEL",),
    "hindustan aeronautics": ("HAL",),
    "bharat petroleum corporation": ("BPCL",),
    "indian oil corporation": ("IOC", "Indian Oil"),
    "hindustan petroleum corporation": ("HPCL",),
    "power grid corporation of india": ("Power Grid",),
}

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

DIRECTION_OPTIONS: tuple[str, ...] = ("positive", "negative", "neutral", "unclear")
EVENT_OPTIONS: tuple[str, ...] = (
    "results",
    "order",
    "deal",
    "regulatory",
    "operations",
    "macro",
    "opinion",
    "price_recap",
)

RELEVANCE_LEVELS: tuple[str, ...] = (
    "Unrelated to this name",
    "Name is only mentioned in passing",
    "About this name but not material to the outlook",
    "Material to this name today",
    "Major event for this name such as results, a ban, a large order, or a regulatory action",
)

IMPACT_LEVELS: tuple[str, ...] = (
    "No impact on the outlook",
    "Color only, such as a small price move with no new fact",
    "Could move this name today",
    "Likely to move this name",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(repo_root() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    collection_name: str = "news_articles"

    jev_base_url: str = ""
    jev_api_key: str = ""
    jev_model: str = "jev-latest"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    holdings_limit: int = 5
    sectors_limit: int = 5
    title_noul_min: float = 0.7
    about_name_min: float = 0.7
    relevance_min: int = 2
    max_scrape_per_entity: int = 5
    max_titles_per_jev_call: int = 40
    max_items_per_query: int = 20
    title_similarity: int = 80
    recent_title_hours: int = 48
    min_body_chars: int = 400
    embed_chars: int = 1500
    body_words: int = 2000
    retention_days: int = 180
    news_window_hours: int = 24
    fetch_workers: int = 2
    scrape_workers: int = 4
    upsert_batch: int = 128
    embed_batch: int = 32

    holdings_csv: str = "data/fund_holdings_aggregate/aggregated_holdings.csv"
    sectors_csv: str = "data/fund_holdings_aggregate/aggregated_sectors.csv"
    run_summary_dir: str = "data/news_runs"
    qdrant_inspect_dir: str = "data/qdrant_inspect"
    scrape_workspace_dir: str = "data/news_scrape_cache"
    jev_input_cost_per_million_usd: float = 0.042
    fresh_start_each_run: bool = True
    fresh_start_clear_qdrant: bool = True

    def path(self, relative: str) -> Path:
        return repo_root() / relative
