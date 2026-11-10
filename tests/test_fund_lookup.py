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
    sectors = extract_top_sectors(detail, limit=5)
    if sectors:
        assert len(sectors) >= 3


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
    short_name = detail.get("fund_short_name") or detail.get("fund_name") or ""
    assert "PPFAS" in short_name or "Parag Parikh" in short_name


def test_absl_gold_etf_is_the_etf_not_a_gold_fund_list() -> None:
    detail, ambiguous, _ = resolve_fund_for_query("tell me absl gold etf")
    assert not ambiguous
    assert detail is not None
    assert detail.get("isin") == "INF209KB18D3"


def test_absl_nifty_50_etf_not_momentum_200() -> None:
    for question, expected_isin in (
        ("what are the top 5 sectors of absl nifty 50 etf", "INF209KB19D1"),
        ("INF209KB19D1", "INF209KB19D1"),
        ("Aditya Birla Sun Life Nifty 50 ETF", "INF209KB19D1"),
    ):
        detail, ambiguous, _ = resolve_fund_for_query(question)
        assert not ambiguous, question
        assert detail is not None, question
        assert detail.get("isin") == expected_isin, (question, detail.get("fund_short_name"))


def test_angel_one_nifty_total_market_index_from_catalog() -> None:
    for question in (
        "what are the top 5 sectors of angel one nifty total market index fund",
        "what are the top 5 sectors of angel one total market index fund",
    ):
        detail, ambiguous, _ = resolve_fund_for_query(question)
        assert not ambiguous, question
        assert detail is not None, question
        assert detail.get("isin") == "INF1J2R01031"


def test_absl_conservative_hybrid_active_fof() -> None:
    q = "what are the top 5 sectors of absl Conservative Hybrid Active FOF"
    detail, ambiguous, _ = resolve_fund_for_query(q)
    assert not ambiguous
    assert detail is not None
    assert detail.get("isin") == "INF084M01044"
    name = (detail.get("fund_short_name") or "").lower()
    assert "conservative hybrid active" in name


def test_absl_nifty_50_index_fund_when_fund_wording() -> None:
    detail, ambiguous, _ = resolve_fund_for_query("what are the top 5 sectors of absl nifty 50 fund")
    assert not ambiguous
    assert detail is not None
    assert detail.get("isin") == "INF209K01LB2"


def test_absl_large_cap_is_not_frontline_or_the_trigger_plan() -> None:
    from news_rag.fund_search import prefer_resolved_fund_name

    detail, ambiguous, _ = resolve_fund_for_query(
        "tell me about the fund managers of absl large cap fund"
    )
    assert not ambiguous
    assert detail is not None
    assert detail.get("isin") == "INF209K01BR9"
    name = (detail.get("fund_name") or "").lower()
    assert "large cap" in name
    assert "frontline" not in name
    assert "trigger" not in name
    shown = prefer_resolved_fund_name(
        {"fund_name": "Aditya Birla Sun Life Frontline Equity Fund", "isin": "INF209K01BR9"},
        detail,
    )
    assert "Large Cap" in shown["fund_name"]
    assert "Frontline" not in shown["fund_name"]


def test_absl_and_ppfas_shorthand() -> None:
    for question, needle in (
        ("top 3 sectors of absl large cap", "aditya birla"),
        ("ppfas large cap sectors", "parag parikh"),
        ("what are the top holdings of ppfas flexi cap", "parag parikh"),
    ):
        detail, ambiguous, _ = resolve_fund_for_query(question)
        assert not ambiguous, question
        assert detail is not None, question
        name = (detail.get("fund_short_name") or detail.get("fund_name") or "").lower()
        assert needle in name, (question, name)


def test_quant_small_cap_is_quant_amc_not_quantum_or_axis_quant() -> None:
    for phrase in ("quant small cap", "quant small cap fund"):
        detail, ambiguous, _ = lookup_extracted_fund(name=phrase)
        assert not ambiguous, phrase
        assert detail is not None, phrase
        assert detail.get("isin") in ("INF966L01051", "INF966L01AA0"), phrase
    detail, ambiguous, _ = resolve_fund_for_query(
        "why do quant small cap fund is going down lately? give me in depth?"
    )
    assert not ambiguous
    assert detail is not None
    assert detail.get("isin") in ("INF966L01051", "INF966L01AA0")


def test_quantum_gold_etf_is_quantum_not_quant() -> None:
    detail, ambiguous, _ = lookup_extracted_fund(name="Quantum Gold ETF")
    assert not ambiguous
    assert detail is not None
    assert detail.get("isin") == "INF082J01010"
    name = (detail.get("fund_short_name") or detail.get("fund_name") or "").lower()
    assert name.startswith("quantum gold etf")
    assert "fof" not in name


def test_axis_quant_is_not_quant_amc() -> None:
    detail, ambiguous, _ = lookup_extracted_fund(name="axis quant fund")
    assert not ambiguous
    assert detail is not None
    name = (detail.get("fund_short_name") or "").lower()
    assert "axis" in name
    assert detail.get("isin") == "INF846K011A2"


def test_invested_hdfc_large_cap_not_large_mid() -> None:
    q = (
        "I have invested in the HDFC large cap fund, "
        "what insights do you have for me for this fund?"
    )
    detail, ambiguous, _ = resolve_fund_from_question(q)
    assert not ambiguous
    assert detail is not None
    name = (detail.get("fund_short_name") or "").lower()
    assert "large cap" in name or "large cap fund" in name
    assert "mid" not in name
    assert detail.get("isin") == "INF179K01BE2"


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

