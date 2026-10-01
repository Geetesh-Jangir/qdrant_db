"""Fast search and autocomplete recommendations across mutual funds."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from news_rag.config import get_settings

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _extract_plan_option(isin: str, name: str, direct_growth_isins: set[str]) -> tuple[str, str]:
    name_lower = name.lower()
    
    # 1. Determine Plan
    if "direct" in name_lower or isin in direct_growth_isins:
        plan = "Direct"
    elif "regular" in name_lower:
        plan = "Regular"
    else:
        plan = "Regular"

    # 2. Determine Option
    if "reinvestment" in name_lower or "reinvest" in name_lower:
        option = "IDCW Reinvestment"
    elif "payout" in name_lower:
        option = "IDCW Payout"
    elif "idcw" in name_lower:
        option = "IDCW"
    elif "dividend" in name_lower:
        option = "Dividend"
    elif "bonus" in name_lower:
        option = "Bonus"
    elif "monthly" in name_lower:
        option = "Monthly"
    elif "quarterly" in name_lower:
        option = "Quarterly"
    elif "weekly" in name_lower:
        option = "Weekly"
    elif "fortnightly" in name_lower:
        option = "Fortnightly"
    elif "annually" in name_lower or "annual" in name_lower:
        option = "Annual"
    elif "daily" in name_lower:
        option = "Daily"
    elif "growth" in name_lower or isin in direct_growth_isins:
        option = "Growth"
    else:
        option = "Growth"

    return plan, option


def _normalize_fund_text(text: str) -> str:
    """Normalizes compound market and fund terms into standard separated tokens."""
    t = (text or "").lower()
    t = re.sub(r"\blargecap\b", "large cap", t)
    t = re.sub(r"\bmidcap\b", "mid cap", t)
    t = re.sub(r"\bsmallcap\b", "small cap", t)
    t = re.sub(r"\bflexicap\b", "flexi cap", t)
    t = re.sub(r"\bmulticap\b", "multi cap", t)
    t = re.sub(r"\bmicrocap\b", "micro cap", t)
    t = re.sub(r"\bbluechip\b", "blue chip", t)
    t = re.sub(r"\b&\b", " and ", t)
    t = re.sub(r"\bppfas\b", "parag parikh ppfas", t)
    return t


class FundIndex:
    def __init__(self) -> None:
        self._loaded: bool = False
        self._entries: list[dict[str, Any]] = []
        self._data_path: Path | None = None
        self._full_map: dict[str, dict[str, Any]] | None = None
        self._direct_growth_isins: set[str] = set()

    def _find_data_file(self) -> Path | None:
        settings = get_settings()
        candidates = [
            _REPO_ROOT / settings.allisin_sectors_holdings_json,
            _REPO_ROOT / "data/fund_holdings_aggregate/allisin_sectors_with_holdings.json",
            _REPO_ROOT / "data/fund_holdings_aggregate/fund_sectors_and_holdings_aggregate.json",
        ]
        for path in candidates:
            if path.is_file():
                return path
        return None

    def _load_direct_growth_isins(self) -> set[str]:
        direct_file = _REPO_ROOT / "data" / "direct_plan_growth_isins.txt"
        if direct_file.is_file():
            try:
                return set(direct_file.read_text(encoding="utf-8").splitlines())
            except Exception:
                pass
        return set()

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        data_path = self._find_data_file()
        if not data_path or not data_path.is_file():
            logger.warning("No fund aggregate JSON file found for search index")
            self._loaded = True
            return

        self._data_path = data_path
        self._direct_growth_isins = self._load_direct_growth_isins()

        try:
            with open(data_path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            entries: list[dict[str, Any]] = []
            full_map: dict[str, dict[str, Any]] = {}

            if isinstance(raw, dict):
                for isin, val in raw.items():
                    if isin.startswith("_") or not isinstance(val, dict):
                        continue
                    name = str(val.get("fund_short_name") or val.get("fund_name") or isin).strip()
                    category = str(val.get("category") or "").strip()
                    scheme_type = str(val.get("scheme_type") or "").strip()
                    as_on = str(val.get("as_on") or "").strip()
                    
                    plan, option = _extract_plan_option(isin, name, self._direct_growth_isins)

                    # Strict filter for conversational search: Regular Plan + Growth Option
                    if plan == "Regular" and option == "Growth":
                        entry = {
                            "isin": isin,
                            "fund_short_name": name,
                            "plan": plan,
                            "option": option,
                            "category": category,
                            "scheme_type": scheme_type,
                            "as_on": as_on,
                            "name_lower": name.lower(),
                            "name_norm": _normalize_fund_text(name),
                            "isin_lower": isin.lower(),
                        }
                        entries.append(entry)
                    
                    # Augment full map with plan and option
                    val_copy = dict(val)
                    val_copy["plan"] = plan
                    val_copy["option"] = option
                    full_map[isin] = val_copy

            self._entries = entries
            self._full_map = full_map
            self._loaded = True
            logger.info("Loaded %d Regular Growth funds into search index from %s", len(self._entries), data_path.name)
        except Exception as exc:
            logger.exception("Failed to load fund index from %s: %s", data_path, exc)
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
                    "as_on": e["as_on"],
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
                            "plan": e.get("plan", "Regular"),
                            "option": e.get("option", "Growth"),
                            "category": e["category"],
                            "scheme_type": e["scheme_type"],
                            "as_on": e["as_on"],
                        }
                    )
                    if len(results) >= limit:
                        return results

        return results

    def get_fund_detail(self, isin: str) -> dict[str, Any] | None:
        """Get full details (sectors, holdings, info) for an ISIN."""
        self._ensure_loaded()
        isin_clean = isin.strip().upper()
        if not self._full_map or isin_clean not in self._full_map:
            for k, val in (self._full_map or {}).items():
                if k.upper() == isin_clean:
                    return {"isin": k, **val}
            return None

        val = self._full_map[isin_clean]
        return {"isin": isin_clean, **val}

    def resolve_fund_from_text(self, text: str) -> dict[str, Any] | None:
        """Intelligently resolves a Regular Growth mutual fund from natural language text or ISIN."""
        self._ensure_loaded()
        if not text:
            return None

        clean_text = text.strip()
        lower_text = clean_text.lower()

        # 1. Direct ISIN match (INF...)
        isin_match = re.search(r"\b(INF[A-Z0-9]{9})\b", clean_text, re.IGNORECASE)
        if isin_match:
            isin_str = isin_match.group(1).upper()
            detail = self.get_fund_detail(isin_str)
            if detail:
                return detail

        norm_text = _normalize_fund_text(clean_text)

        # 2. Check curated conversational aliases
        for alias, isin in FUND_ALIASES.items():
            norm_alias = _normalize_fund_text(alias)
            if re.search(rf"\b{re.escape(norm_alias)}\b", norm_text) or re.search(rf"\b{re.escape(alias)}\b", lower_text):
                detail = self.get_fund_detail(isin)
                if detail:
                    return detail

        # 3. Token-set scoring against all Regular Growth fund entries
        stop_words = {
            "what", "where", "which", "when", "how", "much", "many", "does", "will", "this", "that",
            "fund", "funds", "mutual", "holding", "holdings", "sector", "sectors", "growth", "regular",
            "plan", "option", "impact", "affect", "news", "today", "return", "returns", "latest",
            "price", "prices", "trend", "trends", "current", "tell", "show", "give", "about", "with",
            "have", "from", "over", "last", "days", "week", "month", "year", "time", "rate", "rates",
            "happening", "recently", "doing", "performance"
        }
        q_tokens = [w for w in re.findall(r"\b[a-z0-9]+\b", norm_text) if len(w) >= 3 and w not in stop_words]
        q_set = set(q_tokens)

        if len(q_set) >= 2:
            best_entry = None
            best_score = -999

            distinguishing_categories = {
                "large", "mid", "small", "flexi", "multi", "micro", "focused", "contra", "value",
                "hybrid", "etf", "index", "overnight", "liquid", "debt", "psu", "pharma",
                "technology", "manufacturing", "consumption", "elss", "tax"
            }

            for e in self._entries:
                norm_e = e.get("name_norm") or _normalize_fund_text(e["name_lower"])
                e_tokens = [w for w in re.findall(r"\b[a-z0-9]+\b", norm_e) if len(w) >= 3 and w not in stop_words]
                e_set = set(e_tokens)

                matched = q_set & e_set
                if len(matched) < 2:
                    continue

                score = len(matched) * 10

                # Distinguishing category penalty if entry has a category word NOT requested in query
                for extra in (e_set - q_set):
                    if extra in distinguishing_categories:
                        score -= 15

                # Bonus if all query tokens are present in fund entry
                if q_tokens and all(t in e_set for t in q_tokens):
                    score += 20

                # Bonus for exact token set equality
                if len(q_set) == len(e_set) and q_set == e_set:
                    score += 30

                if score > best_score and score >= 10:
                    best_score = score
                    best_entry = e

            if best_entry:
                return self.get_fund_detail(best_entry["isin"])

        return None


FUND_ALIASES: dict[str, str] = {
    "parag parikh flexi cap": "INF879O01027",
    "parag parikh flexicap": "INF879O01027",
    "parag parikh": "INF879O01027",
    "ppfas flexi cap": "INF879O01027",
    "ppfas flexicap": "INF879O01027",
    "ppfas": "INF879O01027",
    "hdfc top 100": "INF179K01BE2",
    "sbi bluechip": "INF200K01164",
    "sbi blue chip": "INF200K01164",
    "invesco largecap": "INF205K01304",
    "invesco large cap": "INF205K01304",
    "invesco large and mid cap": "INF205K01247",
    "invesco large & mid cap": "INF205K01247",
    "nippon india growth": "INF204K01018",
    "nippon growth": "INF204K01018",
    "icici prudential bluechip": "INF109K014L5",
    "icici bluechip": "INF109K014L5",
    "mirae asset large cap": "INF769K01010",
    "mirae large cap": "INF769K01010",
    "kotak emerging equity": "INF174K01101",
    "axis bluechip": "INF846K01164",
    "quantum value": "INF082J01044",
    "quantum elss": "INF082J01085",
    "sbi small cap": "INF200K01T43",
    "hdfc mid cap opportunities": "INF179K01967",
    "motilal oswal midcap": "INF247L01168",
    "uti nifty 50 index": "INF789F01059",
    "dsp flexi cap": "INF740K01079",
}


def extract_top_holdings(detail: dict[str, Any] | None, limit: int = 10) -> list[dict[str, Any]]:
    """Robustly extracts and sorts top equity holdings from fund detail dictionary."""
    if not detail:
        return []
    raw = detail.get("holdings") or {}
    items: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for name, meta in raw.items():
            if isinstance(meta, dict):
                pct = float(meta.get("percentage") or 0.0)
                ind = meta.get("industry", "Equity")
            else:
                try:
                    pct = float(meta)
                except Exception:
                    pct = 0.0
                ind = "Equity"
            items.append({"name": str(name), "percentage": pct, "industry": ind})
    elif isinstance(raw, list):
        for h in raw:
            if isinstance(h, dict):
                name = h.get("instrument_name") or h.get("name") or ""
                pct = float(h.get("percentage") or 0.0)
                ind = h.get("industry", "Equity")
                items.append({"name": str(name), "percentage": pct, "industry": ind})
            elif isinstance(h, str):
                items.append({"name": h, "percentage": 0.0, "industry": "Equity"})
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
                name = s.get("sector_label") or s.get("sector") or ""
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


