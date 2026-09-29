"""Rule-based time and hint parsing from user questions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

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
    "the",
    "is",
    "are",
    "was",
    "were",
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
    "news",
    "about",
    "stock",
    "shares",
    "share",
    "price",
    "underperforming",
    "performing",
    "performance",
    "market",
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
}

# Map phrases in the question to corpus entity_names (same labels as the ingest universe).
TOPIC_ENTITY_HINTS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Macro & Commodity Entities
    (re.compile(r"\bgold\b|\bbullion\b|\byellow\s+metal\b|\bsgb\b|\bsovereign\s+gold\b", re.I), "Macro - Gold"),
    (re.compile(r"\bsilver\b|\bwhite\s+metal\b", re.I), "Macro - Silver"),
    (re.compile(r"\bcrude\b|\bcrude\s+oil\b|\bbrent\b|\boil\s+prices?\b|\bpetroleum\b|\bopec\b", re.I), "Macro - Crude Oil"),
    (re.compile(r"\brupee\b|\binr\b|\busd\b|\bdollar\b|\bforex\b|\bcurrency\b|\bexchange\s+rate\b", re.I), "Macro - US Dollar & Rupee Forex"),
    (re.compile(r"\brepo\s+rate\b|\brbi\s+policy\b|\bmonetary\s+policy\b|\binterest\s+rates?\b|\brate\s+cut\b|\brate\s+hike\b|\bmpc\b", re.I), "Macro - Interest Rates & RBI Monetary Policy"),
    (re.compile(r"\binflation\b|\bcpi\b|\bwpi\b|\bcost\s+of\s+living\b|\bprice\s+rise\b", re.I), "Macro - Inflation (CPI & WPI)"),
    (re.compile(r"\bfii\b|\bfiis\b|\bdii\b|\bdiis\b|\bfpi\b|\bfpis\b|\bforeign\s+investors?\b|\binstitutional\s+flows?\b", re.I), "Macro - FII & DII Market Flows"),
    (re.compile(r"\bgdp\b|\beconomic\s+growth\b|\bindian\s+economy\b|\bgrowth\s+rate\b", re.I), "Macro - India GDP & Economic Growth"),
    (re.compile(r"\bbudget\b|\bunion\s+budget\b|\bfiscal\s+deficit\b|\bgovernment\s+policy\b|\bgst\s+council\b", re.I), "Macro - Government Policy & Union Budget"),
    (re.compile(r"\bgeopolitic|\btrade\s+war\b|\btariffs?\b|\bglobal\s+trade\b|\bsanctions?\b|\bmiddle\s+east\b|\bwar\b|\bconflict\b", re.I), "Macro - Global Trade & Geopolitics"),

    # Industry / Sector Entities
    (re.compile(r"\bbanking\b|\bbank\s+sector\b|\bbanks\b|\bpsu\s+banks?\b|\bprivate\s+banks?\b", re.I), "Banks"),
    (re.compile(r"\bit\s+sector\b|\bsoftware\b|\bit\s+services\b|\btech\s+sector\b", re.I), "It - Software"),
    (re.compile(r"\bpharma\b|\bbiotech\b|\bpharmaceuticals?\b|\bhealthcare\b|\bdrugmakers?\b", re.I), "Pharmaceuticals & Biotechnology"),
    (re.compile(r"\bretail\b|\bretailing\b", re.I), "Retailing"),
    (re.compile(r"\bauto\b|\bautomobile\b|\bcarmaker\b|\bevs?\b|\belectric\s+vehicles?\b", re.I), "Automobiles"),
    (re.compile(r"\bcapital\s+market\b|\bstock\s+market\b|\bsebi\b", re.I), "Capital Markets"),
    (re.compile(r"\bnbfc\b|\bfinance\s+sector\b|\bfinancial\s+services\b", re.I), "Finance"),
    (re.compile(r"\bpower\b|\belectricity\b|\benergy\s+sector\b|\brenewable\b", re.I), "Power"),
    (re.compile(r"\breal\s+estate\b|\brealty\b|\bhousing\s+market\b", re.I), "Realty"),
    (re.compile(r"\bfmcg\b|\bconsumer\s+goods\b", re.I), "Fast Moving Consumer Goods"),
    (re.compile(r"\bmetals?\b|\bsteel\s+sector\b|\bmining\b", re.I), "Metals & Mining"),
)


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

    days = default_days
    for pattern, fixed_days in TIME_PATTERNS:
        match = pattern.search(question)
        if not match:
            continue
        if fixed_days > 0:
            days = fixed_days
            break
        groups = match.groups()
        if groups and groups[0].isdigit():
            n = int(groups[0])
            if "week" in match.group(0).lower():
                days = n * 7
            elif "month" in match.group(0).lower():
                days = n * 30
            else:
                days = n
            break

    start = now - timedelta(days=days)
    label = f"last {days} days"
    return to_iso(start), to_iso(now), label


def extract_stock_hint(question: str, explicit: str | None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    for pattern, entity_label in TOPIC_ENTITY_HINTS:
        if pattern.search(question):
            return entity_label
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9&.\-]{1,}", question)
    for token in tokens:
        lower = token.lower()
        if lower in STOPWORDS or len(lower) < 2:
            continue
        return token
    return ""


def resolve_entities(hint: str, corpus_names: set[str]) -> tuple[list[str], str]:
    if not hint:
        return [], "no_stock_hint"
    hint_lower = hint.lower()
    matches = []
    for name in sorted(corpus_names):
        if hint_lower in name.lower() or name.lower() in hint_lower:
            matches.append(name)
    if matches:
        return matches, "matched"
    token = hint_lower
    for name in sorted(corpus_names):
        parts = name.lower().split()
        if any(token in part or part.startswith(token) for part in parts if len(part) >= 3):
            matches.append(name)
    if matches:
        return matches[:5], "fuzzy_matched"
    return [], "not_in_corpus"


SECTOR_CORPUS_NAMES = {
    "Banks",
    "It - Software",
    "Pharmaceuticals & Biotechnology",
    "Retailing",
    "Automobiles",
    "Capital Markets",
    "Finance",
    "Power",
    "Realty",
    "Fast Moving Consumer Goods",
    "Metals & Mining",
    "Oil, Gas & Consumable Fuels",
    "Telecom",
    "Chemicals",
    "Construction Materials",
}


def classify_query_intent(
    question: str,
    stock_hint: str,
    resolved_entities: list[str],
) -> str:
    """Classifies user query intent into single_stock, macro_commodity, sector, or general."""
    lower_q = question.lower()
    
    # 1. Check Macro / Commodity
    if any(entity.startswith("Macro -") for entity in resolved_entities):
        return "macro_commodity"
    macro_terms = [
        "gold", "silver", "crude", "oil", "brent", "petroleum", "rupee", "dollar", "forex",
        "inflation", "cpi", "wpi", "interest rate", "repo rate", "rbi policy", "mpc",
        "fii", "dii", "fpi", "gdp", "economic growth", "union budget", "geopolitic"
    ]
    if any(re.search(rf"\b{re.escape(term)}\b", lower_q) for term in macro_terms):
        return "macro_commodity"

    # 2. Check Sector / Industry
    if any(entity in SECTOR_CORPUS_NAMES for entity in resolved_entities):
        return "sector"
    sector_terms = ["sector", "industry", "banking industry", "it sector", "auto sector", "pharma sector"]
    if any(term in lower_q for term in sector_terms):
        return "sector"

    # 3. Check Single Stock
    if resolved_entities and not any(e.startswith("Macro -") for e in resolved_entities):
        # Specific company match in corpus
        return "single_stock"
    if stock_hint and stock_hint.lower() not in STOPWORDS:
        return "single_stock"

    return "general"

