"""Read-only sector → fund weight index for market-wide top-N fund ranking."""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Any, Literal

from lib.portfolio_scope import normalize_sector_label, sector_query_for_label
from news_rag.config import get_settings

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]

# User / news phrasing → sector keys in sector_to_isin_weights.json
_SECTOR_ALIASES: dict[str, tuple[str, ...]] = {
    # Information Technology
    "information technology": ("It - Software", "It - Services", "Software"),
    "it sector": ("It - Software", "It - Services"),
    "it": ("It - Software", "It - Services"),
    "technology": ("It - Software", "It - Services", "Technology Hardware & Equipment"),
    "tech": ("It - Software", "It - Services"),
    "software": ("It - Software", "Software"),

    # Banking & Financials
    "banking": ("Banks", "Finance"),
    "banking & financials": ("Banks", "Finance", "Financial Services"),
    "banking & financial services": ("Banks", "Finance", "Financial Services"),
    "financials": ("Banks", "Finance", "Financial Services"),
    "financial services": ("Banks", "Finance", "Financial Services", "Capital Markets"),
    "bank sector": ("Banks", "Finance"),
    "financial": ("Banks", "Finance", "Capital Markets"),
    "banks": ("Banks", "Finance"),
    "psu banks": ("Banks",),
    "public sector banks": ("Banks",),
    "private banks": ("Banks",),
    "rbi": ("Banks", "Finance"),
    "repo rate": ("Banks", "Finance"),
    "repo": ("Banks", "Finance"),
    "rate hike": ("Banks", "Finance"),
    "monetary policy": ("Banks", "Finance"),

    # Healthcare / Pharma
    "pharmaceuticals & healthcare": ("Pharmaceuticals & Biotechnology", "Healthcare Services", "Healthcare"),
    "pharmaceuticals": ("Pharmaceuticals & Biotechnology", "Healthcare"),
    "pharma": ("Pharmaceuticals & Biotechnology", "Healthcare Services", "Healthcare"),
    "healthcare": ("Healthcare Services", "Pharmaceuticals & Biotechnology", "Healthcare"),
    "health care": ("Healthcare Services", "Pharmaceuticals & Biotechnology"),

    # Auto / Automotive
    "automotive": ("Automobiles", "Auto Components", "Auto Ancillaries"),
    "automotive sector": ("Automobiles", "Auto Components"),
    "auto sector": ("Automobiles", "Auto Components"),
    "automobile": ("Automobiles", "Auto Components"),
    "automobiles": ("Automobiles", "Auto Components"),

    # Capital Goods / Industrial
    "capital goods": ("Capital Goods", "Industrial Manufacturing", "Industrial Products"),
    "capital goods & industrial solutions": ("Capital Goods", "Industrial Manufacturing", "Industrial Products"),
    "industrial": ("Industrial Manufacturing", "Industrial Products", "Capital Goods"),
    "industrials": ("Industrial Manufacturing", "Industrial Products", "Capital Goods"),
    "infrastructure": ("Construction", "Power", "Industrial Products"),

    # Energy / Oil / Metals
    "oil": ("Petroleum Products", "Energy"),
    "crude": ("Petroleum Products", "Energy"),
    "barrel": ("Petroleum Products", "Energy"),
    "brent": ("Petroleum Products", "Energy"),
    "energy": ("Power", "Petroleum Products", "Energy"),
    "power": ("Power", "Energy"),
    "real estate": ("Realty", "Real Estate"),
    "realty": ("Realty", "Real Estate"),
    "metal": ("Ferrous Metals", "Non - Ferrous Metals", "Metals & Mining"),
    "metals": ("Ferrous Metals", "Non - Ferrous Metals", "Metals & Mining"),
}

# Do not infer these sector keys from random news entity tags (e.g. Insurance ETF headlines).
_ARTICLE_INFER_BLOCKLIST = frozenset(
    {
        "insurance",
        "gold",
        "silver",
        "mutual fund",
        "internal - mutual fund units",
    }
)

_PASSIVE_NAME_RE = re.compile(
    r"\b(etf|exchange\s+traded|index\s+fund|nifty|bse\s|sensex|tri\b|psu\s+bank\s+index|"
    r"target\s+maturity|fund\s+of\s+fund|fof\b)",
    re.I,
)

_NON_PURE_SECTOR_VEHICLE_RE = re.compile(
    r"\b(arbitrage|equity\s+savings|balanced\s+advantage|dynamic\s+asset|multi[-\s]asset|"
    r"balanced\s+hybrid|conservative\s+hybrid|aggressive\s+hybrid|hybrid\b|"
    r"income\s+plus\s+arbitrage)\b",
    re.I,
)

