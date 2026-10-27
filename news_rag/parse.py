"""Rule-based time and hint parsing from user questions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

TIME_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    (re.compile(r"\blast\s+(\d+)\s+days?\b", re.I), 0),
    (re.compile(r"\bpast\s+(\d+)\s+days?\b", re.I), 0),
    (re.compile(r"\blast\s+one\s+week\b|\blast\s+1\s+week\b|\bpast\s+week\b|\blast\s+week\b", re.I), 7),
    (re.compile(r"\blast\s+(\d+)\s+weeks?\b", re.I), 0),
    (re.compile(r"\blast\s+month\b|\bpast\s+month\b|\blast\s+one\s+month\b", re.I), 30),
    (re.compile(r"\blast\s+(\d+)\s+months?\b", re.I), 0),
    (re.compile(r"\byesterday\b", re.I), 1),
    (re.compile(r"\btoday\b", re.I), 1),
]

STOPWORDS = {
    "why",
    "what",
    "how",
    "when",
    "where",
    "who",
    "which",
    "the",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "for",
    "in",
    "on",
    "at",
    "to",
    "a",
    "an",
    "and",
    "or",
    "of",
    "last",
    "past",
    "one",
    "week",
    "weeks",
    "day",
    "days",
    "month",
    "months",
    "year",
    "years",
    "news",
    "about",
    "stock",
    "stocks",
    "shares",
    "share",
    "price",
    "prices",
    "underperforming",
    "performing",
    "performance",
    "market",
    "markets",
    "india",
    "indian",
    "whats",
    "what's",
    "happening",
    "happened",
    "sector",
    "industry",
    "going",
    "with",
    "tell",
    "me",
    "give",
    "update",
    "updates",
    "latest",
    "did",
    "do",
    "does",
    "will",
    "can",
    "could",
    "should",
    "would",
    "drop",
    "dropping",
    "fell",
    "falling",
    "rise",
    "rising",
    "gain",
    "gaining",
    "jump",
    "jumping",
    "surge",
    "surging",
    "affect",
    "affects",
    "affecting",
    "impact",
    "impacts",
    "impacting",
    "mean",
    "means",
    "meaning",
    "overall",
    "mood",
    "view",
    "outlook",
    "today",
    "yesterday",
    "tomorrow",
    "this",
    "that",
    "these",
    "those",
    "define",
    "definition",
    "explain",
    "explanation",
    "concept",
    "describe",
    "description",
}

CONCEPT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*what\s+is\s+(a|an|the)?\s*[\w\s&'-]+(\?|$)", re.I),
    re.compile(r"^\s*what\s+are\s+(a|an|the)?\s*[\w\s&'-]+(\?|$)", re.I),
    re.compile(r"^\s*define\s+[\w\s&'-]+(\?|$)", re.I),
    re.compile(r"^\s*explain\s+(what\s+is\s+|what\s+are\s+|the\s+concept\s+of\s+)?[\w\s&'-]+(\?|$)", re.I),
    re.compile(r"\bmeaning\s+of\s+[\w\s&'-]+(\?|$)", re.I),
    re.compile(r"\bwhat\s+does\s+[\w\s&'-]+\s+mean\b", re.I),
    re.compile(r"^\s*how\s+does\s+(a|an|the)?\s*[\w\s&'-]+\s+work(\?|$)", re.I),
)


def is_concept_query(question: str) -> bool:
    q = question.strip().lower()
    if any(p in q for p in [
        "what is happening", "what's happening", "what happened", "what is going on",
        "price", "trend", "moving", "falling", "rising", "drop", "surge", "gain",
        "today", "yesterday", "last week", "last month", "30 day", "rate", "target", "outlook"
    ]):
        return False
    return any(p.search(question) for p in CONCEPT_PATTERNS)

# Map phrases in the question to corpus entity_names (exact labels matching ingest universe).
TOPIC_ENTITY_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Macro & Commodity Entities
    (re.compile(r"\bgold\b|\bbullion\b|\byellow\s+metal\b|\bsgb\b|\bsovereign\s+gold\b", re.I), "Macro - Gold"),
    (re.compile(r"\bsilver\b|\bwhite\s+metal\b", re.I), "Macro - Silver"),
    (re.compile(r"\bcrude\b|\bcrude\s+oil\b|\bbrent\b|\boil\s+prices?\b|\bpetroleum\b|\bopec\b", re.I), "Macro - Crude Oil"),
    (re.compile(r"\bnatural\s+gas\b|\bgas\s+price", re.I), "Macro - Natural Gas"),
    (re.compile(r"\brupee\b|\binr\b|\busd\b|\bdollar\b|\bforex\b|\bcurrency\b|\bexchange\s+rate\b", re.I), "Macro - Rupee / USD"),
    (re.compile(r"\brepo\s+rate\b|\brbi\s+policy\b|\bmonetary\s+policy\b|\binterest\s+rates?\b|\brate\s+cut\b|\brate\s+hike\b|\bmpc\b|\bhome\s+loans?\b", re.I), "Macro - RBI Repo Rate"),
    (re.compile(r"\bbond\s+yield|\bg-sec|\bgsec\b|\b10-year\s+yield\b", re.I), "Macro - Bond Yields"),
    (re.compile(r"\binflation\b|\bcpi\b|\bwpi\b|\bcost\s+of\s+living\b|\bprice\s+rise\b", re.I), "Macro - Inflation (CPI)"),
    (re.compile(r"\bgdp\b|\beconomic\s+growth\b|\bindian\s+economy\b|\bgrowth\s+rate\b", re.I), "Macro - GDP & Economy"),
    (re.compile(r"\btariffs?\b|\btrade\s+war\b|\bglobal\s+trade\b|\bsanctions?\b|\bexport\s+duty\b", re.I), "Macro - Tariffs & Trade"),
    (re.compile(r"\bfii\b|\bfiis\b|\bdii\b|\bdiis\b|\bfpi\b|\bfpis\b|\bforeign\s+investors?\b|\binstitutional\s+flows?\b", re.I), "Macro"),

    # Industry / Sector Entities
    (re.compile(r"\bbanking\b|\bbank\s+sector\b|\bbanks\b|\bpsu\s+banks?\b|\bprivate\s+banks?\b", re.I), "Banks"),
    (re.compile(r"\bit\s+sector\b|\bsoftware\b|\bit\s+services\b|\btech\s+sector\b", re.I), "IT - Software"),
    (re.compile(r"\bhospital\b|\bhospitals\b|\bhealthcare\b|\bhealth\s+care\b|\bmedical\b", re.I), "Healthcare Services"),
    (re.compile(r"\bpharma\b|\bbiotech\b|\bpharmaceuticals?\b|\bdrugmakers?\b", re.I), "Pharmaceuticals & Biotechnology"),
    (re.compile(r"\bretail\b|\bretailing\b|\be-commerce\b", re.I), "Retailing"),
    (re.compile(r"\bauto\b|\bautomobile\b|\bcarmaker\b|\bevs?\b|\belectric\s+vehicles?\b", re.I), "Automobiles"),
    (re.compile(r"\bfinance\s+sector\b|\bfinancial\s+services\b|\bnbfc\b", re.I), "Finance"),
    (re.compile(r"\bpower\b|\belectricity\b|\benergy\s+sector\b|\brenewable\b", re.I), "Power"),
    (re.compile(r"\bfmcg\b|\bconsumer\s+goods\b", re.I), "Diversified FMCG"),
    (re.compile(r"\bmetals?\b|\bsteel\s+sector\b|\bmining\b", re.I), "Ferrous Metals"),
    (re.compile(r"\btelecom\b|\b5g\b|\btelecommunication\b", re.I), "Telecom - Services"),
    (re.compile(r"\btransport\b|\baviation\b|\bairline\b|\bairlines\b|\bair\s+travel\b", re.I), "Transport Services"),
    (re.compile(r"\binsurance\b|\blife\s+insurance\b", re.I), "Insurance"),
    (re.compile(r"\bfintech\b|\bdigital\s+payments?\b", re.I), "Financial Technology (Fintech)"),
    (re.compile(r"\bconstruction\b|\binfrastructure\b|\brealty\b|\breal\s+estate\b|\bcement\b", re.I), "Construction"),
)

SECTOR_EXPANSIONS: dict[str, list[str]] = {
    "Healthcare Services": [
        "Healthcare Services",
        "Pharmaceuticals & Biotechnology",
        "Max Healthcare Institute Limited",
        "Fortis Healthcare Limited",
        "Apollo Hospitals Enterprise Limited",
        "Dr. Lal PathLabs Ltd.",
        "Sun Pharmaceutical Industries Limited",
        "Torrent Pharmaceuticals Limited",
    ],
    "Pharmaceuticals & Biotechnology": [
        "Pharmaceuticals & Biotechnology",
        "Healthcare Services",
        "Sun Pharmaceutical Industries Limited",
        "Torrent Pharmaceuticals Limited",
        "Aurobindo Pharma Limited",
        "Sai Life Sciences Limited",
        "Max Healthcare Institute Limited",
    ],
    "IT - Software": [
        "IT - Software",
        "Infosys Limited",
        "Tata Consultancy Services Limited",
        "HCL Technologies Ltd.",
        "Coforge Limited",
        "Wipro Limited",
        "Tech Mahindra Limited",
    ],
    "Banks": [
        "Banks",
        "Finance",
        "ICICI Bank Limited",
        "HDFC Bank Limited",
        "State Bank of India",
        "Kotak Mahindra Bank Limited",
        "Axis Bank Limited",
        "The Federal Bank Limited",
        "AU Small Finance Bank Limited",
        "Indian Bank",
    ],
    "Finance": [
        "Finance",
        "Banks",
        "Bajaj Finance Limited",
        "Financial Technology (Fintech)",
        "One 97 Communications Limited",
    ],
    "Automobiles": [
        "Automobiles",
        "Mahindra & Mahindra Limited",
        "Maruti Suzuki India Limited",
        "Bajaj Auto Limited",
        "Tata Motors Limited",
        "Eicher Motors Ltd.",
        "Hero MotoCorp Limited",
    ],
    "Retailing": [
        "Retailing",
        "Diversified FMCG",
        "Trent Limited",
        "Eternal Limited",
        "FSN E-Commerce Ventures Ltd.",
        "Titan Company Limited",
    ],
    "Diversified FMCG": [
        "Diversified FMCG",
        "ITC Limited",
        "Hindustan Unilever Ltd.",
        "Tata Consumer Products Limited",
    ],
    "Transport Services": [
        "Transport Services",
        "InterGlobe Aviation Limited",
        "Container Corporation of India Limited",
    ],
    "Telecom - Services": [
        "Telecom - Services",
        "Bharti Airtel Limited",
        "Vodafone Idea Limited",
    ],
    "Power": [
        "Power",
        "NTPC Limited",
        "Tata Power Company Limited",
        "Power Grid Corporation of India Limited",
        "Adani Power Limited",
    ],
    "Construction": [
        "Construction",
        "Construction Materials",
        "Larsen & Toubro Limited",
        "Prestige Estates Projects Limited",
        "ABB India Limited",
        "Siemens Limited",
        "Ultratech Cement Ltd.",
    ],
    "Ferrous Metals": [
        "Ferrous Metals",
        "Tata Steel Ltd.",
        "JSW Steel Limited",
        "Hindalco Industries Limited",
    ],
}

COMPANY_ALIAS_MAP: dict[str, str] = {
    "tcs": "Tata Consultancy Services Limited",
    "infy": "Infosys Limited",
    "infosys": "Infosys Limited",
    "reliance": "Reliance Industries Limited",
    "ril": "Reliance Industries Limited",
    "hdfc": "HDFC Bank Limited",
    "hdfc bank": "HDFC Bank Limited",
    "icici": "ICICI Bank Limited",
    "icici bank": "ICICI Bank Limited",
    "sbi": "State Bank of India",
    "state bank": "State Bank of India",
    "kotak": "Kotak Mahindra Bank Limited",
    "axis bank": "Axis Bank Limited",
    "axis": "Axis Bank Limited",
    "lt": "Larsen & Toubro Limited",
    "l&t": "Larsen & Toubro Limited",
    "larsen": "Larsen & Toubro Limited",
    "tata steel": "Tata Steel Ltd.",
    "maruti": "Maruti Suzuki India Limited",
    "asian paints": "Asian Paints Limited",
    "itc": "ITC Limited",
    "airtel": "Bharti Airtel Limited",
    "bharti airtel": "Bharti Airtel Limited",
    "hcl": "HCL Technologies Ltd.",
    "hcl tech": "HCL Technologies Ltd.",
    "bajaj finance": "Bajaj Finance Limited",
    "bajaj auto": "Bajaj Auto Limited",
    "sun pharma": "Sun Pharmaceutical Industries Limited",
    "titan": "Titan Company Limited",
    "hul": "Hindustan Unilever Ltd.",
    "hindustan unilever": "Hindustan Unilever Ltd.",
    "ultratech": "Ultratech Cement Ltd.",
    "m&m": "Mahindra & Mahindra Limited",
    "mahindra": "Mahindra & Mahindra Limited",
    "eicher": "Eicher Motors Ltd.",
    "hero": "Hero MotoCorp Limited",
    "ntpc": "NTPC Limited",
    "ongc": "Oil & Natural Gas Corporation Limited",
    "paytm": "One 97 Communications Limited",
    "zomato": "Eternal Limited",
    "nykaa": "FSN E-Commerce Ventures Ltd.",
    "indiago": "InterGlobe Aviation Limited",
    "indigo": "InterGlobe Aviation Limited",
}


@dataclass
class ParsedQuery:
    question: str
    published_from: str
    published_to: str
    window_label: str
    stock_hint: str
    entity_resolved: list[str]
    entity_match_note: str
    intent: str = "general"
    fund_resolved: dict | None = None
    sub_questions: list[str] = field(default_factory=list)
    router_result: Any | None = None
    fund_ambiguous: bool = False
    close_funds: list[str] = field(default_factory=list)
    contract: Any | None = None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_date_field(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    text = str(value).strip()
    if len(text) == 10:
        text = text + "T00:00:00Z"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def infer_window_days_from_question(question: str, *, default_days: int) -> int:
    """Days to look back from question phrasing; falls back to default_days."""
    for pattern, fixed_days in TIME_PATTERNS:
        match = pattern.search(question or "")
        if not match:
            continue
        if fixed_days > 0:
            return fixed_days
        groups = match.groups()
        if groups and groups[0].isdigit():
            n = int(groups[0])
            if "week" in match.group(0).lower():
                return n * 7
            if "month" in match.group(0).lower():
                return n * 30
            return n
    lower = (question or "").lower()
    if any(p in lower for p in ("right now", "currently", "at the moment", "market now")):
        return 7
    return default_days


def parse_time_window(
    question: str,
    *,
    date_from: str | None,
    date_to: str | None,
    default_days: int,
) -> tuple[str, str, str]:
    now = utc_now()
    start = parse_date_field(date_from)
    end = parse_date_field(date_to)
    if start or end:
        if not start:
            start = now - timedelta(days=default_days)
        if not end:
            end = now
        label = f"{start.date().isoformat()} to {end.date().isoformat()}"
        return to_iso(start), to_iso(end), label

    days = infer_window_days_from_question(question, default_days=default_days)

    start = now - timedelta(days=days)
    label = f"last {days} days"
    return to_iso(start), to_iso(now), label


SECTOR_CORPUS_NAMES = {
    "Banks",
    "IT - Software",
    "It - Software",
    "Pharmaceuticals & Biotechnology",
    "Retailing",
    "Automobiles",
    "Auto Components",
    "Capital Markets",
    "Finance",
    "Power",
    "Realty",
    "Diversified FMCG",
    "Fast Moving Consumer Goods",
    "Ferrous Metals",
    "Metals & Mining",
    "Oil, Gas & Consumable Fuels",
    "Petroleum Products",
    "Telecom - Services",
    "Telecom",
    "Chemicals & Petrochemicals",
    "Chemicals",
    "Construction Materials",
    "Construction",
    "Consumer Durables",
    "Healthcare Services",
    "Insurance",
    "Financial Technology (Fintech)",
}


def split_multi_questions(question: str) -> list[str]:
    """Splits compound questions into individual sub-questions if multiple questions are detected."""
    # Split on question marks first
    parts = [p.strip() for p in re.split(r"\?+", question) if p.strip()]
    if len(parts) > 1:
        return [p + ("?" if not p.endswith("?") else "") for p in parts if len(p) > 5]
    
    # Split on explicit connectors like "and what", "also how", "and how"
    sub_parts = re.split(r",?\s+(?:and|also)\s+(?:what|how|why|which|is|does|will|tell me)\s+", question, flags=re.I)
    if len(sub_parts) > 1 and all(len(p.strip()) > 10 for p in sub_parts):
        return [p.strip() for p in sub_parts]
        
    return [question.strip()]


