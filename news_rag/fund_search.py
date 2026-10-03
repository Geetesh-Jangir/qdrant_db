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

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]
_API_BASE_URL = "https://backend.rupeestop.com/api/v1/app/fund"

# Pre-merger HDFC MF ISINs (INF063A*) → current HDFC AMC codes served by the API.
_ISIN_ALIASES: dict[str, str] = {
    "INF063A01027": "INF179KA1RT1",  # HDFC Large & Mid Cap Regular Growth
    "INF063A01050": "INF179KA1RZ8",  # HDFC Small Cap Regular Growth
}

# Colloquial / legacy scheme names → Regular Growth ISIN in our universe.
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
    "zerodha": ("zerodha", "smallcase"),
    "whiteoak": ("whiteoak", "white oak"),
    "lic": ("lic", "life insurance"),
    "mahindra": ("mahindra",),
    "sundaram": ("sundaram",),
    "union": ("union",),
    "nj": ("nj",),
    "trust": ("trust",),
}


def _amc_hints_from_tokens(tokens: list[str]) -> list[str]:
    hints: list[str] = []
    joined = " ".join(tokens)
    for key, needles in _AMC_HINT_TOKENS.items():
        if key in tokens or any(n in joined for n in needles):
            hints.append(key)
    return hints


def _entry_matches_amc(entry: dict[str, Any], hints: list[str]) -> bool:
    if not hints:
        return True
    amc = _normalize_fund_text(str(entry.get("amc") or ""))
    name = _normalize_fund_text(str(entry.get("fund_short_name") or entry.get("fund_name") or ""))
    blob = f"{amc} {name}"
    for hint in hints:
        needles = _AMC_HINT_TOKENS.get(hint, (hint,))
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


def _scheme_alias_isin(norm_name: str) -> str | None:
    key = _normalize_fund_text(norm_name)
    key = re.sub(r"\s+-\s+.*$", "", key).strip()
    key = re.sub(r"\s+fund\s*$", "", key).strip()
    return _SCHEME_NAME_TO_ISIN.get(key)


def is_market_fund_discovery_question(question: str) -> bool:
    """Top-N / which-funds market queries — do not bind a single scheme from question text."""
    lower = (question or "").lower()
    if re.search(r"\b(most\s+affected|highest\s+exposure|worst\s+hit|most\s+impacted)\b", lower):
        return True
    if re.search(r"\b(?:which|what)\s+funds?\b", lower) and re.search(r"\btop\s*\d+", lower):
        return True
    if re.search(r"\btop\s*\d+\s+funds\b", lower):
        return True
    return False


def extract_fund_phrase_from_question(question: str) -> tuple[str, str]:
    """Best-effort scheme name / ISIN from natural-language question (no LLM)."""
    q = (question or "").strip()
    if not q:
        return "", ""
    isin_m = _ISIN_IN_TEXT.search(q)
    isin = isin_m.group(1).upper() if isin_m else ""

    patterns = [
        r"(?:latest|current)\s+(?:nav|net asset value)\s+(?:of|for)\s+(.+?)(?:\?|$)",
        r"(?:nav|net asset value)\s+(?:of|for)\s+(.+?)(?:\?|$)",
        r"(?:show|get|tell me|what is|what's)\s+(?:the\s+)?(?:latest|current)?\s*nav\s+(?:of|for)\s+(.+?)(?:\?|$)",
        r"(?:top\s+\d+\s+)?holdings?\s+(?:in|of|for)\s+(.+?)(?:\?|$)",
        r"(?:top\s+\d+\s+)?sectors?\s+(?:in|of|for)\s+(.+?)(?:\?|$)",
        r"sector\s+(?:allocation|breakdown|exposure)\s+(?:of|for|in)\s+(.+?)(?:\?|$)",
        r"\bimpact\s+of\s+.+?\s+on\s+(.+?)(?:\?|$)",
        r"\baffect(?:ing)?\s+(?:the\s+)?(.+?)(?:\?|$)",
        r"\bon\s+(.+?fund)\b",
        r"\bfor\s+(.+?fund)\b",
        r"\b(?:in|of)\s+(.+?fund)\b",
        r"\bfor\s+(.+?)(?:\?|$)",
    ]
    fund_name = ""
    for pat in patterns:
        m = re.search(pat, q, re.I)
        if m:
            fund_name = _clean_fund_phrase(m.group(1))
            if len(fund_name) >= 3:
                break
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
            if any(
                tok in norm
                for tok in (
                    "cap",
                    "flexi",
                    "large",
                    "mid",
                    "small",
                    "elss",
                    "index",
                    "ppfas",
                    "parag",
                    "hdfc",
                    "icici",
                    "sbi",
                    "axis",
                    "kotak",
                    "nippon",
                    "mirae",
                    "uti",
                )
            ):
                fund_name = candidate
    return isin, fund_name


