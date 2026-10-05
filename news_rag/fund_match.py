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


def fuzzy_rank_entries(
    phrase: str,
    entries: list[dict[str, Any]],
    *,
    amc_filter: list[dict[str, Any]] | None = None,
) -> list[tuple[float, dict[str, Any], str]]:
    """Return sorted (score, entry, method) candidates."""
    pool = amc_filter if amc_filter is not None else entries
    norm = _normalize_fund_text(phrase)
    if not norm:
        return []
    scored: list[tuple[float, dict[str, Any], str]] = []
    for entry in pool:
        c_name = str(entry.get("fund_short_name") or entry.get("fund_name") or "")
        c_norm = _normalize_fund_text(c_name)
        if not c_norm:
            continue
        ts = fuzz.token_set_ratio(norm, c_norm)
        ps = fuzz.partial_ratio(norm, c_norm)
        score = max(ts, ps)
        if norm in c_norm or c_norm in norm:
            score = max(score, 95.0)
        scored.append((float(score), entry, "rapidfuzz"))
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
