"""Thresholds, publishers, sector queries, and environment settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
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
    exclude: tuple[str, ...] = ()
    min_hits: int = 1


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
    "Banks": SectorQuery(
        "RBI credit growth India",
        ("bank", "rbi", "npa", "credit growth", "bank lending"),
        exclude=("nbfc", "fintech", "housing finance", "microfinance"),
    ),
    "Pharmaceuticals & Biotechnology": SectorQuery("Indian pharma USFDA", ("pharma", "drug", "usfda", "biotech")),
    "It - Software": SectorQuery("Indian IT sector results", ("it sector", "it services", "software services", "software")),
    "Finance": SectorQuery(
        "NBFC India RBI",
        ("nbfc", "finance company", "housing finance", "microfinance"),
        exclude=("scheduled commercial bank", "public sector bank", "private sector bank"),
    ),
    "Capital Markets": SectorQuery("Indian stock exchange SEBI", ("sebi", "stock exchange", "brokerage", "capital market")),
    "Automobiles": SectorQuery("auto sales India", ("automobile", "carmaker", "passenger vehicle", "auto sales")),
    "Auto Components": SectorQuery(
        "auto ancillary India",
        ("auto component", "auto parts", "ancillary"),
        exclude=("capital goods order",),
    ),
    "Retailing": SectorQuery(
        "Indian retail sector",
        ("retail", "retailer"),
        exclude=("retail inflation", "cpi"),
    ),
    "Electrical Equipment": SectorQuery(
        "electrical equipment India orders",
        ("electrical equipment", "transformer", "switchgear"),
        exclude=("auto component", "auto parts"),
    ),
    "Consumer Durables": SectorQuery("consumer durables India", ("consumer durable", "appliance")),
    "Industrial Products": SectorQuery(
        "capital goods India orders",
        ("industrial product", "bearings", "capital goods order"),
        exclude=("transformer", "switchgear", "auto component", "auto parts"),
        min_hits=1,
    ),
    "Petroleum Products": SectorQuery("crude oil India OMC", ("crude", "oil marketing", "refinery", "petrol", "diesel")),
    "Telecom - Services": SectorQuery(
        "telecom ARPU India",
        ("telecom operator", "telecom tariff", "arpu", "spectrum"),
    ),
    "Power": SectorQuery("power sector India electricity", ("power sector", "electricity", "discom")),
    "Healthcare Services": SectorQuery("Indian hospital sector", ("hospital", "healthcare", "diagnostic")),
    "Construction": SectorQuery("infrastructure order India construction", ("construction", "epc", "infrastructure order")),
    "Chemicals & Petrochemicals": SectorQuery("Indian chemical sector", ("chemical", "petrochemical")),
    "Realty": SectorQuery("Indian real estate sector", ("real estate", "realty", "property")),
    "Insurance": SectorQuery(
        "Indian insurance sector",
        ("insurance sector", "insurer", "life insurance", "general insurance"),
    ),
    "Aerospace & Defense": SectorQuery("India defence orders", ("defence", "defense", "aerospace")),
    "Diversified Fmcg": SectorQuery("FMCG India demand", ("fmcg", "consumer goods")),
    "Financial Technology (fintech)": SectorQuery(
        "India fintech",
        ("fintech", "digital payments", "upi"),
        exclude=("nbfc", "housing finance", "microfinance"),
    ),
    "Transport Services": SectorQuery("aviation shipping India", ("airline", "aviation", "shipping", "logistics")),
    "Cement & Cement Products": SectorQuery("cement prices India", ("cement",)),
    "Food Products": SectorQuery("packaged food India", ("packaged food", "food product", "dairy")),
    "Ferrous Metals": SectorQuery(
        "steel prices India",
        ("steel price", "steel demand", "steelmaker", "ferrous"),
    ),
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

# Sector bellwethers (market leaders and dominant players) for sector read-throughs
SECTOR_BELLWETHERS: dict[str, str] = {
    "Banks": "HDFC Bank, State Bank of India (SBI), ICICI Bank, Axis Bank, Kotak Mahindra Bank",
    "Finance": "Bajaj Finance, Jio Financial, Shriram Finance, Chola Investment",
    "It - Software": "TCS, Infosys, HCL Tech, Wipro, Tech Mahindra",
    "Automobiles": "Tata Motors, Maruti Suzuki, Mahindra & Mahindra (M&M), Bajaj Auto, Hero MotoCorp",
    "Auto Components": "Samvardhana Motherson, Bosch, Bharat Forge, Sona BLW",
    "Pharmaceuticals & Biotechnology": "Sun Pharma, Dr. Reddy's, Cipla, Divi's Lab, Lupin",
    "Petroleum Products": "Reliance Industries (RIL), ONGC, Indian Oil (IOC), BPCL, HPCL",
    "Telecom - Services": "Bharti Airtel, Reliance Jio, Vodafone Idea",
    "Power": "NTPC, Power Grid, Tata Power, Adani Power",
    "Construction": "Larsen & Toubro (L&T), NCC, IRB Infrastructure",
    "Realty": "DLF, Macrotech (Lodha), Godrej Properties, Oberoi Realty",
    "Cement & Cement Products": "UltraTech Cement, Ambuja Cements, ACC, Shree Cement",
    "Ferrous Metals": "Tata Steel, JSW Steel, Jindal Steel & Power, SAIL",
    "Non - Ferrous Metals": "Hindalco, Vedanta, Hindustan Zinc, National Aluminium (NALCO)",
    "Chemicals & Petrochemicals": "SRF, PI Industries, Aarti Industries, Gujarat Fluorochemicals",
    "Capital Markets": "BSE, NSE, MCX, CDSL, Angel One",
    "Insurance": "LIC, HDFC Life, SBI Life, ICICI Prudential Life, ICICI Lombard",
    "Retailing": "Trent, Avenue Supermarts (DMart), Titan Company",
    "Consumer Durables": "Havells, Voltas, Dixon Technologies, Whirlpool",
    "Diversified Fmcg": "Hindustan Unilever (HUL), ITC, Nestle India, Britannia, Godrej Consumer",
    "Food Products": "Nestle India, Britannia, Varun Beverages, Bikaji, Hatsun Agro",
    "Aerospace & Defense": "Hindustan Aeronautics (HAL), Bharat Electronics (BEL), Mazagon Dock, Cochin Shipyard",
    "Transport Services": "InterGlobe Aviation (IndiGo), Container Corporation (CONCOR), Delhivery",
    "Healthcare Services": "Apollo Hospitals, Max Healthcare, Fortis Healthcare, Medanta",
}

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

HIGH_IMPACT_MACRO_KEYWORDS: tuple[str, ...] = (
    # Commodities
    "crude oil",
    "brent crude",
    "natural gas",
    "coal",
    "gold",
    "silver",
    "copper",
    "iron ore",
    "steel",

    # Currency
    "usd/inr",
    "rupee depreciation",
    "rupee appreciation",

    # Interest rates / monetary policy
    "rbi",
    "repo rate",
    "interest rate",
    "rate cut",
    "rate hike",
    "federal reserve",
    "fed",

    # Inflation / economy
    "inflation",
    "cpi",
    "gdp",
    "pmi",

    # Bonds
    "10-year g-sec",
    "bond yield",
    "us treasury yield",

    # Government / trade
    "tariff",
    "trade war",
    "fiscal deficit",

    # Geopolitics / supply shocks
    "sanctions",
    "supply disruption",
)

MACRO_QUERY_CLUSTERS: tuple[str, ...] = (
    "India crude oil brent natural gas coal steel gold copper commodity prices",
    "USD INR rupee depreciation appreciation 10-year g-sec bond yield US treasury",
    "RBI repo rate cut rate hike interest rates inflation CPI GDP PMI federal reserve",
    "India tariffs trade war fiscal deficit sanctions supply disruption economy",
)

MACRO_ENTITIES: tuple[dict[str, str], ...] = (
    {"name": "Macro - Gold", "query": "Gold price India MCX bullion"},
    {"name": "Macro - Silver", "query": "Silver price India MCX bullion"},
    {"name": "Macro - Crude Oil", "query": "Crude oil Brent prices India fuel"},
    {"name": "Macro - Natural Gas", "query": "Natural gas prices India PNG CNG"},
    {"name": "Macro - Rupee / USD", "query": "USD INR Rupee exchange rate currency"},
    {"name": "Macro - Bond Yields", "query": "India 10-year benchmark bond yield G-sec"},
    {"name": "Macro - RBI Repo Rate", "query": "RBI repo rate monetary policy committee MPC"},
    {"name": "Macro - Inflation (CPI)", "query": "India CPI retail inflation food prices"},
    {"name": "Macro - GDP & Economy", "query": "India GDP growth economic outlook"},
    {"name": "Macro - Tariffs & Trade", "query": "India trade deficit export import tariffs"},
    {"name": "Macro - SEBI", "query": "SEBI India capital markets regulator circular"},
    {"name": "Macro - Nifty 50", "query": "Nifty 50 index India stock market"},
    {"name": "Macro - Sensex", "query": "Sensex BSE index India stock market"},
    {"name": "Macro - Bank Nifty", "query": "Bank Nifty index India banking stocks"},
    {"name": "Macro - FII DII Flows", "query": '"FII DII" OR "foreign investors" stock market India'},
    {"name": "Macro - India VIX", "query": '"India VIX" OR "volatility index" NSE'},
    {"name": "Macro - WPI Inflation", "query": '"WPI inflation" India wholesale prices'},
    {"name": "Macro - IIP", "query": '"IIP" OR "industrial production" India'},
    {"name": "Macro - GST Collections", "query": '"GST collections" India monthly'},
    {
        "name": "Macro - Geopolitical Risk",
        "query": 'war OR sanctions OR tariff OR conflict "stock market" OR "Indian markets"',
    },
)

# Extra Google News phrasings per entity (RSS returns a different top-N per phrasing; items are
# merged and de-duplicated by URL at fetch time). The primary query stays the first attempt.
MACRO_QUERY_VARIANTS: dict[str, tuple[str, ...]] = {
    "Macro - Nifty 50": (
        '"Nifty 50" OR "Nifty" stock market India',
        "Nifty closes OR ends OR settles Sensex",
        "Nifty today closing bell",
        "Nifty support resistance outlook week",
    ),
    "Macro - Bank Nifty": (
        '"Nifty Bank" OR "Bank Nifty"',
        "Nifty Bank index PSU private banks",
        "Nifty Bank record high OR falls HDFC ICICI SBI",
    ),
    "Macro - Sensex": (
        'Sensex BSE "stock market"',
        "Sensex Nifty closing bell",
        "Sensex points top gainers losers",
    ),
    "Macro - FII DII Flows": (
        "FPI outflow OR inflow Indian equities",
        "DII buying FII selling net crore",
        "NSDL FPI data month",
        "provisional data NSE FII net",
    ),
    "Macro - India VIX": (
        "India VIX fear gauge Nifty",
        "market volatility India VIX jumps OR falls",
        "India VIX volatility election OR budget OR Fed",
    ),
    "Macro - Crude Oil": (
        '"crude oil" OR "Brent" OR "WTI" India impact',
        "oil prices OMC OR rupee OR inflation Brent",
        "OPEC output cut Brent India import bill",
    ),
    "Macro - Rupee / USD": (
        'rupee OR "USD INR" "forex market"',
        "rupee closes against dollar RBI intervention",
        "rupee record low OR gains forex reserves",
    ),
    "Macro - Gold": ("gold prices safe haven India", "gold rate today MCX record"),
    "Macro - Silver": ("silver prices record MCX", "silver safe haven industrial demand India"),
    "Macro - Natural Gas": ("LNG imports India gas price hike", "APM gas price OR CNG price hike"),
    "Macro - RBI Repo Rate": (
        "RBI MPC policy decision repo rate",
        "RBI governor policy stance rate",
        "RBI policy minutes OR CRR OR liquidity",
    ),
    "Macro - Bond Yields": ("10-year G-Sec yield falls OR rises", "bond yields India US Treasury FPI debt"),
    "Macro - Inflation (CPI)": (
        '"CPI inflation" India OR "retail inflation"',
        "India retail inflation MOSPI data",
        "CPI inflation print food vegetable prices month",
    ),
    "Macro - WPI Inflation": (
        "wholesale inflation India MoCI data",
        "WPI inflation fuel manufactured products",
    ),
    "Macro - GDP & Economy": (
        '"India GDP" growth quarterly',
        "India GDP data MOSPI quarter",
        "GDP growth Q1 OR Q2 OR Q3 OR Q4 India estimate",
    ),
    "Macro - IIP": (
        "India factory output industrial production data",
        "IIP manufacturing mining electricity growth",
    ),
    "Macro - GST Collections": ("GST collection gross record crore", "GST revenue month finance ministry"),
    "Macro - SEBI": (
        "SEBI board meeting OR order OR norms",
        "SEBI new rules market regulator",
        "SEBI penalty OR ban OR consultation paper",
    ),
    "Macro - Tariffs & Trade": ("US tariffs India exports", "India trade deficit month commerce ministry"),
    "Macro - Geopolitical Risk": (
        "geopolitical tension markets crash OR selloff India",
        "Middle East OR Russia OR China tensions Sensex Nifty",
        "Red Sea OR Ukraine OR Taiwan oil markets India",
    ),
}

# Per-sector extra phrasings, same merge behaviour as MACRO_QUERY_VARIANTS.
SECTOR_QUERY_VARIANTS: dict[str, tuple[str, ...]] = {
    "Banks": ("bank credit deposit growth India", "Nifty Bank PSU banks NIM"),
    "Pharmaceuticals & Biotechnology": ("pharma exports USFDA approval India", "Nifty Pharma drug pricing NPPA"),
    "It - Software": ("Nifty IT TCS Infosys deal wins", "Indian IT services demand US clients"),
    "Finance": ("NBFC asset quality India", "housing finance microfinance RBI norms"),
    "Capital Markets": ("SEBI stock broker OR exchange rules", "demat accounts SIP flows India"),
    "Automobiles": ("Nifty Auto monthly sales", "passenger vehicle two-wheeler demand India"),
    "Auto Components": ("auto component makers demand India",),
    "Retailing": ("retail consumption demand India quick commerce",),
    "Electrical Equipment": ("power equipment transmission orders India",),
    "Consumer Durables": ("consumer durables demand AC OR appliances India",),
    "Industrial Products": ("industrial capex order inflow India",),
    "Petroleum Products": ("OMC marketing margin petrol diesel India", "refining margin GRM India"),
    "Telecom - Services": ("telecom tariff hike India Jio Airtel", "Vodafone Idea AGR spectrum"),
    "Power": ("India peak power demand discoms", "renewable capacity addition India"),
    "Healthcare Services": ("hospital chain occupancy ARPOB India",),
    "Construction": ("NHAI OR infra project awards India EPC",),
    "Chemicals & Petrochemicals": ("specialty chemicals demand exports India", "anti-dumping duty chemicals India"),
    "Realty": ("housing sales launches India real estate", "real estate prices demand top cities"),
    "Insurance": ("life insurers premium growth India", "IRDAI norms insurance"),
    "Aerospace & Defense": ("defence ministry contract HAL BEL", "defence exports indigenisation India"),
    "Diversified Fmcg": ("FMCG volume growth rural demand", "FMCG price hike input costs India"),
    "Financial Technology (fintech)": ("UPI transactions volume NPCI", "RBI fintech payments regulation"),
    "Transport Services": ("airline passenger traffic India DGCA", "port cargo logistics volumes India"),
    "Cement & Cement Products": ("cement demand volume price hike India",),
    "Food Products": ("dairy OR edible oil OR packaged food prices India",),
    "Ferrous Metals": ("steel safeguard duty imports India", "steel demand JSW Tata Steel realisation"),
    "Non - Ferrous Metals": ("aluminium copper LME India Hindalco Vedanta",),
    "Leisure Services": ("hotel occupancy room rates India travel demand",),
    "Beverages": ("liquor OR beer OR soft drinks demand India",),
    "Agricultural, Commercial & Construction Vehicles": ("tractor sales monsoon rural demand", "truck CV sales India"),
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
    "Unrelated or routine operational noise (e.g. weekend branch opening, holidays, minor customer notices)",
    "Name is only mentioned in passing with no business significance",
    "About this name or sector but low/temporary impact on earnings and outlook",
    "Material to this company or sector (meaningful operational, contract, regulatory, or financial development)",
    "Major event such as earnings surprise, regulatory sanction/approval, transformative order, or plant shutdown",
)

IMPACT_LEVELS: tuple[str, ...] = (
    "No material impact (temporary/routine operational news like Sunday branch opening or holiday schedule)",
    "Color only, such as minor price movement or routine management comments with no new material fact",
    "High impact: Meaningful state/national policy, earnings, major order, or regulatory shift that could move the stock outlook",
    "Very high impact: Transformative event likely to materially change earnings, valuation, risk, or business trajectory",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(repo_root() / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="before")
    @classmethod
    def _clean_empty_env_strings(cls, values: object) -> object:
        if isinstance(values, dict):
            cleaned = {}
            for k, v in values.items():
                if isinstance(v, str) and v.strip() == "":
                    # Allow specific string fields to remain empty if needed, but omit others so defaults apply
                    if k in {"qdrant_api_key", "jev_base_url", "jev_api_key", "portfolio_json"}:
                        cleaned[k] = ""
                    else:
                        continue
                else:
                    cleaned[k] = v
            return cleaned
        return values

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    collection_name: str = "news_articles"

    jev_base_url: str = ""
    jev_api_key: str = ""
    jev_model: str = "jev-latest"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
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

    holdings_limit: int = 5
    sectors_limit: int = 2
    title_noul_min: float = 0.5
    about_name_min: float = 0.7
    relevance_min: int = 2
    # 0 = no cap: scrape every title that passes title_noul_min (body Jev still gates Qdrant).
    max_scrape_per_entity: int = 0
    max_scrape_per_industry: int = 0
    max_titles_per_jev_call: int = 0
    macro_news_enabled: bool = True
    macro_news_query: str = "India RBI economy markets budget"
    # 0 = scan full RSS; keep every item that passes publisher/time/language/https filters.
    max_items_per_query: int = 0
    title_similarity: int = 80
    recent_title_hours: int = 720
    min_body_chars: int = 400
    embed_chars: int = 1500
    body_words: int = 2000
    # 0 = never delete by age. Ignored when news_corpus_mode is true.
    retention_days: int = 0
    # Accumulate articles in Qdrant across runs; skip retention deletes and never wipe the collection.
    news_corpus_mode: bool = True
    # Global title dedupe vs existing corpus. 0 hours = all stored articles; 0 limit = no cap.
    corpus_title_dedupe_hours: int = 0
    corpus_title_dedupe_limit: int = 0
    # Keep articles whose publish time is within this many hours (fetch + scrape). Env: NEWS_WINDOW_HOURS.
    # Ignored when news_date_range is set.
    news_window_hours: int = 720
    # Google News RSS search window suffix, e.g. 1d, 7d, 30d (without "when:"). Env: GOOGLE_NEWS_WHEN.
    # Ignored when news_date_range is set.
    google_news_when: str = "1d"
    # Inclusive start / exclusive end, e.g. 5/10/2026-7/10/2026 covers 5 Oct and 6 Oct.
    # Env: NEWS_DATE_RANGE. Empty = use google_news_when + news_window_hours (daily cron).
    news_date_range: str = ""
    fetch_workers: int = 1
    scrape_workers: int = 4
    scrape_domain_gap_sec: float = 0
    scrape_max_attempts: int = 3
    scrape_backoff_base_sec: float = 2.0
    news_run_subdir: str = ""
    news_failures_dir: str = "data/news_failures"
    upsert_batch: int = 128
    embed_batch: int = 32

    holdings_csv: str = "data/fund_holdings_aggregate/aggregated_holdings.csv"
    sectors_csv: str = "data/fund_holdings_aggregate/aggregated_sectors.csv"
    # When empty (default), load_universe loads top holdings (holdings_limit) and top sectors (sectors_limit).
    # To load a specific investor portfolio universe instead, set PORTFOLIO_JSON in .env (e.g. investor_data/mohit/portfolio.json).
    portfolio_json: str = ""
    allisin_sectors_holdings_json: str = "data/fund_holdings_aggregate/allisin_sectors_with_holdings.json"
    portfolio_allisin_holdings_json: str = "data/fund_holdings_aggregate/portfolio_allisin_holdings.json"
    portfolio_manifest_path: str = "data/fund_holdings_aggregate/portfolio_news_scope.json"
    aggregated_holdings_map: str = "data/fund_holdings_aggregate/aggregated_holdings_map.json"
    aggregated_holdings_csv: str = "data/fund_holdings_aggregate/aggregated_holdings.csv"

    portfolio_holding_min_pct: float = 2.0
    portfolio_sector_min_pct: float = 3.0
    run_summary_dir: str = "data/news_runs"
    qdrant_inspect_dir: str = "data/qdrant_inspect"
    scrape_workspace_dir: str = "data/news_scrape_cache"
    jev_input_cost_per_million_usd: float = 0.042
    fresh_start_each_run: bool = False
    fresh_start_clear_qdrant: bool = False
    # Fresh start never deletes .log files when true (default). Env: PRESERVE_RUN_LOGS.
    preserve_run_logs: bool = True
    # When fresh_start_each_run is true, delete old run JSON summaries only if true. Env: FRESH_START_CLEAR_RUN_JSON.
    fresh_start_clear_run_json: bool = False

    def path(self, relative: str) -> Path:
        return repo_root() / relative
