"""Smart Fund Universe Agent & Query Engine for regular-growth-by-amc catalog (2,194 funds across 67 AMCs)."""

from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from news_rag.config import get_settings
from historical_data.nav_service import get_fund_nav_history
from news_rag.json_util import safe_json_dumps
from news_rag.llm_client import call_insight_llm, llm_api_key_configured
from news_rag.llm_text import parse_json_from_text
from news_rag.query_log import QueryLogger

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Comprehensive category patterns for Indian Mutual Funds
_CATEGORY_PATTERNS: list[tuple[str, str, str, list[str]]] = [
    # (Category Name, Scheme Type, Sub-type, Regex Keywords)
    ("Large Cap", "Equity", "Large Cap", [r"\blarge\s*cap\b", r"\bblue\s*chip\b", r"\btop\s*100\b", r"\bnifty\s*50\b"]),
    ("Mid Cap", "Equity", "Mid Cap", [r"\bmid\s*cap\b", r"\bemerging\s*equit(?:y|ies)\b", r"\bnifty\s*midcap\b"]),
    ("Small Cap", "Equity", "Small Cap", [r"\bsmall\s*cap\b", r"\bmicro\s*cap\b", r"\bnifty\s*smallcap\b"]),
    ("Large & Mid Cap", "Equity", "Large & Mid Cap", [r"\blarge\s*(?:and|&)\s*mid\s*cap\b", r"\btop\s*200\b"]),
    ("Flexi Cap", "Equity", "Flexi Cap", [r"\bflexi\s*cap\b", r"\bflexicap\b"]),
    ("Multi Cap", "Equity", "Multi Cap", [r"\bmulti\s*cap\b", r"\bmulticap\b"]),
    ("ELSS / Tax Saver", "Equity", "ELSS", [r"\belss\b", r"\btax\s*saver\b", r"\btax\s*saving\b", r"\blong\s*term\s*equity\b"]),
    ("Focused", "Equity", "Focused", [r"\bfocused\b", r"\bfocus\s*25\b", r"\bfocus\s*30\b"]),
    ("Value / Contra", "Equity", "Value / Contra", [r"\bvalue\s*fund\b", r"\bcontra\b", r"\bvalue\s*discovery\b"]),
    ("Dividend Yield", "Equity", "Dividend Yield", [r"\bdividend\s*yield\b"]),
    
    # Sectoral / Thematic Equity
    ("Banking & Financial Services", "Equity", "Sectoral - Banking", [r"\bbank(?:ing)?\b", r"\bfinancial\s*services\b", r"\bpsu\s*bank\b"]),
    ("Information Technology", "Equity", "Sectoral - IT", [r"\b(?:it|technology|tech|digital\s*india|software)\b"]),
    ("Healthcare & Pharma", "Equity", "Sectoral - Healthcare", [r"\bpharma(?:ceutical)?\b", r"\bhealth\s*care\b", r"\bhealthcare\b"]),
    ("Automobile & Auto Ancillary", "Equity", "Sectoral - Auto", [r"\bauto(?:mobile)?\b", r"\btransportation\b", r"\bauto\s*ancillar(?:y|ies)\b"]),
    ("Infrastructure & Construction", "Equity", "Sectoral - Infrastructure", [r"\binfra(?:structure)?\b", r"\bconstruction\b"]),
    ("Energy & Power", "Equity", "Sectoral - Energy", [r"\benergy\b", r"\bpower\b", r"\bpetroleum\b", r"\boil\b"]),
    ("Defense & Aerospace", "Equity", "Thematic - Defense", [r"\bdefen[cs]e\b", r"\baerospace\b"]),
    ("Manufacturing & Industrial", "Equity", "Thematic - Manufacturing", [r"\bmanufacturing\b", r"\bindustrial\b", r"\bcapital\s*goods\b"]),
    ("Consumption & FMCG", "Equity", "Thematic - Consumption", [r"\bconsumption\b", r"\bfmcg\b", r"\bconsumer\b"]),
    ("ESG / Sustainability", "Equity", "Thematic - ESG", [r"\besg\b", r"\bsustainab(?:ility|le)\b", r"\bclean\s*energy\b"]),
    ("MNC / International", "Equity", "Thematic - Global", [r"\bmnc\b", r"\binternational\b", r"\bglobal\b", r"\bus\s*equity\b", r"\bworld\b"]),
    ("Special Situations / Quant", "Equity", "Thematic - Special Situations", [r"\bspecial\s*situations\b", r"\bquant\b", r"\bbusiness\s*cycle\b", r"\bmomentum\b", r"\bquality\b"]),

    # Hybrid Categories
    ("Arbitrage", "Hybrid", "Arbitrage", [r"\barbitrage\b"]),
    ("Balanced Advantage / Dynamic Asset", "Hybrid", "Balanced Advantage", [r"\bbalanced\s*advantage\b", r"\bdynamic\s*asset\b", r"\bdynamic\s*equity\b"]),
    ("Aggressive Hybrid", "Hybrid", "Aggressive Hybrid", [r"\baggressive\s*hybrid\b", r"\bequity\s*hybrid\b"]),
    ("Conservative Hybrid", "Hybrid", "Conservative Hybrid", [r"\bconservative\s*hybrid\b", r"\bregular\s*savings\b"]),
    ("Multi Asset Allocation", "Hybrid", "Multi Asset", [r"\bmulti\s*asset\b"]),
    ("Equity Savings", "Hybrid", "Equity Savings", [r"\bequity\s*savings\b"]),

    # Commodities / Bullion
    ("Gold ETF / Fund", "Commodity", "Gold", [r"\bgold\s*(?:etf|fund|fo[f|s])\b"]),
    ("Silver ETF / Fund", "Commodity", "Silver", [r"\bsilver\s*(?:etf|fund|fo[f|s])\b"]),

    # Passive / Index
    ("Index Fund / ETF", "Index / Passive", "Index / ETF", [r"\bindex\s*fund\b", r"\betf\b", r"\bnifty\b", r"\bsensex\b", r"\bbse\b"]),

    # Debt Categories
    ("Liquid", "Debt", "Liquid", [r"\bliquid\b"]),
    ("Overnight", "Debt", "Overnight", [r"\bovernight\b"]),
    ("Ultra Short / Money Market", "Debt", "Ultra Short", [r"\bultra\s*short\b", r"\bmoney\s*market\b", r"\blow\s*duration\b"]),
    ("Short Duration / Corporate Bond", "Debt", "Short Duration", [r"\bshort\s*duration\b", r"\bcorporate\s*bond\b", r"\bbanking\s*(&|and)\s*psu\s*debt\b"]),
    ("Gilt / Government Securities", "Debt", "Gilt", [r"\bgilt\b", r"\b10\s*year\s*gilt\b", r"\bg-sec\b", r"\bgilt\s*etf\b"]),
]