_DEDICATED_SECTORAL_RE = re.compile(
    r"(banking\s*(?:&|and)\s*financial|financial\s+services\s+fund|technology\s+fund|"
    r"pharma(?:ceutical)?|health\s*care\s+fund|infrastructure\s+fund|consumption\s+fund|"
    r"defen[cs]e\s+fund|energy\s+fund|power\s*(?:&|and)\s*infra|psu\s+equity|"
    r"manufacturing\s+fund|auto\s+fund|fmcg|metal\s+fund|precious\s+metals|"
    r"realty|real\s+estate|sectoral|thematic|special\s+situations|"
    r"export|services\s+fund|digital\s+india|mnc\s+fund|media\s+and\s+entertainment)",
    re.I,
)

_PURITY_BUCKET_ORDER = {
    "dedicated_sectoral": 0,
    "diversified_equity": 1,
    "passive": 2,
    "defensive_neutral": 3,
    "debt": 4,
}

_regular_growth_isins: set[str] | None = None
_regular_growth_lock = threading.Lock()


def _repo_path(relative: str) -> Path:
    p = Path(relative)
    return p if p.is_absolute() else _REPO_ROOT / relative


def load_regular_growth_isins() -> set[str]:
    global _regular_growth_isins
    with _regular_growth_lock:
        if _regular_growth_isins is not None:
            return _regular_growth_isins
        settings = get_settings()
        md_path = _repo_path(settings.funds_by_amc_md)
        isins: set[str] = set()
        if md_path.is_file():
            for m in re.finditer(r"`(INF[A-Z0-9]{9})`", md_path.read_text(encoding="utf-8")):
                isins.add(m.group(1).upper())
        _regular_growth_isins = isins
        return isins