def resolve_fund_for_query(
    question: str,
    *,
    isin: str = "",
    name: str = "",
) -> tuple[dict[str, Any] | None, bool, list[str]]:
    """Resolve fund using router fields, then question text, then alias / scan."""
    discovery = is_market_fund_discovery_question(question)
    attempts: list[tuple[str, str]] = []
    if (isin or "").strip() or (name or "").strip():
        attempts.append(((isin or "").strip(), (name or "").strip()))
    if not discovery:
        ext_isin, ext_name = extract_fund_phrase_from_question(question)
        if ext_isin or ext_name:
            attempts.append((ext_isin, ext_name))

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
                    for line in text.splitlines():
                        line = line.strip()
                        if line.startswith("## "):
                            current_amc = line.replace("## ", "").strip()
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
                    logger.info("Loaded %d Regular Growth funds into search index from %s", len(entries), md_path.name)
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

            self._entries = entries
            self._entries_by_isin = entries_by_isin
            self._loaded = True

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
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url)
                if resp.status_code != 200:
                    logger.warning("RupeeStop fund API returned status %d for ISIN %s", resp.status_code, isin_clean)
                    return None
                payload = resp.json()
        except Exception as exc:
            logger.warning("Failed to fetch fund detail from RupeeStop API for %s: %s", isin_clean, exc)
            return None

        raw = payload.get("data") or {}
        if not raw or not isinstance(raw, dict):
            return None

        ident = raw.get("identity") or {}
        facts = raw.get("fund_facts") or {}
        nav = raw.get("nav") or {}
        ret = raw.get("returns") or {}
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

        fund_name = ident.get("fund_name") or entry_meta.get("fund_name") or isin_clean
        fund_short_name = ident.get("fund_short_name") or ident.get("fund_name") or entry_meta.get("fund_short_name") or isin_clean

        cat = ident.get("category") or ident.get("sebi_category") or ident.get("sub_category") or entry_meta.get("category") or ""
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
            "sectors": sectors,
            "holdings": holdings,
        }

        with self._lock:
            self._detail_cache[isin_clean] = detail

        return detail

    def get_fund_detail(self, isin: str) -> dict[str, Any] | None:
        """Get full details (sectors, holdings, info) for an ISIN with caching."""
        self._ensure_loaded()
        raw_isin = isin.strip().upper()
        isin_clean = resolve_canonical_isin(raw_isin)

        # Check cache
        with self._lock:
            if isin_clean in self._detail_cache:
                cached = self._detail_cache[isin_clean]
                if raw_isin != isin_clean and cached:
                    return {**cached, "isin": isin_clean, "legacy_isin": raw_isin}
                return cached
            if raw_isin in self._detail_cache:
                return self._detail_cache[raw_isin]

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
            with self._lock:
                self._detail_cache[isin_clean] = fallback
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

        alias_isin = _scheme_alias_isin(clean_name)
        if alias_isin:
            detail = self.get_fund_detail(alias_isin)
            if detail:
                return detail, False, []

        # 2. Search on extracted name only
        norm_name = _normalize_fund_text(clean_name)
        stop_words = {
            "fund", "funds", "mutual", "scheme", "plan", "growth", "regular",
            "the", "and", "of", "in", "for", "to", "a", "an", "is", "about"
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

        scored_candidates: list[tuple[float, dict[str, Any]]] = []
        for entry in pool:
            c_name = entry.get("fund_short_name") or ""
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

            if "us" in c_tokens and "us" not in q_tokens and "international" not in norm_name:
                score -= 40.0
            if "global" in c_norm and not any(
                x in norm_name for x in ("global", "international", "us", "world", "overseas")
            ):
                score -= 25.0

            if amc_hints and not _entry_matches_amc(entry, amc_hints):
                continue

            if coverage >= 0.45 or (norm_name in c_norm):
                scored_candidates.append((score, entry))

        if not scored_candidates:
            candidates = self.search(norm_name, limit=20)
            for c in candidates:
                entry = self._entries_by_isin.get(str(c.get("isin") or "").upper())
                if not entry or (amc_hints and not _entry_matches_amc(entry, amc_hints)):
                    continue
                scored_candidates.append((80.0, entry))

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


def lookup_extracted_fund(
    isin: str = "",
    name: str = "",
) -> tuple[dict[str, Any] | None, bool, list[str]]:
    """Convenience helper to lookup fund from global fund index."""
    return get_fund_index().lookup_extracted_fund(isin=isin, name=name)


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


_fund_index: FundIndex | None = None


def get_fund_index() -> FundIndex:
    global _fund_index
    if _fund_index is None:
        _fund_index = FundIndex()
    return _fund_index
