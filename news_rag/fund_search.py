"""Fast search and autocomplete recommendations across mutual funds using regular-growth-by-amc universe and live RupeeStop API."""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Any

import httpx

from news_rag.config import get_settings
from news_rag.fund_catalog import get_amc_catalog, install_amc_catalog

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_API_BASE_URL = "https://backend.rupeestop.com/api/v1/app/fund"

# Pre-merger HDFC MF ISINs (INF063A*) → current HDFC AMC codes served by the API.
_ISIN_ALIASES: dict[str, str] = {
    "INF063A01027": "INF179KA1RT1",  # HDFC Large & Mid Cap Regular Growth
    "INF063A01050": "INF179KA1RZ8",  # HDFC Small Cap Regular Growth
}

# Rare legacy nicknames only — routine resolution uses catalog fuzzy match, not this map.
_SCHEME_NAME_TO_ISIN: dict[str, str] = {
    "sbi bluechip": "INF200K01180",
    "sbi blue chip": "INF200K01180",
    "axis bluechip": "INF846K01164",
    "axis blue chip": "INF846K01164",
    "icici pru bluechip": "INF109K01BL4",
    "icici prudential bluechip": "INF109K01BL4",
    "hdfc top 100": "INF179K01BE2",
    "hdfc mid cap opportunities": "INF179K01CR2",
}

_ISIN_IN_TEXT = re.compile(r"\b(INF[A-Z0-9]{9})\b", re.I)

_TOKEN_ALIASES: dict[str, str] = {
    "pru": "prudential",
    "ppfas": "parag",
    "absl": "aditya",
    "parag": "parag",
    "parikh": "parikh",
    "whiteoak": "whiteoak",
    "white": "whiteoak",
    "oak": "whiteoak",
    "lm": "large",
    "l": "large",
    "m": "mid",
}


def resolve_canonical_isin(isin: str) -> str:
    clean = (isin or "").strip().upper()
    return _ISIN_ALIASES.get(clean, clean)


def _clean_company_name(n: Any) -> str:
    s = str(n or "").strip()
    # Remove footnote annotations like £, *, #, @, etc.
    s = re.sub(r"[\*£@#$~\^]+$", "", s).strip()
    return s


# Tokens in the user phrase that imply a specific AMC (must match fund name or ## AMC header).
_AMC_HINT_TOKENS: dict[str, tuple[str, ...]] = {
    "hdfc": ("hdfc",),
    "icici": ("icici",),
    "sbi": ("sbi", "state bank"),
    "axis": ("axis",),
    "kotak": ("kotak",),
    "nippon": ("nippon",),
    "mirae": ("mirae",),
    "absl": ("absl", "aditya birla sun life", "aditya birla"),
    "aditya": ("aditya birla", "aditya birla sun life"),
    "birla": ("aditya birla", "birla sun life"),
    "ppfas": ("ppfas", "parag parikh", "parag"),
    "uti": ("uti",),
    "tata": ("tata",),
    "dsp": ("dsp",),
    "franklin": ("franklin",),
    "invesco": ("invesco",),
    "motilal": ("motilal", "oswal"),
    "bajaj": ("bajaj",),
    "bandhan": ("bandhan",),
    "baroda": ("baroda", "bnp"),
    "canara": ("canara",),
    "edelweiss": ("edelweiss",),
    "quant": ("quant",),
    "hsbc": ("hsbc",),
    "jm": ("jm financial", "jm "),
    "pgim": ("pgim",),
    "samco": ("samco",),
    "groww": ("groww",),
    "angel": ("angel one",),
    "zerodha": ("zerodha", "smallcase"),
    "whiteoak": ("whiteoak", "white oak"),
    "lic": ("lic", "life insurance"),
    "mahindra": ("mahindra",),
    "sundaram": ("sundaram",),
    "union": ("union",),
    "nj": ("nj",),
    "trust": ("trust",),
}


def _needles_for_amc_hint(hint: str) -> tuple[str, ...]:
    cat = get_amc_catalog()
    if cat and cat.hint_tokens:
        needles = cat.needles_for_hint(hint)
        if needles != (hint,):
            return needles
        if hint in cat.hint_tokens:
            return cat.hint_tokens[hint]
    return _AMC_HINT_TOKENS.get(hint, (hint,))


def _amc_hints_from_tokens(tokens: list[str]) -> list[str]:
    hints: list[str] = []
    joined = " ".join(tokens)
    if "angel one" in joined or ("angel" in tokens and "one" in tokens):
        hints.append("angel")
    cat = get_amc_catalog()
    if cat and cat.hint_tokens:
        for tok in tokens:
            if tok in cat.hint_tokens:
                hints.append(tok)
        for i in range(len(tokens) - 1):
            pair = f"{tokens[i]} {tokens[i+1]}"
            if pair in cat.hint_tokens:
                hints.append(pair)
    for key, needles in _AMC_HINT_TOKENS.items():
        if key in hints:
            continue
        if key in tokens or any(n in joined for n in needles):
            hints.append(key)
    return list(dict.fromkeys(hints))


def _entry_matches_amc(entry: dict[str, Any], hints: list[str]) -> bool:
    if not hints:
        return True
    amc = _normalize_fund_text(str(entry.get("amc") or ""))
    name = _normalize_fund_text(str(entry.get("fund_short_name") or entry.get("fund_name") or ""))
    blob = f"{amc} {name}"
    for hint in hints:
        needles = _needles_for_amc_hint(hint)
        if any(n in blob for n in needles):
            return True
    return False


