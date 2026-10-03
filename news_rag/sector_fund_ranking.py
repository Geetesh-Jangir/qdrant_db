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
    "automotive": ("Automobiles", "Auto Components"),
    "automotive sector": ("Automobiles", "Auto Components"),
    "auto sector": ("Automobiles", "Auto Components"),
    "automobile": ("Automobiles",),
    "banking": ("Banks", "Finance"),
    "bank sector": ("Banks", "Finance"),
    "financial": ("Banks", "Finance", "Capital Markets"),
    "it sector": ("It - Software",),
    "software": ("It - Software",),
    "pharma": ("Pharmaceuticals & Biotechnology", "Healthcare Services"),
    "oil": ("Petroleum Products",),
    "crude": ("Petroleum Products",),
    "barrel": ("Petroleum Products",),
    "brent": ("Petroleum Products",),
    "energy": ("Power", "Petroleum Products"),
    "real estate": ("Realty",),
    "metal": ("Ferrous Metals", "Non - Ferrous Metals"),
    "rbi": ("Banks", "Finance"),
    "repo rate": ("Banks", "Finance"),
    "repo": ("Banks", "Finance"),
    "rate hike": ("Banks", "Finance"),
    "monetary policy": ("Banks", "Finance"),
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

    # Scan many candidates; list active diversified funds first, then index/ETFs.
    raw_rows = idx.top_funds_for_sectors(
        sector_keys,
        limit=max(limit * 25, 120),
        min_weight_pct=min_weight_pct,
        combine=combine,
        isin_allowlist=allowlist,
    )
    from news_rag.fund_search import get_fund_index

    index = get_fund_index()

    def _fname(isin: str) -> str:
        hits = index.search(isin, limit=3)
        for h in hits:
            if str(h.get("isin") or "").upper() == isin.upper():
                return str(h.get("fund_short_name") or isin)
        d = index.get_fund_detail(isin)
        if d:
            return str(d.get("fund_short_name") or d.get("fund_name") or isin)
        return isin

    active_rows: list[tuple[str, float, dict[str, float]]] = []
    passive_rows: list[tuple[str, float, dict[str, float]]] = []
    for isin, base_score, per_sector in raw_rows:
        fname = _fname(isin)
        if is_passive_fund_name(fname):
            passive_rows.append((isin, base_score, per_sector))
        else:
            active_rows.append((isin, base_score, per_sector))

    chosen = active_rows[:limit]
    if len(chosen) < limit:
        chosen.extend(passive_rows[: limit - len(chosen)])
    rankings = []
    for isin, base_score, per_sector in chosen:
        rankings.append(
            {
                "isin": isin,
                "sector_weight_pct": round(base_score, 4),
                "impact_score": round(base_score * severity, 4),
                "sector_breakdown": {k: round(v, 4) for k, v in per_sector.items()},
                "passive_sector_product": is_passive_fund_name(_fname(isin)),
            }
        )
    return {
        "sector_keys": sector_keys,
        "rankings": rankings,
        "ranking_universe": universe,
        "ranking_source": "sector_to_isin_weights",
        "severity": severity,
    }