@dataclass
class FundEntry:
    isin: str
    fund_name: str
    amc: str
    amc_short: str
    category: str
    sub_category: str
    scheme_type: str
    plan: str = "Regular"
    option: str = "Growth"


class FundUniverseCatalog:
    """In-memory index of regular-growth-by-amc universe."""

    def __init__(self) -> None:
        self._loaded: bool = False
        self._funds: list[FundEntry] = []
        self._by_isin: dict[str, FundEntry] = {}
        self._amc_list: list[str] = []
        self._lock = threading.Lock()

    def _find_md_file(self) -> Path:
        candidates = [
            _REPO_ROOT / "data/fund_holdings_aggregate/regular-growth-by-amc.md",
            _REPO_ROOT / "data/regular-growth-by-amc.md",
        ]
        for p in candidates:
            if p.is_file():
                return p
        return candidates[0]

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            path = self._find_md_file()
            funds: list[FundEntry] = []
            by_isin: dict[str, FundEntry] = {}
            amcs_set: set[str] = set()

            if path.is_file():
                text = path.read_text(encoding="utf-8")
                current_amc = ""
                for line in text.splitlines():
                    line = line.strip()
                    if line.startswith("## "):
                        current_amc = line.replace("## ", "").strip()
                        amcs_set.add(current_amc)
                    elif line.startswith("- ") and "—" in line:
                        parts = line[2:].split("—")
                        if len(parts) >= 2:
                            fname = parts[0].strip()
                            isin = parts[1].replace("`", "").strip().upper()
                            cat, subcat, stype = self._classify_fund(fname)
                            amc_short = self._short_amc_name(current_amc)
                            entry = FundEntry(
                                isin=isin,
                                fund_name=fname,
                                amc=current_amc,
                                amc_short=amc_short,
                                category=cat,
                                sub_category=subcat,
                                scheme_type=stype,
                            )
                            funds.append(entry)
                            by_isin[isin] = entry

            self._funds = funds
            self._by_isin = by_isin
            self._amc_list = sorted(amcs_set)
            self._loaded = True
            logger.info("FundUniverseCatalog loaded %d funds across %d AMCs", len(funds), len(self._amc_list))

    def _short_amc_name(self, amc: str) -> str:
        s = re.sub(r"\s*(?:Mutual\s+Fund|Asset\s+Management|SIF|AMC|Investment\s+Managers).*$", "", amc, flags=re.I).strip()
        return s or amc

    def _classify_fund(self, name: str) -> tuple[str, str, str]:
        low = name.lower()
        for cat, stype, subcat, patterns in _CATEGORY_PATTERNS:
            for pat in patterns:
                if re.search(pat, low):
                    return cat, subcat, stype
        return "Other Equity", "Diversified Equity", "Equity"

    @property
    def total_funds(self) -> int:
        self.ensure_loaded()
        return len(self._funds)

    @property
    def amcs(self) -> list[str]:
        self.ensure_loaded()
        return list(self._amc_list)

    def query(
        self,
        *,
        category: str | None = None,
        amc: str | None = None,
        scheme_type: str | None = None,
        keyword: str | None = None,
        limit: int = 5,
        enrich_nav: bool = True,
    ) -> list[dict[str, Any]]:
        """Query the fund universe with multiple flexible filters."""
        self.ensure_loaded()
        matches: list[FundEntry] = []

        cat_clean = (category or "").strip().lower()
        amc_clean = (amc or "").strip().lower()
        stype_clean = (scheme_type or "").strip().lower()
        kw_clean = (keyword or "").strip().lower()

        for entry in self._funds:
            if cat_clean:
                # Match against category or sub-category or fund name
                if (
                    cat_clean not in entry.category.lower()
                    and cat_clean not in entry.sub_category.lower()
                    and cat_clean not in entry.fund_name.lower()
                ):
                    continue
            if amc_clean:
                if amc_clean not in entry.amc.lower() and amc_clean not in entry.amc_short.lower():
                    continue
            if stype_clean:
                if stype_clean not in entry.scheme_type.lower():
                    continue
            if kw_clean:
                if kw_clean not in entry.fund_name.lower() and kw_clean not in entry.isin.lower():
                    continue
            matches.append(entry)

        # Diverse representation: if no AMC specified, try to pick from distinct top AMCs
        if not amc_clean and len(matches) > limit:
            picked: list[FundEntry] = []
            seen_amcs: set[str] = set()
            for m in matches:
                if m.amc not in seen_amcs:
                    picked.append(m)
                    seen_amcs.add(m.amc)
                if len(picked) >= limit:
                    break
            if len(picked) < limit:
                for m in matches:
                    if m not in picked:
                        picked.append(m)
                    if len(picked) >= limit:
                        break
            matches = picked
        else:
            matches = matches[:limit]

        results: list[dict[str, Any]] = []
        from concurrent.futures import ThreadPoolExecutor

        def _enrich(entry: FundEntry) -> dict[str, Any]:
            res: dict[str, Any] = {
                "isin": entry.isin,
                "fund_name": entry.fund_name,
                "amc": entry.amc,
                "amc_short": entry.amc_short,
                "category": entry.category,
                "sub_category": entry.sub_category,
                "scheme_type": entry.scheme_type,
                "plan": entry.plan,
                "option": entry.option,
            }
            if enrich_nav:
                try:
                    nav_data = get_fund_nav_history(entry.isin)
                    if nav_data.get("success"):
                        res["latest_nav"] = nav_data.get("latest_nav")
                        res["latest_date"] = nav_data.get("latest_date")
                        stats = nav_data.get("stats") or {}
                        w1 = stats.get("1W")
                        m1 = stats.get("1M")
                        if w1 and "change_pct" in w1:
                            res["return_1w_pct"] = w1["change_pct"]
                        if m1 and "change_pct" in m1:
                            res["return_1m_pct"] = m1["change_pct"]
                except Exception:
                    pass
            return res

        if matches and enrich_nav:
            with ThreadPoolExecutor(max_workers=min(8, len(matches))) as pool:
                results = list(pool.map(_enrich, matches))
        else:
            results = [_enrich(m) for m in matches]

        return results


