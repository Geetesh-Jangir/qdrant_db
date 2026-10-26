"""RapidFuzz + optional embedding fallback for fund name resolution."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from rapidfuzz import fuzz

from news_rag.config import get_settings

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]


_SPELLING_FOLDS: tuple[tuple[str, str], ...] = (
    ("defense", "defence"),
    ("color", "colour"),
    ("organize", "organise"),
)


def fold_fund_spelling(text: str) -> str:
    """Normalize US/UK spelling variants before catalog lookup."""
    s = (text or "").strip()
    lower = s.lower()
    for us, uk in _SPELLING_FOLDS:
        if us in lower:
            lower = lower.replace(us, uk)
    if lower != s.lower():
        return lower
    return s


def _normalize_fund_text(text: str) -> str:
    s = fold_fund_spelling(text or "").lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


_STOP = frozenset(
    {
        "fund",
        "funds",
        "mutual",
        "scheme",
        "plan",
        "growth",
        "regular",
        "direct",
        "the",
        "and",
        "of",
        "in",
        "for",
        "to",
        "a",
        "an",
        "is",
        "about",
        "my",
    }
)


_PLAN_SUFFIX_RE = re.compile(
    r"\s*-\s*(?:Regular|Direct)\s+Plan\s*-\s*(?:Growth|IDCW|Dividend).*$",
    re.I,
)
_GROWTH_SUFFIX_RE = re.compile(r"\s*-\s*Growth\s*$", re.I)

_DISTINCTIVE_TOKENS = frozenset(
    {
        "fof",
        "active",
        "etf",
        "elss",
        "arbitrage",
        "equal",
        "weight",
        "momentum",
        "hybrid",
        "index",
        "flexi",
        "contra",
        "value",
        "focused",
        "liquid",
        "gilt",
        "overnight",
        "200",
        "500",
        "50",
    }
)


def catalog_name_for_match(entry: dict[str, Any]) -> str:
    """Strip plan labels so user phrases align with catalog rows."""
    name = str(entry.get("fund_short_name") or entry.get("fund_name") or "")
    name = _PLAN_SUFFIX_RE.sub("", name).strip()
    name = _GROWTH_SUFFIX_RE.sub("", name).strip()
    return name


def _cap_structure_adjustment(norm_query: str, norm_catalog: str) -> float:
    q = norm_query.split()
    c = norm_catalog
    adj = 0.0
    q_has_mid = "mid" in q
    q_has_large = "large" in q
    q_has_cap = "cap" in q
    if q_has_large and q_has_cap and not q_has_mid:
        if "mid" in c.split() or "&" in c or " and " in c:
            adj -= 50.0
        elif "large" in c and "cap" in c:
            adj += 12.0
    if q_has_mid and q_has_cap and not q_has_large:
        if "large" in c and "mid" in c:
            adj -= 35.0
    if q_has_large and q_has_mid and q_has_cap:
        if "large" in c and "mid" in c:
            adj += 18.0
    if "trigger" in c and "trigger" not in norm_query:
        adj -= 30.0
    return adj


_CATALOG_FILLER_TOKENS = frozenset(
    {
        "fund",
        "regular",
        "direct",
        "plan",
        "growth",
        "mutual",
        "the",
        "and",
        "of",
    }
)

_EXTRA_NAME_TOKENS = frozenset(
    {
        "momentum",
        "quality",
        "shariah",
        "equal",
        "weight",
        "esg",
        "defence",
        "defense",
        "healthcare",
        "pharma",
        "banking",
        "infrastructure",
        "consumption",
        "technology",
        "business",
        "cycle",
        "manufacturing",
        "innovation",
        "digital",
        "housing",
        "psu",
        "commodities",
        "gold",
        "silver",
    }
)


def _catalog_name_extra_token_penalty(norm_query: str, norm_catalog: str) -> float:
    """Penalize catalog names that add qualifiers the user did not say (e.g. Momentum Quality 50)."""
    q_toks = set(norm_query.split())
    c_toks = set(norm_catalog.split())
    extras = {t for t in (c_toks - q_toks) if t not in _CATALOG_FILLER_TOKENS and len(t) > 1}
    adj = -14.0 * len(extras & _EXTRA_NAME_TOKENS)
    adj += -10.0 * len([t for t in extras if t.isdigit() and t not in q_toks])
    return adj


def _distinctive_token_adjustment(norm_query: str, norm_catalog: str) -> float:
    q_toks = set(norm_query.split())
    c_toks = set(norm_catalog.split())
    adj = 0.0
    for t in _DISTINCTIVE_TOKENS:
        if t in q_toks and t in c_toks:
            adj += 8.0
        elif t in q_toks and t not in c_toks:
            adj -= 18.0
    return adj


def rank_catalog_entries_for_phrase(
    phrase: str,
    entries: list[dict[str, Any]],
    *,
    amc_filter: list[dict[str, Any]] | None = None,
) -> list[tuple[float, dict[str, Any], str]]:
    """Fuzzy-match user phrase against the full catalog (thousands of schemes)."""
    pool = amc_filter if amc_filter is not None else entries
    try:
        from news_rag.fund_search import _index_benchmark_score_adjustment, _normalize_fund_text
    except ImportError:
        _normalize_fund_text = _normalize_fund_text  # type: ignore[misc,assignment]

        def _index_benchmark_score_adjustment(_q: str, _c: str) -> float:  # noqa: ANN001
            return 0.0

    norm = _normalize_fund_text(phrase)
    if not norm:
        return []
    scored: list[tuple[float, dict[str, Any], str]] = []
    for entry in pool:
        c_name = catalog_name_for_match(entry)
        c_norm = _normalize_fund_text(c_name)
        if not c_norm:
            continue
        ts = float(fuzz.token_set_ratio(norm, c_norm))
        wr = float(fuzz.WRatio(norm, c_norm))
        pr = float(fuzz.partial_ratio(norm, c_norm))
        score = max(ts, wr, pr)
        if norm in c_norm or c_norm in norm:
            score = max(score, 96.0)
        score += _index_benchmark_score_adjustment(norm, c_norm)
        score += _cap_structure_adjustment(norm, c_norm)
        score += _distinctive_token_adjustment(norm, c_norm)
        score += _catalog_name_extra_token_penalty(norm, c_norm)
        scored.append((score, entry, "rapidfuzz"))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("fund_short_name") or "")))
    return scored


def load_fund_embedding_cache() -> dict[str, list[float]] | None:
    settings = get_settings()
    path = _REPO_ROOT / "data" / "fund_name_embeddings.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if isinstance(v, list)}
    except (OSError, json.JSONDecodeError):
        return None
    return None


def embedding_best_match(
    phrase: str,
    entries: list[dict[str, Any]],
    cache: dict[str, list[float]],
) -> tuple[float, dict[str, Any] | None]:
    try:
        from news_rag.embed import embed_query
    except ImportError:
        return 0.0, None
    q_vec = embed_query(phrase)
    best_score = 0.0
    best_entry: dict[str, Any] | None = None
    for entry in entries:
        isin = str(entry.get("isin") or "").upper()
        vec = cache.get(isin)
        if not vec or len(vec) != len(q_vec):
            continue
        dot = sum(a * b for a, b in zip(q_vec, vec))
        if dot > best_score:
            best_score = dot
            best_entry = entry
    return best_score, best_entry