class SectorFundRankingIndex:
    def __init__(self, doc: dict[str, Any]) -> None:
        self.meta = doc.get("_meta") or {}
        raw_sectors = doc.get("sectors") or {}
        self._sectors: dict[str, dict[str, Any]] = {}
        self._sector_fold: dict[str, str] = {}
        for name, block in raw_sectors.items():
            if not isinstance(block, dict):
                continue
            key = str(name).strip()
            if not key:
                continue
            self._sectors[key] = block
            self._sector_fold[key.casefold()] = key

    @property
    def sector_names(self) -> list[str]:
        return sorted(self._sectors.keys())

    def has_sector(self, key: str) -> bool:
        return key in self._sectors

    def resolve_sector_keys(self, labels: list[str]) -> list[str]:
        """Map free-text sector labels to canonical keys present in the index."""
        found: list[str] = []
        seen: set[str] = set()

        def add(key: str) -> None:
            if key in self._sectors and key not in seen:
                seen.add(key)
                found.append(key)

        for raw in labels:
            text = (raw or "").strip()
            if not text:
                continue
            norm = normalize_sector_label(text)
            if norm in self._sectors:
                add(norm)
                continue
            fold = norm.casefold()
            if fold in self._sector_fold:
                add(self._sector_fold[fold])
                continue
            mapped = sector_query_for_label(norm)
            if mapped:
                canon = mapped[0]
                if canon in self._sectors:
                    add(canon)
                    continue
                if canon.casefold() in self._sector_fold:
                    add(self._sector_fold[canon.casefold()])
                    continue
            lower = text.lower()
            for alias, keys in _SECTOR_ALIASES.items():
                if alias in lower:
                    for k in keys:
                        add(k)
            # substring match on index keys (last resort)
            for sk in self._sectors:
                if _sector_label_in_text(sk, lower):
                    add(sk)

        return found

    def resolve_from_question(self, question: str, event_focus: str = "") -> list[str]:
        blob = f"{question} {event_focus}".strip()
        lower = blob.lower()
        keys: list[str] = []
        for alias, sector_keys in _SECTOR_ALIASES.items():
            if alias in lower:
                keys.extend(sector_keys)
        # explicit sector names from index appearing in text
        for sk in self._sectors:
            if _sector_label_in_text(sk, blob):
                keys.append(sk)
        return self.resolve_sector_keys(keys)

    def is_passive_sector_product(self, fund_name: str) -> bool:
        return bool(_PASSIVE_NAME_RE.search(fund_name or ""))

    def allocations_for_sector(self, sector_key: str) -> dict[str, float]:
        block = self._sectors.get(sector_key) or {}
        raw = block.get("allocations") or {}
        out: dict[str, float] = {}
        if isinstance(raw, dict):
            for isin, pct in raw.items():
                try:
                    out[str(isin).strip().upper()] = float(pct)
                except (TypeError, ValueError):
                    continue
        return out

    def top_funds_for_sector(
        self,
        sector_key: str,
        *,
        limit: int = 5,
        min_weight_pct: float = 0.0,
        isin_allowlist: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        alloc = self.allocations_for_sector(sector_key)
        rows: list[tuple[str, float]] = []
        for isin, pct in alloc.items():
            if pct < min_weight_pct:
                continue
            if isin_allowlist is not None and isin not in isin_allowlist:
                continue
            rows.append((isin, pct))
        rows.sort(key=lambda x: (-x[1], x[0]))
        return rows[: max(1, limit)]

    def top_funds_for_sectors(
        self,
        sector_keys: list[str],
        *,
        limit: int = 5,
        min_weight_pct: float = 0.0,
        combine: Literal["max", "sum"] = "max",
        isin_allowlist: set[str] | None = None,
    ) -> list[tuple[str, float, dict[str, float]]]:
        """Return (isin, combined_score, per_sector_weights)."""
        scores: dict[str, float] = {}
        breakdown: dict[str, dict[str, float]] = {}

        for sk in sector_keys:
            for isin, pct in self.allocations_for_sector(sk).items():
                if pct < min_weight_pct:
                    continue
                if isin_allowlist is not None and isin not in isin_allowlist:
                    continue
                breakdown.setdefault(isin, {})[sk] = pct
                if combine == "sum":
                    scores[isin] = scores.get(isin, 0.0) + pct
                else:
                    scores[isin] = max(scores.get(isin, 0.0), pct)

        ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        out: list[tuple[str, float, dict[str, float]]] = []
        for isin, score in ranked:
            if len(out) >= limit:
                break
            out.append((isin, score, breakdown.get(isin, {})))
        return out


def is_passive_fund_name(name: str) -> bool:
    return bool(_PASSIVE_NAME_RE.search(name or ""))


def classify_sector_fund_purity(
    fund_name: str,
    *,
    category: str = "",
    scheme_type: str = "",
) -> Literal[
    "dedicated_sectoral",
    "diversified_equity",
    "defensive_neutral",
    "passive",
    "debt",
]:
    """Whether a scheme is a pure sector/thematic product vs incidental sector exposure."""
    name = fund_name or ""
    cat_cf = (category or "").casefold()
    st_cf = (scheme_type or "").casefold()
    if st_cf == "debt" or cat_cf == "debt" or any(
        k in name.casefold()
        for k in (
            "liquid fund",
            "overnight",
            "money market",
            "ultra short",
            "low duration",
            "short duration",
            "corporate bond",
            "gilt",
            "dynamic bond",
            "credit risk",
            "target maturity",
            "fixed horizon",
        )
    ):
        return "debt"
    if is_passive_fund_name(name) or "index" in cat_cf or st_cf.startswith("index"):
        return "passive"
    if (
        _NON_PURE_SECTOR_VEHICLE_RE.search(name)
        or "hybrid" in cat_cf
        or "arbitrage" in cat_cf
        or "multi asset" in cat_cf
    ):
        return "defensive_neutral"
    if "sector" in cat_cf or "thematic" in cat_cf:
        return "dedicated_sectoral"
    if _DEDICATED_SECTORAL_RE.search(name):
        return "dedicated_sectoral"
    return "diversified_equity"


def _sector_label_in_text(sector_key: str, text: str) -> bool:
    """Match sector labels in user text without 'Auto' ⊂ 'automotive' false positives."""
    sk = (sector_key or "").strip()
    if not sk:
        return False
    if re.search(rf"\b{re.escape(sk)}\b", text, re.I):
        return True
    if len(sk) >= 10 and sk.casefold() in text.casefold():
        return True
    return False


def sectors_from_article_industries(articles: list[dict]) -> list[str]:
    """Infer sector keys from industry_names only (not stock/ETF entity tags)."""
    labels: list[str] = []
    for a in articles:
        for ind in a.get("industry_names") or []:
            labels.append(str(ind))
    idx = get_sector_fund_ranking_index()
    keys = idx.resolve_sector_keys(labels)
    return [k for k in keys if k.casefold() not in _ARTICLE_INFER_BLOCKLIST]


_index: SectorFundRankingIndex | None = None
_index_lock = threading.Lock()
def sector_ranking_index_path() -> Path:
    settings = get_settings()
    return _repo_path(settings.sector_to_isin_weights_json)


def sector_ranking_data_available() -> bool:
    return sector_ranking_index_path().is_file()


def clear_sector_fund_ranking_index_cache() -> None:
    """Call after uploading sector_to_isin_weights.json (no restart required)."""
    global _index
    with _index_lock:
        _index = None


def get_sector_fund_ranking_index() -> SectorFundRankingIndex:
    global _index
    with _index_lock:
        if _index is not None:
            return _index
        path = sector_ranking_index_path()
        if not path.is_file():
            logger.warning(
                "Sector fund ranking file missing at %s — rankings disabled until file is copied",
                path,
            )
            _index = SectorFundRankingIndex({"sectors": {}})
            return _index
        doc = json.loads(path.read_text(encoding="utf-8"))
        _index = SectorFundRankingIndex(doc)
        logger.info(
            "Loaded sector fund ranking index: %d sectors",
            len(_index.sector_names),
        )
        return _index


def rank_funds_by_sector_exposure(
    sector_keys: list[str],
    *,
    limit: int = 5,
    severity: float = 1.0,
    regular_growth_only: bool | None = None,
    combine: Literal["max", "sum"] = "max",
    min_weight_pct: float = 0.0,
) -> dict[str, Any]:
    """Deterministic top-N funds for sector discovery queries."""
    settings = get_settings()
    if regular_growth_only is None:
        regular_growth_only = settings.impact_ranking_regular_growth_only
    idx = get_sector_fund_ranking_index()
    allowlist = load_regular_growth_isins() if regular_growth_only else None
    universe = "regular_growth" if regular_growth_only else "all_indexed"
    if not sector_keys:
        return {
            "sector_keys": [],
            "rankings": [],
            "ranking_universe": universe,
            "ranking_source": "sector_to_isin_weights",
            "severity": severity,
        }

    # Catalog lookups are local; keep a wide scan so high-weight ETFs do not crowd out sector funds.
    scan_limit = min(max(limit * 20, 120), 400)
    raw_rows = idx.top_funds_for_sectors(
        sector_keys,
        limit=scan_limit,
        min_weight_pct=min_weight_pct,
        combine=combine,
        isin_allowlist=allowlist,
    )
    from news_rag.fund_search import get_fund_index

    index = get_fund_index()

    def _catalog(isin: str) -> dict[str, Any]:
        return index.catalog_entry(isin) or {}

    buckets: dict[str, list[tuple[str, float, dict[str, float]]]] = {
        k: [] for k in _PURITY_BUCKET_ORDER
    }
    for isin, base_score, per_sector in raw_rows:
        detail = _catalog(isin)
        fname = str(detail.get("fund_short_name") or detail.get("fund_name") or isin)
        purity = classify_sector_fund_purity(
            fname,
            category=str(detail.get("category") or ""),
            scheme_type=str(detail.get("scheme_type") or ""),
        )
        buckets[purity].append((isin, base_score, per_sector))

    ordered_rows: list[tuple[str, float, dict[str, float], str]] = []
    defensive_rows: list[tuple[str, float, dict[str, float], str]] = []
    for purity in sorted(_PURITY_BUCKET_ORDER, key=lambda k: _PURITY_BUCKET_ORDER[k]):
        for isin, base_score, per_sector in buckets[purity]:
            row = (isin, base_score, per_sector, purity)
            if purity == "defensive_neutral":
                defensive_rows.append(row)
            else:
                ordered_rows.append(row)

    chosen = ordered_rows[:limit]
    rankings = []
    for isin, base_score, per_sector, purity in chosen:
        detail = _catalog(isin)
        fname = str(detail.get("fund_short_name") or detail.get("fund_name") or isin)
        rankings.append(
            {
                "isin": isin,
                "sector_weight_pct": round(base_score, 4),
                "impact_score": round(base_score * severity, 4),
                "sector_breakdown": {k: round(v, 4) for k, v in per_sector.items()},
                "fund_name": fname,
                "passive_sector_product": is_passive_fund_name(fname),
                "sector_purity": purity,
                "category": detail.get("category") or "",
                "scheme_type": detail.get("scheme_type") or "",
            }
        )
    defensive_alternatives = []
    for isin, base_score, per_sector, purity in defensive_rows[:5]:
        detail = _catalog(isin)
        defensive_alternatives.append(
            {
                "isin": isin,
                "fund_name": str(detail.get("fund_short_name") or detail.get("fund_name") or isin),
                "sector_weight_pct": round(base_score, 4),
                "sector_breakdown": {k: round(v, 4) for k, v in per_sector.items()},
                "sector_purity": purity,
                "category": detail.get("category") or "",
            }
        )
    return {
        "sector_keys": sector_keys,
        "rankings": rankings,
        "defensive_alternatives": defensive_alternatives,
        "ranking_universe": universe,
        "ranking_source": "sector_to_isin_weights",
        "severity": severity,
        "prefer_dedicated_sectoral": True,
    }
