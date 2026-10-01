"""Fund name lookup must respect AMC hints (e.g. HDFC vs ABSL large & mid cap)."""

from __future__ import annotations

from news_rag.fund_search import extract_top_sectors, get_fund_index, lookup_extracted_fund


def test_hdfc_large_mid_cap_not_absl() -> None:
    detail, ambiguous, _close = lookup_extracted_fund(
        isin="",
        name="hdfc large and mid cap fund",
    )
    assert not ambiguous
    assert detail is not None
    name = (detail.get("fund_short_name") or detail.get("fund_name") or "").lower()
    assert "hdfc" in name
    assert detail.get("isin") == "INF179KA1RT1"
    assert len(extract_top_sectors(detail, limit=5)) >= 3


def test_fund_index_has_amc_on_search_hit() -> None:
    index = get_fund_index()
    hits = index.search("HDFC Large", limit=3)
    assert hits
    assert any("hdfc" in (h.get("fund_short_name") or "").lower() for h in hits)