_CATALOG_INSTANCE: FundUniverseCatalog | None = None
_CATALOG_LOCK = threading.Lock()


def get_fund_universe_catalog() -> FundUniverseCatalog:
    global _CATALOG_INSTANCE
    with _CATALOG_LOCK:
        if _CATALOG_INSTANCE is None:
            _CATALOG_INSTANCE = FundUniverseCatalog()
            _CATALOG_INSTANCE.ensure_loaded()
        return _CATALOG_INSTANCE


class FundUniverseAgent:
    """Agent that processes natural language queries over the 2,194 fund catalog."""

    def __init__(self) -> None:
        self.catalog = get_fund_universe_catalog()

    def parse_and_execute(self, query: str, *, query_log: QueryLogger | None = None) -> dict[str, Any]:
        """Classifies intent and fetches matched funds with live NAV metrics."""
        q = (query or "").strip()
        limit = self._extract_limit(q, default=3)
        amc = self._extract_amc(q)
        cat = self._extract_category(q)
        keyword = self._extract_keyword(q, amc, cat)

        funds = self.catalog.query(
            category=cat,
            amc=amc,
            keyword=keyword,
            limit=limit,
            enrich_nav=True,
        )

        return {
            "query": q,
            "detected_category": cat,
            "detected_amc": amc,
            "detected_limit": limit,
            "total_found": len(funds),
            "funds": funds,
        }

    def answer_question(self, question: str, *, query_log: QueryLogger | None = None) -> str:
        """End-to-end question answering returning formatted markdown response."""
        data = self.parse_and_execute(question, query_log=query_log)
        funds = data.get("funds") or []
        if not funds:
            return (
                f"We searched our universe of **{self.catalog.total_funds} Regular Growth mutual funds** "
                f"across **{len(self.catalog.amcs)} AMCs** but could not find matching schemes for: *\"{question}\"*."
            )

        cat = data.get("detected_category") or "Mutual Funds"
        amc = data.get("detected_amc") or ""
        scope_str = f"{amc} {cat}".strip()

        lines = [
            f"💡 **Mutual Fund Selection**",
            f"Here are top **{len(funds)} {scope_str}** schemes from our verified Regular Growth universe:\n",
        ]

        for idx, f in enumerate(funds, start=1):
            fname = f.get("fund_name")
            isin = f.get("isin")
            amc_name = f.get("amc_short") or f.get("amc")
            category = f.get("category")
            nav = f.get("latest_nav")
            ret_1m = f.get("return_1m_pct")
            ret_1w = f.get("return_1w_pct")

            nav_bits = []
            if nav is not None:
                nav_bits.append(f"NAV: **₹{nav:,.2f}**")
            if ret_1m is not None:
                s = "+" if ret_1m > 0 else ""
                nav_bits.append(f"1M: **{s}{ret_1m}%**")
            if ret_1w is not None:
                s = "+" if ret_1w > 0 else ""
                nav_bits.append(f"1W: **{s}{ret_1w}%**")

            metrics_str = f" ({', '.join(nav_bits)})" if nav_bits else ""
            lines.append(
                f"{idx}. **{fname}** — `{isin}`\n"
                f"   • **AMC**: {amc_name} | **Category**: {category}{metrics_str}"
            )

        return "\n".join(lines)

    def _extract_limit(self, q: str, default: int = 3) -> int:
        m = re.search(r"\b(\d{1,2})\s+(?:funds?|schemes?|options?|etfs?)\b", q, re.I)
        if m:
            try:
                return max(1, min(int(m.group(1)), 15))
            except ValueError:
                pass
        word_map = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "ten": 10}
        for w, val in word_map.items():
            if re.search(rf"\b{w}\s+(?:mutual\s+)?(?:funds?|schemes?|options?)\b", q, re.I):
                return val
        return default

    def _extract_amc(self, q: str) -> str | None:
        amc_map = {
            "hdfc": "HDFC",
            "icici": "ICICI Prudential",
            "sbi": "SBI",
            "axis": "Axis",
            "kotak": "Kotak",
            "nippon": "Nippon",
            "mirae": "Mirae",
            "parag parikh": "PPFAS",
            "ppfas": "PPFAS",
            "quant": "Quant",
            "tata": "Tata",
            "dsp": "DSP",
            "motilal": "Motilal Oswal",
            "uti": "UTI",
            "canara": "Canara Robeco",
            "edelweiss": "Edelweiss",
            "bandhan": "Bandhan",
            "franklin": "Franklin",
            "invesco": "Invesco",
            "whiteoak": "WhiteOak",
            "groww": "Groww",
            "zerodha": "Zerodha",
            "sundaram": "Sundaram",
            "baroda": "Baroda BNP",
            "hsbc": "HSBC",
            "union": "Union",
            "mahindra": "Mahindra Manulife",
            "360 one": "360 ONE",
        }
        low = q.lower()
        for k, v in amc_map.items():
            if re.search(rf"\b{k}\b", low):
                return v
        return None

    def _extract_category(self, q: str) -> str | None:
        low = q.lower()
        for cat, _stype, _subcat, patterns in _CATEGORY_PATTERNS:
            for pat in patterns:
                if re.search(pat, low):
                    return cat
        return None

    def _extract_keyword(self, q: str, amc: str | None, cat: str | None) -> str | None:
        low = q.lower()
        # Look for specific themes
        for kw in ["momentum", "quality", "low volatility", "alpha", "gold", "silver", "defence", "defense", "psu", "infra", "mfg", "technology", "pharma"]:
            if re.search(rf"\b{kw}\b", low):
                return kw
        return None