def _normalize_fund_text(text: str) -> str:
    """Normalizes compound market and fund terms into standard separated tokens."""
    t = (text or "").lower()
    t = re.sub(r"\blargecap\b", "large cap", t)
    t = re.sub(r"\bmidcap\b", "mid cap", t)
    t = re.sub(r"\bsmallcap\b", "small cap", t)
    t = re.sub(r"\bflexicap\b", "flexi cap", t)
    t = re.sub(r"\bmulticap\b", "multi cap", t)
    t = re.sub(r"\bmicrocap\b", "micro cap", t)
    if not re.search(r"\bus\s+blue", t):
        t = re.sub(r"\bblue\s*chip\b|\bbluechip\b", "large cap", t)
    t = re.sub(r"\btop\s*100\b", "large cap", t)
    t = re.sub(r"\btop\s*200\b", "large mid cap", t)
    t = re.sub(r"\bopportunities\b", "", t)
    t = re.sub(r"\b&\b", " and ", t)
    t = re.sub(r"\babsl\b", "aditya birla sun life", t)
    t = re.sub(r"\bppfas\b", "parag parikh ppfas", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _expand_query_token(token: str) -> set[str]:
    out = {token}
    alias = _TOKEN_ALIASES.get(token)
    if alias:
        out.add(alias)
    if len(token) >= 4:
        out.add(token[:4])
    return out


def _clean_fund_phrase(phrase: str) -> str:
    p = (phrase or "").strip().rstrip("?").strip()
    p = re.sub(
        r"\b(-\s*)?(regular|direct)\s+plan\b.*$",
        "",
        p,
        flags=re.I,
    ).strip()
    p = re.sub(r"\b(growth|idcw|dividend)\s*(?:option|plan)?\s*$", "", p, flags=re.I).strip()
    p = re.sub(r"^(?:the|a|an)\s+", "", p, flags=re.I)
    return p


_GARBAGE_SCHEME_PHRASE = re.compile(
    r"^(?:me|my|this|that|it|any)(?:\s+(?:for\s+)?(?:me\s+)?(?:for\s+)?(?:this|that|the)\s+fund)?$",
    re.I,
)


def _is_plausible_scheme_phrase(phrase: str) -> bool:
    """Reject pronoun tails like 'me for this fund' that fuzzy-match unrelated schemes."""
    cleaned = _clean_fund_phrase(phrase)
    if len(cleaned) < 3:
        return False
    if cleaned.upper().startswith("INF"):
        return True
    norm = _normalize_fund_text(cleaned)
    if not norm:
        return False
    if _GARBAGE_SCHEME_PHRASE.fullmatch(norm):
        return False
    tokens = [w for w in re.findall(r"\b[a-z0-9]+\b", norm) if len(w) >= 2]
    if not tokens:
        return False
    if _amc_hints_from_tokens(tokens):
        return True
    scheme_markers = (
        "cap",
        "flexi",
        "large",
        "mid",
        "small",
        "elss",
        "index",
        "etf",
        "ppfas",
        "parag",
        "absl",
        "aditya",
        "birla",
        "defence",
        "defense",
        "banking",
        "technology",
        "pharma",
        "infra",
        "thematic",
        "equity",
        "debt",
        "hybrid",
        "bluechip",
        "focused",
        "contra",
        "value",
        "liquid",
        "gilt",
        "nifty",
        "index",
        "etf",
        "bees",
        "market",
        "total",
    )
    if any(m in norm for m in scheme_markers):
        return True
    # Bare AMC name only (e.g. "hdfc defence") is OK when at least two tokens.
    if len(tokens) >= 2 and not re.match(r"^(me|my|this|that|it)\b", norm):
        return True
    return False


def _scheme_alias_isin(norm_name: str) -> str | None:
    key = _normalize_fund_text(norm_name)
    key = re.sub(r"\s+-\s+.*$", "", key).strip()
    key = re.sub(r"\s+fund\s*$", "", key).strip()
    hit = _SCHEME_NAME_TO_ISIN.get(key)
    if hit:
        return hit
    for alias_key, isin in _SCHEME_NAME_TO_ISIN.items():
        if _normalize_fund_text(alias_key) == key:
            return isin
    return None


def is_market_fund_discovery_question(question: str) -> bool:
    """Top-N / which-funds market queries — do not bind a single scheme from question text."""
    lower = (question or "").lower()
    if is_macro_metals_question(question):
        return True
    if re.search(r"\b(barrel+s?|brent|wti|crude)\b", lower) and re.search(
        r"\b(sector|energy|funds?|affect)\b", lower
    ):
        return True
    if re.search(
        r"\b(hot in the market|how'?s the market|how is the market|what to focus on|market doing)\b",
        lower,
    ):
        return True
    if re.search(r"\bsectors?\b", lower) and re.search(
        r"\b(positive|postive|negative|last month|past month)\b", lower
    ):
        return True
    if re.search(r"\b(most\s+affected|highest\s+exposure|worst\s+hit|most\s+impacted)\b", lower):
        return True
    if re.search(r"\b(?:which|what)\s+funds?\b", lower) and re.search(r"\btop\s*\d+", lower):
        return True
    if re.search(r"\btop\s*\d+\s+funds\b", lower):
        return True
    return False


def is_macro_metals_question(question: str) -> bool:
    """Gold/silver macro or market-wide — 'my portfolio' is rhetorical, not investor book lookup."""
    lower = (question or "").lower()
    if not re.search(r"\b(gold|silver|bullion)\b", lower):
        return False
    # Explicit single-scheme facts
    if re.search(r"\b(isin|inf[a-z0-9]{9})\b", lower, re.I):
        return False
    if re.search(r"\b(nav|holdings?|sectors?)\s+(?:of|for)\s+", lower):
        if re.search(
            r"\b(hdfc|icici|axis|kotak|mirae|sbi|nippon|edelweiss|motilal|bandhan)\b",
            lower,
        ):
            return False
    macro = (
        r"\bportfolio\b",
        r"\bdownfall\b",
        r"\bdeclin(e|ing)\b",
        r"\b(sudden\s+)?fall(?:ing|en)?\b",
        r"\bdrop(?:ped|ping)?\b",
        r"\breason\b",
        r"\bwhat could\b",
        r"\bwhy\b",
        r"\bwhich\s+stocks?\b",
        r"\bstocks?\b.*\baffect",
        r"\baffect.*\b(mutual\s+)?funds?\b",
        r"\b(mutual\s+)?funds?\b.*\baffect",
        r"\bgold\s+and\s+silver\b",
        r"\bsilver\s+and\s+gold\b",
        r"\bmcx\b",
        r"\bspot\s+price",
        r"\bprecious\s+metal",
    )
    if any(re.search(p, lower) for p in macro):
        return True
    if re.search(r"\bany\s+mutual\s+funds?\b", lower):
        return True
    return False


def _is_bullion_phrase_not_scheme(phrase: str) -> bool:
    norm = _normalize_fund_text(phrase)
    if not norm:
        return False
    if re.fullmatch(
        r"(gold and silver|silver and gold|gold silver|gold|silver|my portfolio|it|any mutual funds?|barrell? prices?)",
        norm,
    ):
        return True
    if "gold" in norm and "silver" in norm and "fof" not in norm and "fund" not in norm:
        return True
    return False


def extract_fund_phrase_from_question(question: str) -> tuple[str, str]:
    """Best-effort scheme name / ISIN from natural-language question (no LLM)."""
    q = (question or "").strip()
    if not q:
        return "", ""
    isin_m = _ISIN_IN_TEXT.search(q)
    isin = isin_m.group(1).upper() if isin_m else ""

    amc_phrase = _extract_amc_scheme_phrase(q)
    topic_tail = ""
    topic_m = re.search(
        r"(?:top\s+\d+\s+)?(?:sectors?|holdings?|stocks?|shares?)\s+(?:in|of|for)\s+(.+?)(?:\?|$)",
        q,
        re.I,
    )
    if topic_m:
        topic_tail = _clean_fund_phrase(topic_m.group(1))
    if topic_tail and _is_plausible_scheme_phrase(topic_tail):
        if not amc_phrase or _phrase_specificity_score(topic_tail) >= _phrase_specificity_score(amc_phrase):
            return isin, topic_tail
    if amc_phrase:
        return isin, amc_phrase

    patterns = [
        r"\binvested\s+in\s+(?:the\s+)?(.+?)(?:\s+fund)?(?:\s*,|\?|$)",
        r"(?:latest|current)\s+(?:nav|net asset value)\s+(?:of|for)\s+(.+?)(?:\?|$)",
        r"(?:nav|net asset value)\s+(?:of|for)\s+(.+?)(?:\?|$)",
        r"(?:show|get|tell me|what is|what's)\s+(?:the\s+)?(?:latest|current)?\s*nav\s+(?:of|for)\s+(.+?)(?:\?|$)",
        r"(?:how\s+(?:is|has|was))\s+(.+?)\s+(?:fund\s+)?(?:working|performing|done)\b",
        r"(?:tell me|explain)\s+(?:how\s+)?(.+?)\s+(?:fund\s+)?(?:is\s+)?(?:working|performing)\b",
        r"(?:top\s+\d+\s+)?holdings?\s+(?:in|of|for)\s+(.+?)(?:\?|$)",
        r"(?:top\s+\d+\s+)?sectors?\s+(?:in|of|for)\s+(.+?)(?:\?|$)",
        r"sector\s+(?:allocation|breakdown|exposure)\s+(?:of|for|in)\s+(.+?)(?:\?|$)",
        r"\bimpact\s+of\s+.+?\s+on\s+(.+?)(?:\?|$)",
        r"\baffect(?:ing)?\s+(?:the\s+)?(.+?)(?:\?|$)",
        r"\bon\s+((?:the\s+)?(?:[a-z][\w\s&'.-]{2,40}?\s+)?fund)\b",
        r"\bfor\s+((?:the\s+)?(?:[a-z][\w\s&'.-]{2,40}?\s+)?fund)\b",
        r"\b(?:in|of)\s+(.+?fund)\b",
        r"\b((?:hdfc|icici|sbi|axis|kotak|nippon|mirae|uti|ppfas|parag|whiteoak|bandhan|quant|dsp|tata|absl)\s+[\w\s&'-]{2,40}?)(?:\s+fund)?\b",
    ]
    fund_name = ""
    for pat in patterns:
        m = re.search(pat, q, re.I)
        if m:
            fund_name = _clean_fund_phrase(m.group(1))
            if len(fund_name) >= 3 and _is_plausible_scheme_phrase(fund_name):
                break
            fund_name = ""
    if not fund_name and not isin:
        # Scheme-like tail after common lead-ins (no trailing "fund" required).
        m = re.search(
            r"(?:about|on|for|in|of)\s+([A-Za-z0-9][\w\s&'.-]{4,}?)(?:\?|$)",
            q,
            re.I,
        )
        if m:
            candidate = _clean_fund_phrase(m.group(1))
            norm = _normalize_fund_text(candidate)
            if _is_plausible_scheme_phrase(candidate):
                fund_name = candidate
    if not fund_name and not isin:
        late_amc = _extract_amc_scheme_phrase(q)
        if late_amc:
            fund_name = late_amc
    return isin, fund_name


# Rebuilt from regular-growth-by-amc.md headers on FundIndex load (see _sync_amc_prefix_from_catalog).
_AMC_PREFIX_RE = re.compile(r"(?!x)x")
_AMC_SCAN = _AMC_PREFIX_RE


def _sync_amc_prefix_from_catalog() -> None:
    global _AMC_PREFIX_RE, _AMC_SCAN
    cat = get_amc_catalog()
    if cat and cat.prefix_re is not None:
        _AMC_PREFIX_RE = cat.prefix_re
        _AMC_SCAN = _AMC_PREFIX_RE

_SCHEME_TAIL_TOPIC_RE = re.compile(
    r"\s+(?:sectors?|holdings?|stocks?|shares?)(?:\s+(?:allocation|breakdown|exposure))?\s*$",
    re.I,
)

_PHRASE_TAIL_STOP_WORDS = frozenset(
    {
        "what",
        "which",
        "how",
        "why",
        "when",
        "where",
        "who",
        "top",
        "are",
        "the",
        "of",
        "for",
        "in",
        "on",
        "at",
        "to",
        "a",
        "an",
        "is",
        "was",
        "were",
        "me",
        "my",
        "sectors",
        "sector",
        "holdings",
        "holding",
        "stocks",
        "stock",
        "shares",
        "share",
        "nav",
        "news",
        "impact",
        "affect",
        "affecting",
        "tell",
        "show",
        "give",
        "latest",
        "current",
    }
)


def _slurp_scheme_tail_from_question(question: str, start: int) -> str:
    """Read scheme words after AMC prefix (e.g. nifty 50 etf), stopping at question glue words."""
    raw = (question[start:] or "").lstrip()
    if not raw:
        return ""
    tokens: list[str] = []
    for m in re.finditer(r"[A-Za-z0-9&]+", raw):
        word = m.group(0)
        low = word.lower()
        if low in _PHRASE_TAIL_STOP_WORDS:
            break
        tokens.append(word)
        if len(tokens) >= 10:
            break
    return " ".join(tokens).strip()


def _compose_amc_scheme_phrase(question: str, match: re.Match[str]) -> str:
    amc = match.group(1).strip()
    tail_start = match.end()
    rest = _slurp_scheme_tail_from_question(question, tail_start)
    rest = _extend_amc_phrase_tail(question, tail_start, rest)
    rest = _SCHEME_TAIL_TOPIC_RE.sub("", rest).strip()
    rest = re.sub(
        r"\b(in|over|during|for|within)\s+(?:the\s+)?(?:last|past)\s+.+$",
        "",
        rest,
        flags=re.I,
    ).strip()
    return _clean_fund_phrase(f"{amc} {rest}".strip())


def _extract_amc_scheme_phrase(question: str) -> str:
    """AMC shorthand (ABSL, PPFAS, …) + full index/category tail (e.g. nifty 50 etf)."""
    q = question or ""
    best = ""
    best_score = 0.0
    for m in _AMC_PREFIX_RE.finditer(q):
        candidate = _compose_amc_scheme_phrase(q, m)
        if not _is_plausible_scheme_phrase(candidate):
            continue
        score = _phrase_specificity_score(candidate)
        if score > best_score:
            best_score = score
            best = candidate
    return best


def _index_benchmark_score_adjustment(norm_query: str, c_norm: str) -> float:
    """Disambiguate Nifty 50 vs Nifty 200/500 and ETF vs index fund."""
    q = (norm_query or "").lower()
    c = (c_norm or "").lower()
    adj = 0.0
    if re.search(r"nifty\s*50|nifty50", q) or re.search(r"\bnifty\b.{0,16}\b50\b", q):
        if re.search(r"nifty\s*50|nifty50", c):
            adj += 50.0
        if re.search(r"\b200\b", c) and not re.search(r"\b200\b", q):
            adj -= 60.0
        if re.search(r"\b500\b", c) and not re.search(r"\b500\b", q):
            adj -= 45.0
        if "momentum" in c and "momentum" not in q:
            adj -= 35.0
    if re.search(r"\betf\b", q):
        if "etf" in c or "exchange traded" in c:
            adj += 20.0
        elif "index fund" in c:
            adj -= 25.0
    elif re.search(r"\bfund\b", q) and "etf" not in q:
        if "index fund" in c or re.search(r"\bfund\b", c):
            adj += 12.0
        if " etf" in c or c.endswith("etf"):
            adj -= 18.0
    if ("equal weight" in c or "equal-weight" in c) and "equal" not in q:
        adj -= 45.0
    return adj

_CATEGORY_STEMS = frozenset({"large", "mid", "small", "flexi", "multi", "micro"})


def _extend_amc_phrase_tail(question: str, pos_after_match: int, rest: str) -> str:
    """AMC regex often stops at 'large' before 'cap' — read the suffix from the question."""
    r = (rest or "").strip()
    if not r:
        return r
    remainder = (question[pos_after_match:] or "").lstrip()
    if not remainder:
        return r
    parts = _normalize_fund_text(r).split()
    last = parts[-1] if parts else ""
    if last in _CATEGORY_STEMS and re.match(r"^cap\b", remainder, re.I):
        r = f"{r} cap"
        remainder = remainder[3:].lstrip()
    if re.match(r"^&\s*mid\s+cap\b", remainder, re.I):
        r = f"{r} & mid cap"
    return r.strip()


def _phrase_specificity_score(phrase: str) -> float:
    norm = _normalize_fund_text(phrase)
    tokens = [t for t in norm.split() if t]
    score = float(len(tokens) * 10 + len(norm))
    if "cap" in tokens:
        score += 15.0
    if phrase.upper().startswith("INF"):
        score += 100.0
    return score


def collect_fund_phrase_candidates(question: str) -> list[str]:
    """Ordered fund name / ISIN guesses from question text (no LLM)."""
    q = (question or "").strip()
    if not q:
        return []
    seen: set[str] = set()
    out: list[str] = []

    def add(phrase: str) -> None:
        cleaned = _clean_fund_phrase(phrase)
        if len(cleaned) < 3 or not _is_plausible_scheme_phrase(cleaned):
            return
        if _is_bullion_phrase_not_scheme(cleaned):
            return
        key = _normalize_fund_text(cleaned)
        if key in seen:
            return
        seen.add(key)
        out.append(cleaned)

    amc_phrase = _extract_amc_scheme_phrase(q)
    if amc_phrase:
        add(amc_phrase)
    for m in _AMC_PREFIX_RE.finditer(q):
        add(_compose_amc_scheme_phrase(q, m))

    isin, name = extract_fund_phrase_from_question(q)
    if isin:
        add(isin)
    if name:
        add(name)

    out.sort(key=_phrase_specificity_score, reverse=True)
    return out


def resolve_fund_from_question(
    question: str,
) -> tuple[dict[str, Any] | None, bool, list[str]]:
    """Resolve a fund from natural language, including shorthand (e.g. 'hdfc defence')."""
    if is_macro_metals_question(question):
        return None, False, []
    if is_market_fund_discovery_question(question):
        return None, False, []
    best_detail: dict[str, Any] | None = None
    best_score = -1.0
    for phrase in collect_fund_phrase_candidates(question):
        if phrase.upper().startswith("INF"):
            detail, amb, close = lookup_extracted_fund(isin=phrase.upper())
        else:
            detail, amb, close = lookup_extracted_fund(name=phrase)
        if amb:
            return None, True, close
        if detail and not amb:
            spec = _phrase_specificity_score(phrase)
            if spec > best_score:
                best_score = spec
                best_detail = detail
    if best_detail is not None:
        return best_detail, False, []
    return resolve_fund_for_query(question)


def resolve_fund_for_query(
    question: str,
    *,
    isin: str = "",
    name: str = "",
) -> tuple[dict[str, Any] | None, bool, list[str]]:
    """Resolve fund using router fields, then question text, then alias / scan."""
    discovery = is_market_fund_discovery_question(question)
    try:
        from news_rag.domain_intake import is_macro_or_commodity_focus, question_mentions_fund_scheme

        if is_macro_or_commodity_focus(question) and not question_mentions_fund_scheme(question):
            return None, False, []
    except Exception:
        pass
    attempts: list[tuple[str, str]] = []
    if (isin or "").strip() or (name or "").strip():
        attempts.append(((isin or "").strip(), (name or "").strip()))
    if not discovery:
        ext_isin, _ext_name = extract_fund_phrase_from_question(question)
        if ext_isin:
            attempts.append((ext_isin, ""))
        for phrase in collect_fund_phrase_candidates(question):
            if phrase.upper().startswith("INF"):
                attempts.append((phrase.upper(), ""))
            else:
                attempts.append(("", phrase))

    seen: set[tuple[str, str]] = set()
    last_ambiguous = False
    last_close: list[str] = []
    for i, n in attempts:
        key = (i.upper(), _normalize_fund_text(n))
        if key in seen:
            continue
        seen.add(key)
        detail, amb, close = lookup_extracted_fund(isin=i, name=n)
        if detail and not amb:
            return detail, False, []
        if amb:
            last_ambiguous = True
            last_close = close

    alias_isin = _scheme_alias_isin(name or question)
    if alias_isin and not discovery:
        detail, amb, close = lookup_extracted_fund(isin=alias_isin, name="")
        if detail and not amb:
            return detail, False, []

    if discovery:
        return None, False, []

    if last_ambiguous and last_close:
        return None, True, last_close

    scan_detail, scan_amb, scan_close = _lookup_fund_scan_question(question)
    if scan_detail and not scan_amb:
        return scan_detail, False, []
    if scan_amb:
        return None, True, scan_close
    if last_ambiguous:
        return None, True, last_close
    return None, False, []


def _lookup_fund_scan_question(question: str) -> tuple[dict[str, Any] | None, bool, list[str]]:
    """Try sliding token windows from the question against the fund index."""
    index = get_fund_index()
    index._ensure_loaded()
    norm_q = _normalize_fund_text(question)
    words = [w for w in re.findall(r"\b[a-z0-9]+\b", norm_q) if len(w) >= 2]
    stop = {
        "what", "which", "how", "show", "tell", "give", "latest", "current", "top",
        "nav", "holdings", "holding", "sectors", "sector", "allocation", "news",
        "impact", "affect", "affecting", "will", "does", "the", "and", "for", "in",
        "of", "on", "me", "is", "are", "from", "with", "recent", "positive",
        "negative", "benefit", "worst", "hit", "funds", "fund", "mutual", "scheme",
        "why", "crude", "oil", "price", "prices", "increase", "increasing", "decrease",
        "day", "daily", "every", "rising", "falling", "brent", "petrol", "commodity",
    }
    tokens = [w for w in words if w not in stop]
    if len(tokens) < 2:
        return None, False, []

    best: tuple[float, dict[str, Any]] | None = None
    for width in range(min(8, len(tokens)), 1, -1):
        for start in range(0, len(tokens) - width + 1):
            phrase = " ".join(tokens[start : start + width])
            if len(phrase) < 5:
                continue
            detail, amb, _close = lookup_extracted_fund(isin="", name=phrase)
            if detail and not amb:
                score = float(width) * 10.0 + len(phrase)
                if best is None or score > best[0]:
                    best = (score, detail)
        if best is not None:
            break
    if best:
        return best[1], False, []
    return None, False, []


def _infer_category_and_type(name: str) -> tuple[str, str]:
    """Infers scheme category and type from fund name."""
    nl = name.lower()
    scheme_type = "Equity"
    category = "Other Equity"

    if any(k in nl for k in ["liquid", "overnight", "money market", "ultra short", "low duration", "short duration", "corporate bond", "banking & psu", "gilt", "dynamic bond", "credit risk", "target maturity", "fixed horizon"]):
        scheme_type = "Debt"
        category = "Debt"
    elif any(k in nl for k in ["balanced hybrid", "aggressive hybrid", "conservative hybrid", "balanced advantage", "dynamic asset", "multi asset", "arbitrage", "equity savings"]):
        scheme_type = "Hybrid"
        category = "Hybrid"
    elif any(k in nl for k in ["gold etf", "gold fund", "silver etf", "silver fund", "commodity"]):
        scheme_type = "Commodity"
        category = "Commodities"
    elif any(k in nl for k in ["index fund", "etf", "nifty 50", "sensex", "nifty", "bse"]):
        scheme_type = "Index / Passive"
        category = "Index Funds"
    elif "flexi cap" in nl or "flexicap" in nl:
        category = "Flexi Cap"
    elif "large cap" in nl or "largecap" in nl or "bluechip" in nl:
        category = "Large Cap"
    elif "mid cap" in nl or "midcap" in nl or "emerging equity" in nl:
        category = "Mid Cap"
    elif "small cap" in nl or "smallcap" in nl:
        category = "Small Cap"
    elif "elss" in nl or "tax saver" in nl:
        category = "ELSS"
    elif "focused" in nl:
        category = "Focused"
    elif "value" in nl or "contra" in nl:
        category = "Value / Contra"

    return category, scheme_type


def _fund_text(value: Any) -> str:
    return str(value or "").strip()


def _named_weights(rows: Any) -> list[dict[str, Any]]:
    """Keep label and percentage only. Rating inputs never belong here."""
    if not isinstance(rows, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = _fund_text(row.get("label") or row.get("name") or row.get("asset"))
        try:
            percentage = round(float(row.get("percentage")), 2)
        except (TypeError, ValueError):
            continue
        if label:
            cleaned.append({"label": label, "percentage": percentage})
    return cleaned


class FundIndex:
    def __init__(self) -> None:
        self._loaded: bool = False
        self._entries: list[dict[str, Any]] = []
        self._entries_by_isin: dict[str, dict[str, Any]] = {}
        self._detail_cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._data_path: Path | None = None

    def _find_md_file(self) -> Path | None:
        candidates = [
            _REPO_ROOT / "data/fund_holdings_aggregate/regular-growth-by-amc.md",
            _REPO_ROOT / "data/regular-growth-by-amc.md",
        ]
        for path in candidates:
            if path.is_file():
                return path
        return None

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return

            md_path = self._find_md_file()
            entries: list[dict[str, Any]] = []
            entries_by_isin: dict[str, dict[str, Any]] = {}

            if md_path and md_path.is_file():
                self._data_path = md_path
                try:
                    text = md_path.read_text(encoding="utf-8")
                    current_amc = ""
                    amc_headers: list[str] = []
                    for line in text.splitlines():
                        line = line.strip()
                        if line.startswith("## "):
                            current_amc = line.replace("## ", "").strip()
                            if current_amc:
                                amc_headers.append(current_amc)
                        elif line.startswith("- ") and "—" in line:
                            parts = line[2:].split("—")
                            if len(parts) >= 2:
                                fname = parts[0].strip()
                                isin = parts[1].replace("`", "").strip()
                                cat, stype = _infer_category_and_type(fname)
                                entry = {
                                    "isin": isin,
                                    "fund_name": fname,
                                    "fund_short_name": fname,
                                    "amc": current_amc,
                                    "plan": "Regular",
                                    "option": "Growth",
                                    "category": cat,
                                    "scheme_type": stype,
                                    "as_on": "",
                                    "name_lower": fname.lower(),
                                    "name_norm": _normalize_fund_text(fname),
                                    "isin_lower": isin.lower(),
                                }
                                entries.append(entry)
                                entries_by_isin[isin.upper()] = entry
                    cat = install_amc_catalog(amc_headers)
                    _sync_amc_prefix_from_catalog()
                    logger.info(
                        "Loaded %d Regular Growth funds (%d AMCs, %d AMC prefixes) from %s",
                        len(entries),
                        len(amc_headers),
                        len(cat.prefixes),
                        md_path.name,
                    )
                except Exception as exc:
                    logger.exception("Failed loading funds from markdown %s: %s", md_path, exc)

            # Fallback to json if markdown was empty or missing
            if not entries:
                json_candidates = [
                    _REPO_ROOT / "data/fund_holdings_aggregate/allisin_sectors_with_holdings.json",
                    _REPO_ROOT / "data/fund_holdings_aggregate/fund_sectors_and_holdings_aggregate.json",
                ]
                for jpath in json_candidates:
                    if jpath.is_file():
                        try:
                            with open(jpath, "r", encoding="utf-8") as f:
                                raw = json.load(f)
                            if isinstance(raw, dict):
                                for isin, val in raw.items():
                                    if isin.startswith("_") or not isinstance(val, dict):
                                        continue
                                    fname = str(val.get("fund_short_name") or val.get("fund_name") or isin).strip()
                                    cat = str(val.get("category") or "").strip()
                                    stype = str(val.get("scheme_type") or "").strip()
                                    entry = {
                                        "isin": isin,
                                        "fund_name": fname,
                                        "fund_short_name": fname,
                                        "amc": "",
                                        "plan": "Regular",
                                        "option": "Growth",
                                        "category": cat,
                                        "scheme_type": stype,
                                        "as_on": str(val.get("as_on") or ""),
                                        "name_lower": fname.lower(),
                                        "name_norm": _normalize_fund_text(fname),
                                        "isin_lower": isin.lower(),
                                    }
                                    entries.append(entry)
                                    entries_by_isin[isin.upper()] = entry
                            logger.info("Fallback loaded %d funds from %s", len(entries), jpath.name)
                            break
                        except Exception:
                            pass

            if get_amc_catalog() is None:
                install_amc_catalog([])
                _sync_amc_prefix_from_catalog()

            self._entries = entries
            self._entries_by_isin = entries_by_isin
            self._loaded = True

    def sample_fund_names(self, n: int = 2, name_contains: str = "") -> list[str]:
        """Pick n catalog funds, preferring different AMCs, for an unnamed comparison.

        `name_contains` is a hint chosen by the planner (for example "flexi"); every word must
        appear in the fund name. When it matches too few funds it is ignored.
        """
        import random

        self._ensure_loaded()
        pool = [e for e in self._entries if e.get("fund_name")]
        words = [w for w in re.split(r"\s+", (name_contains or "").lower().strip()) if w]
        if words:
            hinted = [e for e in pool if all(w in str(e.get("fund_name")).lower() for w in words)]
            if len(hinted) >= max(1, n):
                pool = hinted
                words = ["_hinted_"]
            else:
                words = []
        # Random picks should have a meaningful sector mix: skip debt/liquid/gilt/gold-type schemes.
        _non_equity = re.compile(
            r"gilt|liquid|overnight|debt|bond|money market|treasury|duration|credit risk|banking & psu|"
            r"fixed maturity|\bfmp\b|\bg-?sec\b|ibx|sdl|gold|silver|arbitrage|floater|ultra short|low duration|"
            r"fund of funds|\bfof\b|etf|multi asset",
            re.I,
        )
        _equity = re.compile(
            r"equity|cap\b|flexi|focus|elss|tax saver|value|contra|dividend yield|sectoral|thematic|infra|"
            r"pharma|health|bank|financial|technology|\bit\b|consumption|opportunit|bluechip|blue chip|"
            r"manufactur|energy|\bpsu\b|\besg\b|quant|nifty 50|sensex|momentum|alpha|growth fund|"
            r"innovation|business cycle|mnc|digital|auto",
            re.I,
        )
        equity_pool = [
            e for e in pool
            if _equity.search(str(e.get("fund_name"))) and not _non_equity.search(str(e.get("fund_name")))
        ]
        if len(equity_pool) >= 5 and words != ["_hinted_"]:
            pool = equity_pool
        n = max(1, n)
        if len(pool) <= n:
            return [str(e["fund_name"]) for e in pool]
        shuffled = list(pool)
        random.shuffle(shuffled)
        picked: list[str] = []
        seen_amc: set[str] = set()
        for entry in shuffled:
            amc = str(entry.get("amc") or "")
            if amc and amc in seen_amc:
                continue
            picked.append(str(entry["fund_name"]))
            if amc:
                seen_amc.add(amc)
            if len(picked) >= n:
                return picked
        for entry in shuffled:
            name = str(entry["fund_name"])
            if name not in picked:
                picked.append(name)
            if len(picked) >= n:
                break
        return picked

    def search(self, query: str, limit: int = 15) -> list[dict[str, Any]]:
        """Search funds by name or ISIN with autocomplete ranking."""
        self._ensure_loaded()
        q = (query or "").strip().lower()
        if not q:
            return [
                {
                    "isin": e["isin"],
                    "fund_short_name": e["fund_short_name"],
                    "plan": e.get("plan", "Regular"),
                    "option": e.get("option", "Growth"),
                    "category": e["category"],
                    "scheme_type": e["scheme_type"],
                    "as_on": e.get("as_on", ""),
                }
                for e in self._entries[:limit]
            ]

        exact_isin: list[dict] = []
        prefix_isin: list[dict] = []
        name_starts: list[dict] = []
        word_starts: list[dict] = []
        contains: list[dict] = []

        norm_q = _normalize_fund_text(q)
        q_words = norm_q.split()

        for e in self._entries:
            isin_lower = e["isin_lower"]
            name_lower = e["name_lower"]
            name_norm = e.get("name_norm") or _normalize_fund_text(name_lower)

            if isin_lower == q:
                exact_isin.append(e)
            elif isin_lower.startswith(q):
                prefix_isin.append(e)
            elif name_lower.startswith(q) or name_norm.startswith(norm_q):
                name_starts.append(e)
            elif any(w.startswith(q) for w in name_lower.split()) or any(w.startswith(norm_q) for w in name_norm.split()):
                word_starts.append(e)
            elif all(w in name_norm for w in q_words) or all(w in name_lower for w in q.split()) or q in isin_lower:
                contains.append(e)

        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        for group in (exact_isin, prefix_isin, name_starts, word_starts, contains):
            for e in group:
                if e["isin"] not in seen:
                    seen.add(e["isin"])
                    results.append(
                        {
                            "isin": e["isin"],
                            "fund_short_name": e["fund_short_name"],
                            "amc": e.get("amc", ""),
                            "plan": e.get("plan", "Regular"),
                            "option": e.get("option", "Growth"),
                            "category": e["category"],
                            "scheme_type": e["scheme_type"],
                            "as_on": e.get("as_on", ""),
                        }
                    )
                    if len(results) >= limit:
                        return results

        return results

    def fetch_fund_detail_from_api(self, isin: str, timeout: float = 12.0) -> dict[str, Any] | None:
        """Fetches full live fund sectors, holdings, NAV and metadata from RupeeStop backend API."""
        isin_clean = resolve_canonical_isin(isin)
        if isin_clean != (isin or "").strip().upper():
            logger.info("Resolved legacy ISIN %s → %s for fund API", isin.strip().upper(), isin_clean)
        url = f"{_API_BASE_URL}/{isin_clean}"
        payload = None
        for attempt in range(3):  # transient read timeouts must not silently produce an empty fund
            try:
                with httpx.Client(timeout=timeout + 6.0 * attempt) as client:
                    resp = client.get(url)
                    if resp.status_code != 200:
                        logger.warning("RupeeStop fund API returned status %d for ISIN %s", resp.status_code, isin_clean)
                        if resp.status_code < 500:
                            return None
                        continue
                    payload = resp.json()
                    break
            except Exception as exc:
                logger.warning(
                    "Failed to fetch fund detail from RupeeStop API for %s (attempt %d/3): %s",
                    isin_clean, attempt + 1, exc,
                )
        if payload is None:
            return None

        raw = payload.get("data") or {}
        if not raw or not isinstance(raw, dict):
            return None

        ident = raw.get("identity") or {}
        facts = raw.get("fund_facts") or {}
        nav = raw.get("nav") or {}
        ret = raw.get("returns") or {}
        ratios = raw.get("ratios") or {}
        alloc = raw.get("allocations") or {}
        port = raw.get("portfolio") or {}

        # 1. Process sectors into standard { sector_name: percentage } map
        raw_sectors = alloc.get("sector_from_holdings") or alloc.get("sector") or []
        sectors: dict[str, float] = {}
        if isinstance(raw_sectors, list):
            for s in raw_sectors:
                if isinstance(s, dict):
                    sname = str(s.get("sector") or s.get("name") or "").strip()
                    if sname:
                        try:
                            sectors[sname] = float(s.get("percentage") or 0.0)
                        except Exception:
                            pass
        elif isinstance(raw_sectors, dict):
            for sname, pct in raw_sectors.items():
                try:
                    sectors[str(sname).strip()] = float(pct or 0.0)
                except Exception:
                    pass

        # 2. Process holdings into standard { company_name: {percentage, industry, rating, market_value} }
        raw_holdings = port.get("holdings") or []
        holdings: dict[str, dict[str, Any]] = {}
        if isinstance(raw_holdings, list):
            for h in raw_holdings:
                if isinstance(h, dict):
                    hname = _clean_company_name(h.get("instrument_name") or h.get("company_name") or h.get("name") or "")
                    if hname:
                        pct = float(h.get("percentage") or 0.0)
                        ind = str(h.get("industry") or h.get("asset_type") or "Equity").strip()
                        rat = str(h.get("rating") or "").strip()
                        mv = float(h.get("market_value") or 0.0) if h.get("market_value") is not None else None
                        holdings[hname] = {
                            "percentage": pct,
                            "industry": ind,
                            "rating": rat,
                            "market_value": mv,
                        }
        elif isinstance(raw_holdings, dict):
            for hname, meta in raw_holdings.items():
                cname = _clean_company_name(hname)
                if isinstance(meta, dict):
                    holdings[cname] = {
                        "percentage": float(meta.get("percentage") or 0.0),
                        "industry": str(meta.get("industry") or "Equity"),
                        "rating": str(meta.get("rating") or ""),
                    }
                else:
                    try:
                        p = float(meta)
                    except Exception:
                        p = 0.0
                    holdings[cname] = {"percentage": p, "industry": "Equity", "rating": ""}

        # 3. Process returns
        returns_map: dict[str, Any] = {}
        if isinstance(ret, dict):
            for period in ["1m", "3m", "6m", "1y", "3y", "5y", "ytd", "inception"]:
                val_obj = ret.get(period)
                if isinstance(val_obj, dict):
                    returns_map[period] = val_obj.get("value")
                elif val_obj is not None:
                    returns_map[period] = val_obj
            extra = ret.get("extra") or {}
            if isinstance(extra, dict):
                for period in ["1w", "9m", "2y", "4y"]:
                    val_obj = extra.get(period)
                    if isinstance(val_obj, dict):
                        returns_map[period] = val_obj.get("value")
                    elif val_obj is not None:
                        returns_map[period] = val_obj

        # Dates & identification
        as_on = (
            str(port.get("portfolio_date") or "").strip()
            or str((raw.get("as_on") or {}).get("accord") or "").strip()
            or str((raw.get("as_on") or {}).get("nav") or "").strip()
        )

        entry_meta = self._entries_by_isin.get(isin_clean) or {}

        api_name = str(ident.get("fund_name") or "").strip()
        api_short = str(ident.get("fund_short_name") or ident.get("fund_name") or "").strip()
        if entry_meta.get("fund_short_name"):
            fund_name = str(entry_meta.get("fund_name") or api_name or isin_clean)
            fund_short_name = str(entry_meta.get("fund_short_name"))
        else:
            fund_name = api_name or isin_clean
            fund_short_name = api_short or fund_name

        cat = (
            ident.get("category")
            or ident.get("sebi_category")
            or ident.get("morningstar_category_short")
            or ident.get("sub_category")
            or entry_meta.get("category")
            or ""
        )
        from news_rag.fund_rupeestop_metrics import normalize_category_average_returns, parse_fund_costs

        category_average_returns = normalize_category_average_returns(
            ratios.get("category_averages") if isinstance(ratios, dict) else None
        )
        costs = parse_fund_costs(facts if isinstance(facts, dict) else None)
        stype = ident.get("scheme_type") or entry_meta.get("scheme_type") or "Equity"
        plan = ident.get("plan") or entry_meta.get("plan") or "Regular"
        opt = ident.get("option") or entry_meta.get("option") or "Growth"

        detail: dict[str, Any] = {
            "isin": isin_clean,
            "fund_name": fund_name,
            "fund_short_name": fund_short_name,
            "category": cat,
            "scheme_type": stype,
            "plan": plan,
            "option": opt,
            "as_on": as_on,
            "benchmark": facts.get("benchmark") or get_fund_benchmark(cat, fund_name),
            "nav": nav.get("value"),
            "nav_date": nav.get("date"),
            "nav_day_change": nav.get("day_change"),
            "nav_day_change_pct": nav.get("day_change_pct"),
            "high_52w": nav.get("high_52w"),
            "low_52w": nav.get("low_52w"),
            "returns": returns_map,
            "category_average_returns": category_average_returns,
            "expense_ratio": costs.get("expense_ratio") or {},
            "exit_load_remarks": costs.get("exit_load_remarks") or "",
            "exit_load_summary": costs.get("exit_load_summary") or "",
            "aum": costs.get("aum"),
            "aum_as_on_date": costs.get("aum_as_on_date") or "",
            "inception_date": str(ident.get("inception_date") or "").strip(),
            "sebi_riskometer": _fund_text(
                ident.get("sebi_riskometer")
                or raw.get("sebi_riskometer")
                or ((raw.get("risk") or {}).get("sebi_riskometer") if isinstance(raw.get("risk"), dict) else "")
            ),
            "market_cap": _named_weights(raw.get("market_cap") or alloc.get("market_cap") or port.get("market_cap")),
            "asset_allocation": _named_weights(alloc.get("asset")),
            "risk_label": str((raw.get("risk") or {}).get("label") or "").strip() if isinstance(raw.get("risk"), dict) else "",
            "managers": parse_fund_managers_from_api_payload(raw),
            "sectors": sectors,
            "holdings": holdings,
        }

        with self._lock:
            self._detail_cache[isin_clean] = detail

        return detail

    def catalog_entry(self, isin: str) -> dict[str, Any] | None:
        """Local Regular Growth catalog row only — no live fund API."""
        self._ensure_loaded()
        raw = (isin or "").strip().upper()
        if not raw:
            return None
        return self._entries_by_isin.get(raw) or self._entries_by_isin.get(resolve_canonical_isin(raw))

    def isins_in_category(self, category: str, *, exclude_isin: str = "", limit: int = 30) -> tuple[list[str], bool]:
        """Other regular-growth schemes in the same catalog category."""
        self._ensure_loaded()
        wanted = (category or "").strip().casefold()
        skip = (exclude_isin or "").strip().upper()
        if not wanted:
            return [], False
        matches: list[str] = []
        for entry in self._entries:
            isin = str(entry.get("isin") or "").strip().upper()
            label = str(entry.get("category") or "").strip().casefold()
            if not isin or isin == skip or label != wanted:
                continue
            matches.append(isin)
        truncated = len(matches) > limit
        return matches[:limit], truncated

    def get_fund_detail(self, isin: str) -> dict[str, Any] | None:
        """Get full details (sectors, holdings, info) for an ISIN with caching."""
        self._ensure_loaded()
        raw_isin = isin.strip().upper()
        isin_clean = resolve_canonical_isin(raw_isin)

        # A catalog-only stub has no NAV or holdings. Drop it and try the API again.
        with self._lock:
            cached = self._detail_cache.get(isin_clean) or self._detail_cache.get(raw_isin)
            if cached is not None and not detail_has_live_facts(cached):
                self._detail_cache.pop(isin_clean, None)
                self._detail_cache.pop(raw_isin, None)
                cached = None
            if cached is not None:
                if raw_isin != isin_clean:
                    return {**cached, "isin": isin_clean, "legacy_isin": raw_isin}
                return cached

        # Fetch from live RupeeStop API
        detail = self.fetch_fund_detail_from_api(isin_clean)
        if detail:
            return detail

        # Fallback to local entries metadata if API was unreachable or has no data
        entry = self._entries_by_isin.get(isin_clean) or self._entries_by_isin.get(raw_isin)
        if entry:
            fallback = {
                "isin": isin_clean,
                "fund_name": entry["fund_name"],
                "fund_short_name": entry["fund_short_name"],
                "category": entry["category"],
                "scheme_type": entry["scheme_type"],
                "plan": entry["plan"],
                "option": entry["option"],
                "as_on": entry.get("as_on", ""),
                "benchmark": get_fund_benchmark(entry["category"], entry["fund_name"]),
                "sectors": {},
                "holdings": {},
            }
            return fallback

        return None

    def lookup_extracted_fund(
        self,
        isin: str = "",
        name: str = "",
    ) -> tuple[dict[str, Any] | None, bool, list[str]]:
        """Lookup fund by exact ISIN or extracted scheme name only.

        Returns:
            (fund_detail, is_ambiguous, close_matches)
        """
        self._ensure_loaded()
        clean_isin = (isin or "").strip().upper()
        clean_name = (name or "").strip()

        # 1. Exact ISIN lookup
        if clean_isin:
            isin_match = re.search(r"\b(INF[A-Z0-9]{9})\b", clean_isin)
            target_isin = isin_match.group(1).upper() if isin_match else clean_isin
            detail = self.get_fund_detail(target_isin)
            if detail:
                return detail, False, []

        # Check if name contains an ISIN
        if clean_name:
            isin_in_name = re.search(r"\b(INF[A-Z0-9]{9})\b", clean_name, re.IGNORECASE)
            if isin_in_name:
                detail = self.get_fund_detail(isin_in_name.group(1).upper())
                if detail:
                    return detail, False, []

        if not clean_name:
            return None, False, []

        if not _is_plausible_scheme_phrase(clean_name):
            return None, False, []

        alias_isin = _scheme_alias_isin(clean_name)
        if alias_isin:
            detail = self.get_fund_detail(alias_isin)
            if detail:
                entry = self._entries_by_isin.get(alias_isin.upper())
                if entry:
                    detail = {
                        **detail,
                        "fund_name": entry.get("fund_name") or detail.get("fund_name"),
                        "fund_short_name": entry.get("fund_short_name") or detail.get("fund_short_name"),
                        "amc": entry.get("amc") or detail.get("amc"),
                    }
                return detail, False, []

        norm_name = _normalize_fund_text(clean_name)
        stop_words = {
            "fund", "funds", "mutual", "scheme", "plan", "growth", "regular",
            "the", "and", "of", "in", "for", "to", "a", "an", "is", "about",
            "life", "sun",
        }
        q_tokens = [w for w in re.findall(r"\b[a-z0-9]+\b", norm_name) if len(w) >= 2 and w not in stop_words]
        if not q_tokens:
            return None, False, []

        amc_hints = _amc_hints_from_tokens(q_tokens)

        pool: list[dict[str, Any]] = list(self._entries)
        if amc_hints:
            pool = [e for e in pool if _entry_matches_amc(e, amc_hints)]
            if not pool:
                return None, False, []

        settings = get_settings()
        from news_rag.fund_match import (
            catalog_name_for_match,
            embedding_best_match,
            load_fund_embedding_cache,
            rank_catalog_entries_for_phrase,
        )

        ranked = [
            row
            for row in rank_catalog_entries_for_phrase(clean_name, pool)
            if _entry_matches_query_scheme(clean_name, row[1])
        ]
        accept = float(settings.fund_fuzzy_accept)
        reject = float(settings.fund_fuzzy_reject)
        gap = float(settings.fund_fuzzy_ambiguous_gap)
        if amc_hints:
            accept = min(accept, 86.0)

        if ranked:
            top_score, top_entry, _ = ranked[0]
            second_score = ranked[1][0] if len(ranked) > 1 else 0.0
            if top_score >= accept:
                if len(ranked) > 1 and abs(top_score - second_score) < gap:
                    close = [str(e[1].get("fund_short_name") or "") for e in ranked[:5]]
                    return None, True, [n for n in close if n]
                detail = self.get_fund_detail(str(top_entry["isin"]))
                if detail:
                    return detail, False, []
            if reject <= top_score < accept:
                cache = load_fund_embedding_cache()
                if cache:
                    _emb_score, emb_entry = embedding_best_match(clean_name, pool, cache)
                    if (
                        emb_entry is not None
                        and _emb_score >= 0.55
                        and _entry_matches_query_scheme(clean_name, emb_entry)
                    ):
                        detail = self.get_fund_detail(str(emb_entry["isin"]))
                        if detail:
                            return detail, False, []

        scored_candidates: list[tuple[float, dict[str, Any]]] = []
        for entry in pool:
            c_name = catalog_name_for_match(entry)
            c_norm = _normalize_fund_text(c_name)
            c_tokens = set(re.findall(r"\b[a-z0-9]+\b", c_norm))

            matched: list[str] = []
            for t in q_tokens:
                expanded = _expand_query_token(t)
                if expanded & c_tokens:
                    matched.append(t)
                elif any(
                    any(ct.startswith(ex) or ex.startswith(ct) for ct in c_tokens)
                    for ex in expanded
                    if len(ex) >= 4
                ):
                    matched.append(t)

            coverage = len(matched) / len(q_tokens) if q_tokens else 0.0

            score = coverage * 100.0
            if len(matched) == len(q_tokens):
                score += 50.0
            if norm_name in c_norm or c_norm in norm_name:
                score += 40.0
            # Prefer schemes whose category tokens align (large / mid / cap)
            for cat_token in ("large", "mid", "small", "flexi", "multi"):
                if cat_token in q_tokens and cat_token in c_tokens:
                    score += 8.0
            # "large cap" without "mid" must not map to Large & Mid Cap.
            if "large" in q_tokens and "cap" in q_tokens and "mid" not in q_tokens:
                if "mid" in c_norm and ("large" in c_norm or "&" in c_name or "and" in c_norm):
                    score -= 45.0
            if "mid" in q_tokens and "cap" in q_tokens and "large" not in q_tokens:
                if "large" in c_norm and "mid" in c_norm:
                    score -= 35.0
            if "mid" not in q_tokens and re.search(r"\bmid\b", c_norm) and "large" in q_tokens:
                score -= 25.0

            score += _index_benchmark_score_adjustment(norm_name, c_norm)

            if "us" in c_tokens and "us" not in q_tokens and "international" not in norm_name:
                score -= 40.0
            if "global" in c_norm and not any(
                x in norm_name for x in ("global", "international", "us", "world", "overseas")
            ):
                score -= 25.0

            if amc_hints and not _entry_matches_amc(entry, amc_hints):
                continue

            if (coverage >= 0.45 or (norm_name in c_norm)) and _entry_matches_query_scheme(clean_name, entry):
                scored_candidates.append((score, entry))

        if not scored_candidates:
            candidates = self.search(norm_name, limit=20)
            for c in candidates:
                entry = self._entries_by_isin.get(str(c.get("isin") or "").upper())
                if not entry or (amc_hints and not _entry_matches_amc(entry, amc_hints)):
                    continue
                if _entry_matches_query_scheme(clean_name, entry):
                    scored_candidates.append((80.0, entry))

        if not scored_candidates and ranked and ranked[0][0] >= reject:
            detail = self.get_fund_detail(str(ranked[0][1]["isin"]))
            if detail:
                return detail, False, []

        if not scored_candidates:
            return None, False, []

        scored_candidates.sort(key=lambda x: (-x[0], str(x[1].get("fund_short_name") or "")))
        top_score, top_entry = scored_candidates[0]

        close_matches = [
            str(e.get("fund_short_name") or "")
            for score, e in scored_candidates[:8]
            if abs(score - top_score) < 12.0
        ]
        close_matches = [n for n in close_matches if n]

        if len(set(close_matches)) > 1 and top_score < 145.0:
            return None, True, close_matches[:5]

        detail = self.get_fund_detail(str(top_entry["isin"]))
        return detail, False, []


def _entry_matches_query_scheme(query_name: str, entry: dict[str, Any]) -> bool:
    """A large-cap question stays on a large-cap scheme, not a mid-cap or trigger plan."""
    q = set(_normalize_fund_text(query_name).split())
    c = set(_normalize_fund_text(str(entry.get("fund_name") or entry.get("fund_short_name") or "")).split())
    if "trigger" in c and "trigger" not in q:
        return False
    if "large" in q and "cap" in q and "mid" not in q:
        return "large" in c and "cap" in c and "mid" not in c
    if "mid" in q and "cap" in q and "large" not in q:
        return "mid" in c and "cap" in c and "large" not in c
    if "small" in q and "cap" in q:
        return "small" in c and "cap" in c
    if "flexi" in q and "flexi" not in c:
        return False
    if "frontline" in q and "frontline" not in c:
        return False
    if "etf" in q and "etf" not in c:
        return False
    return True


def lookup_extracted_fund(
    isin: str = "",
    name: str = "",
) -> tuple[dict[str, Any] | None, bool, list[str]]:
    """Convenience helper to lookup fund from global fund index."""
    return get_fund_index().lookup_extracted_fund(isin=isin, name=name)


_NON_STOCK_HOLDING = re.compile(
    r"treps|reverse\s+repo|cash|net\s+current|net\s+receivable|cblo|treasury|gold\s+etf|silver\s+etf",
    re.I,
)


def detail_has_live_facts(detail: dict[str, Any] | None) -> bool:
    """True when the record came from the fund API, not the local name catalog."""
    if not isinstance(detail, dict):
        return False
    if detail.get("nav") is not None:
        return True
    holdings = detail.get("holdings") or {}
    return bool(holdings)


def _holding_overlap_key(name: str) -> str:
    text = re.sub(r"\b(?:ltd|limited|inc|corp|corporation|plc)\b\.?", "", name.lower())
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def build_holding_overlap(details: list[dict[str, Any]]) -> dict[str, Any]:
    """Stocks held by at least two of the funds, using each fund's full holdings list."""
    books: list[dict[str, Any]] = []
    for detail in details:
        weights: dict[str, tuple[str, float]] = {}
        for row in extract_top_holdings(detail, limit=5000):
            name = str(row.get("name") or "").strip()
            key = _holding_overlap_key(name)
            if not key or _NON_STOCK_HOLDING.search(name):
                continue
            industry = str(row.get("industry") or "")
            if re.search(r"\b(?:cash|debt|gilt|repo)\b", industry, re.I):
                continue
            weights[key] = (name, float(row.get("percentage") or 0.0))
        books.append(
            {
                "fund_name": str(detail.get("fund_short_name") or detail.get("fund_name") or "Fund"),
                "weights": weights,
            }
        )
    counts: dict[str, int] = {}
    for book in books:
        for key in book["weights"]:
            counts[key] = counts.get(key, 0) + 1
    rows: list[dict[str, Any]] = []
    for key, count in counts.items():
        if count < 2:
            continue
        display = next(book["weights"][key][0] for book in books if key in book["weights"])
        weights_out = {
            book["fund_name"]: book["weights"][key][1]
            for book in books
            if key in book["weights"]
        }
        rows.append({"stock": display, "weights": weights_out})
    rows.sort(key=lambda row: sum(row["weights"].values()), reverse=True)
    return {
        "fund_names": [book["fund_name"] for book in books],
        "overlap_count": len(rows),
        "rows": rows,
    }


def extract_top_holdings(detail: dict[str, Any] | None, limit: int = 10) -> list[dict[str, Any]]:
    """Robustly extracts and sorts top equity holdings from fund detail dictionary."""
    if not detail:
        return []
    raw = detail.get("holdings") or {}
    items: list[dict[str, Any]] = []

    if isinstance(raw, dict):
        for name, meta in raw.items():
            cname = _clean_company_name(name)
            if isinstance(meta, dict):
                pct = float(meta.get("percentage") or 0.0)
                ind = meta.get("industry", "Equity")
            else:
                try:
                    pct = float(meta)
                except Exception:
                    pct = 0.0
                ind = "Equity"
            items.append({"name": cname, "percentage": pct, "industry": ind})
    elif isinstance(raw, list):
        for h in raw:
            if isinstance(h, dict):
                name = _clean_company_name(h.get("instrument_name") or h.get("company_name") or h.get("name") or "")
                pct = float(h.get("percentage") or 0.0)
                ind = h.get("industry", "Equity")
                items.append({"name": name, "percentage": pct, "industry": ind})
            elif isinstance(h, str):
                items.append({"name": _clean_company_name(h), "percentage": 0.0, "industry": "Equity"})
    items.sort(key=lambda x: x["percentage"], reverse=True)
    return items[:limit]


def normalize_holding_row(raw: dict[str, Any]) -> dict[str, Any]:
    """Canonical keys for templates and UI (name + weight_pct + sector)."""
    pct = float(
        raw.get("percentage")
        or raw.get("weight_pct")
        or raw.get("weight")
        or 0.0
    )
    name = str(
        raw.get("name")
        or raw.get("company_name")
        or raw.get("instrument_name")
        or ""
    ).strip()
    sector = str(raw.get("industry") or raw.get("sector") or "").strip()
    return {
        "name": name,
        "company_name": name,
        "percentage": pct,
        "weight_pct": pct,
        "industry": sector,
        "sector": sector,
    }


def aggregate_sectors_from_holdings(
    holdings: list[dict[str, Any]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """When the API has no sector file, roll up holding industries (gilt, FOF, etc.)."""
    buckets: dict[str, float] = {}
    for h in holdings:
        label = str(h.get("industry") or h.get("sector") or "").strip() or "Other"
        try:
            pct = float(h.get("percentage") or h.get("weight_pct") or 0.0)
        except (TypeError, ValueError):
            pct = 0.0
        if pct <= 0:
            continue
        buckets[label] = buckets.get(label, 0.0) + pct
    total = sum(buckets.values())
    # Multiple GOI lines rolled into one label can exceed 100% — prefer constituent table instead.
    if total > 102.0 or (len(buckets) == 1 and total > 99.5):
        return []
    rows = [{"sector": name, "percentage": pct} for name, pct in buckets.items()]
    rows.sort(key=lambda x: x["percentage"], reverse=True)
    return rows[: max(1, limit)]


def normalize_sector_row(raw: dict[str, Any]) -> dict[str, Any]:
    pct = float(
        raw.get("percentage")
        or raw.get("weight_pct")
        or raw.get("weight")
        or 0.0
    )
    sec = str(
        raw.get("sector")
        or raw.get("sector_label")
        or raw.get("name")
        or ""
    ).strip()
    return {"sector": sec, "percentage": pct, "weight_pct": pct}


def extract_top_sectors(detail: dict[str, Any] | None, limit: int = 8) -> list[dict[str, Any]]:
    """Robustly extracts and sorts top sector exposures from fund detail dictionary."""
    if not detail:
        return []
    raw = detail.get("sectors") or {}
    items: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for s, pct in raw.items():
            try:
                p = float(pct)
            except Exception:
                p = 0.0
            items.append({"sector": str(s), "percentage": p})
    elif isinstance(raw, list):
        for s in raw:
            if isinstance(s, dict):
                name = s.get("sector_label") or s.get("sector") or s.get("name") or ""
                p = float(s.get("percentage") or 0.0)
                items.append({"sector": str(name), "percentage": p})
            elif isinstance(s, str):
                items.append({"sector": s, "percentage": 0.0})
    items.sort(key=lambda x: x["percentage"], reverse=True)
    return items[:limit]


def get_fund_benchmark(category: str, fund_name: str = "") -> str:
    """Maps fund category and name to the standard AMFI/SEBI benchmark index."""
    c_lower = (category or "").lower()
    n_lower = (fund_name or "").lower()

    if "large & mid" in c_lower or "large and mid" in c_lower or "large & mid" in n_lower or "large and mid" in n_lower:
        return "Nifty LargeMidcap 250 TRI"
    elif "large cap" in c_lower or "largecap" in c_lower or "bluechip" in c_lower or "top 100" in n_lower or "large cap" in n_lower:
        return "Nifty 50 TRI"
    elif "small cap" in c_lower or "smallcap" in c_lower or "small cap" in n_lower:
        return "Nifty Smallcap 250 TRI"
    elif "mid cap" in c_lower or "midcap" in c_lower or "emerging equity" in n_lower or "mid cap" in n_lower:
        return "Nifty Midcap 150 TRI"
    elif "flexi" in c_lower or "multi" in c_lower or "focused" in c_lower or "value" in c_lower or "contra" in c_lower or "elss" in c_lower:
        return "Nifty 500 TRI"
    elif "bank" in c_lower or "financial" in c_lower or "bank" in n_lower:
        return "Nifty Financial Services TRI"
    elif "pharma" in c_lower or "health" in c_lower:
        return "Nifty Healthcare TRI"
    elif "tech" in c_lower or "it" in c_lower:
        return "Nifty IT TRI"
    elif "infra" in c_lower:
        return "Nifty Infrastructure TRI"
    elif "consumption" in c_lower:
        return "Nifty India Consumption TRI"
    elif "hybrid" in c_lower or "balanced" in c_lower:
        return "CRISIL Hybrid 35+65 Aggressive Index"
    elif "arbitrage" in c_lower or "liquid" in c_lower or "overnight" in c_lower:
        return "CRISIL Liquid Debt Index"
    return "Nifty 500 TRI"


def _normalize_manager_record(raw: dict[str, Any]) -> dict[str, Any]:
    schemes: list[dict[str, str]] = []
    for row in raw.get("other_schemes") or []:
        if not isinstance(row, dict):
            continue
        schemes.append(
            {
                "scheme_name": str(row.get("scheme_name") or "").strip(),
                "fund_house": str(row.get("fund_house") or "").strip(),
                "from_date": str(row.get("from_date") or "").strip(),
                "to_date": str(row.get("to_date") or "").strip(),
            }
        )
    basic = raw.get("basic_details")
    if basic is None:
        basic = raw.get("basic_detail")
    if isinstance(basic, str):
        basic = re.sub(r"\s+", " ", basic).strip()
    return {
        "manager_id": raw.get("manager_id"),
        "name": str(raw.get("name") or "").strip(),
        "designation": str(raw.get("designation") or "").strip(),
        "qualification": str(raw.get("qualification") or "").strip(),
        "basic_details": str(basic or "").strip(),
        "managing_since": str(raw.get("managing_since") or "").strip(),
        "total_experience_years": raw.get("total_experience_years"),
        "experience_last_updated": str(raw.get("experience_last_updated") or "").strip(),
        "age": raw.get("age"),
        "other_schemes": schemes[:12],
    }


def parse_fund_managers_from_api_payload(raw: dict[str, Any]) -> dict[str, Any]:
    """Extract current/past managers from RupeeStop /api/v1/app/fund/{isin} payload."""
    block = raw.get("fund_managers") if isinstance(raw.get("fund_managers"), dict) else {}
    current = [
        _normalize_manager_record(m)
        for m in (block.get("current") or [])
        if isinstance(m, dict) and str(m.get("name") or "").strip()
    ]
    past = [
        _normalize_manager_record(m)
        for m in (block.get("past") or [])
        if isinstance(m, dict) and str(m.get("name") or "").strip()
    ]
    return {"current": current, "past": past[:6]}


def _fund_context_for_managers(raw: dict[str, Any]) -> dict[str, Any]:
    ident = raw.get("identity") or {}
    facts = raw.get("fund_facts") or {}
    risk = raw.get("risk") or {}
    objective = raw.get("objective")
    cat = str(ident.get("category") or ident.get("sebi_category") or "").strip()
    sebi = str(ident.get("sebi_category") or "").strip()
    blob = f"{cat} {sebi}".lower()
    is_index = "index" in blob or "etf" in blob
    obj_text = ""
    if isinstance(objective, str):
        obj_text = objective.strip()
    elif isinstance(objective, dict):
        obj_text = str(objective.get("text") or objective.get("description") or "").strip()
    return {
        "category": cat,
        "scheme_type": str(ident.get("scheme_type") or "").strip(),
        "plan": str(ident.get("plan") or "").strip(),
        "option": str(ident.get("option") or "").strip(),
        "inception_date": str(ident.get("inception_date") or "").strip(),
        "benchmark": str(facts.get("benchmark") or "").strip(),
        "risk_label": str(risk.get("label") or "").strip(),
        "objective": obj_text[:500] if obj_text else "",
        "is_index_fund": is_index,
    }


def fetch_fund_managers_for_isin(isin: str, *, timeout: float = 12.0) -> dict[str, Any] | None:
    """Live fund manager facts from RupeeStop fund detail API."""
    isin_clean = resolve_canonical_isin((isin or "").strip().upper())
    if not isin_clean:
        return None
    url = f"{_API_BASE_URL}/{isin_clean}"
    payload = None
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    for attempt in range(3):
        try:
            with httpx.Client(timeout=timeout + 6.0 * attempt) as client:
                resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                if resp.status_code < 500:
                    return None
                continue
            payload = resp.json()
            break
        except Exception as exc:
            logger.warning("Fund managers API fetch failed for %s (attempt %d): %s", isin_clean, attempt + 1, exc)
    if not payload or not payload.get("success"):
        return None
    raw = payload.get("data") or {}
    if not isinstance(raw, dict):
        return None
    ident = raw.get("identity") or {}
    managers = parse_fund_managers_from_api_payload(raw)
    if not managers.get("current") and not managers.get("past"):
        return None
    return {
        "isin": isin_clean,
        "fund_name": str(ident.get("fund_name") or ident.get("fund_short_name") or isin_clean).strip(),
        "context": _fund_context_for_managers(raw),
        **managers,
    }


def fetch_fund_managers_for_query(fund_query: str) -> dict[str, Any] | None:
    text = fund_query or ""
    isin_m = _ISIN_IN_TEXT.search(text)
    if isin_m:
        data = fetch_fund_managers_for_isin(isin_m.group(1).upper())
        if data:
            return data
    detail, _amb, _close = resolve_fund_for_query(text)
    isin = str((detail or {}).get("isin") or "").strip().upper()
    if not isin:
        return None
    data = fetch_fund_managers_for_isin(isin)
    if data and detail:
        data = prefer_resolved_fund_name(data, detail)
    return data


def prefer_resolved_fund_name(data: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    """Show the scheme the query resolved. The manager API can still carry an old name."""
    from news_rag.fund_match import labels_name_the_same_scheme

    catalog = str(detail.get("fund_name") or detail.get("fund_short_name") or "").strip()
    api_name = str(data.get("fund_name") or "").strip()
    if catalog and api_name and not labels_name_the_same_scheme(catalog, api_name):
        data["api_fund_name"] = api_name
        data["fund_name"] = catalog
    elif catalog and not api_name:
        data["fund_name"] = catalog
    return data


_fund_index: FundIndex | None = None


def get_fund_index() -> FundIndex:
    global _fund_index
    if _fund_index is None:
        _fund_index = FundIndex()
    return _fund_index
