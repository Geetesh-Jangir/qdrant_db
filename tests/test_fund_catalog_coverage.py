"""regular-growth-by-amc.md: load parity and lookup coverage."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from news_rag.fund_search import (
    _PLAN_SUFFIX_RE,
    _catalog_alias_keys,
    get_fund_index,
    lookup_extracted_fund,
    resolve_fund_from_question,
)

_MD = Path(__file__).resolve().parents[1] / "data/fund_holdings_aggregate/regular-growth-by-amc.md"


def _md_isins() -> set[str]:
    isins: set[str] = set()
    for line in _MD.read_text(encoding="utf-8").splitlines():
        if not line.startswith("- ") or "`" not in line:
            continue
        m = re.search(r"`(INF[A-Z0-9]{9})`", line)
        if m:
            isins.add(m.group(1).upper())
    return isins


def test_fund_index_parity_with_markdown() -> None:
    idx = get_fund_index()
    idx._ensure_loaded()
    md = _md_isins()
    assert len(idx._entries) == len(md)
    missing = [i for i in md if i not in idx._entries_by_isin]
    assert missing == []


def test_every_catalog_name_has_alias_isin() -> None:
    """All scheme lines have alias keys pointing at the same ISIN (fast parity)."""
    from news_rag.fund_search import _normalize_fund_text

    idx = get_fund_index()
    idx._ensure_loaded()
    failures: list[str] = []
    for entry in idx._entries:
        isin = str(entry.get("isin") or "").upper()
        fname = str(entry.get("fund_name") or "")
        norm = _normalize_fund_text(fname)
        if idx._alias_to_isin.get(norm) != isin:
            failures.append(fname)
    assert not failures, f"missing aliases ({len(failures)}): {failures[:5]}"


def test_exact_catalog_name_lookup_sample() -> None:
    """Spot-check lookup_extracted_fund on a spread sample (alias-fast path)."""
    idx = get_fund_index()
    idx._ensure_loaded()
    slice_entries = idx._entries[::47][:50]
    failures: list[str] = []
    for entry in slice_entries:
        isin = str(entry.get("isin") or "").upper()
        fname = str(entry.get("fund_name") or "")
        detail, ambiguous, _ = lookup_extracted_fund(name=fname)
        if ambiguous or not detail or str(detail.get("isin") or "").upper() != isin:
            failures.append(fname)
    assert not failures, f"failed lookups ({len(failures)}): {failures[:5]}"


def test_alias_keys_include_stripped_plan_suffix() -> None:
    name = "HDFC Large & Mid Cap Fund - Regular Plan - Growth"
    short = _PLAN_SUFFIX_RE.sub("", name).strip()
    keys = _catalog_alias_keys(name)
    assert any("large" in k and "mid" in k for k in keys)
    idx = get_fund_index()
    idx._ensure_loaded()
    d1, a1, _ = lookup_extracted_fund(name=name)
    d2, a2, _ = lookup_extracted_fund(name=short)
    assert not a1 and not a2 and d1 and d2
    assert d1.get("isin") == d2.get("isin")


def test_colloquial_large_and_mid_resolves() -> None:
    detail, ambiguous, _ = resolve_fund_from_question("tell me about hdfc large and mid cap fund")
    assert not ambiguous
    assert detail is not None
    assert detail.get("isin") == "INF179KA1RT1"