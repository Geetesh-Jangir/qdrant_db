"""Fund name lookup must respect AMC hints (e.g. HDFC vs ABSL large & mid cap)."""

from __future__ import annotations

from news_rag.fund_search import (
    extract_fund_phrase_from_question,
    extract_top_sectors,
    get_fund_index,
    lookup_extracted_fund,
    resolve_fund_for_query,
    resolve_fund_from_question,
)


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


def test_colloquial_bluechip_aliases() -> None:
    for phrase, expected_isin in (
        ("SBI Bluechip Fund", "INF200K01180"),
        ("Axis Blue Chip Fund", "INF846K01164"),
        ("ICICI Prudential Bluechip Fund", "INF109K01BL4"),
    ):
        detail, ambiguous, _ = lookup_extracted_fund(name=phrase)
        assert not ambiguous, phrase
        assert detail is not None, phrase
        assert detail.get("isin") == expected_isin


def test_extract_nav_without_fund_word() -> None:
    isin, name = extract_fund_phrase_from_question(
        "What is the latest NAV of Parag Parikh Flexi Cap?"
    )
    assert not isin
    assert "parag" in name.lower() or "ppfas" in name.lower()
    detail, amb, _ = resolve_fund_for_query(
        "What is the latest NAV of Parag Parikh Flexi Cap?",
        isin="",
        name="",
    )
    assert not amb
    assert detail is not None
    assert "PPFAS" in (detail.get("fund_short_name") or "")


def test_invested_hdfc_defence_not_pronoun_tail() -> None:
    q = (
        "I have invested in the HDFC Defence fund, "
        "what insights do you have for me for this fund?"
    )
    _isin, name = extract_fund_phrase_from_question(q)
    assert "defence" in (name or "").lower()
    assert "hdfc" in (name or "").lower()
    detail, ambiguous, _ = resolve_fund_from_question(q)
    assert not ambiguous
    assert detail is not None
    assert detail.get("isin") == "INF179KC1GL9"
    bad, amb2, _ = lookup_extracted_fund(name="me for this fund")
    assert bad is None and not amb2


def test_fast_route_nav_without_fund_keyword() -> None:
    from news_rag.query_router import try_fast_fund_fact_route

    r = try_fast_fund_fact_route("Show latest NAV for Kotak Flexicap")
    assert r is not None
    assert r.intent == "fund_nav"
    assert "kotak" in r.fund.name.lower()
