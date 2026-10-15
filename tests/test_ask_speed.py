"""Deterministic checks for the ask-a-question latency plan."""

from news_rag.insight.analyst import analyst_should_run
from news_rag.insight.brief import QuestionBrief, question_tier, random_fund_count, validate_brief_plan
from news_rag.insight.findings import Findings
from news_rag.insight.gather import EvidenceSet, LedgerEntry
from news_rag.insight.grounding import mentions_publication_date, publication_date_keys, tidy_prose
from news_rag.insight.registry import ensure_registry, registry_prompt_block
from news_rag.insight.verify import verify_answer
from news_rag.sector_fund_ranking import candidate_sector_names, top_sector_names


class _Settings:
    insight_use_llm_analyst = True
    insight_analyst_mode = "auto"
    insight_prune_market_facets = True


def test_tidy_prose_keeps_percent_after_a_number():
    assert "6.1 percent" in tidy_prose("The index fell 6.1 percent today")
    assert "per cent" not in tidy_prose("a stray per cent with no number")


def test_publication_date_does_not_flag_unrelated_event_dates():
    keys = publication_date_keys("2026-10-07")
    assert mentions_publication_date("The RBI hiked rates on 7 October.", keys)
    assert not mentions_publication_date("The RBI hiked rates on 15 October.", keys)
    assert mentions_publication_date("Sold off (7 Oct).", set())


def test_market_brief_is_tier_t0_and_one_news_path():
    brief = QuestionBrief(evidence_needs=["market_overview", "news_drivers", "sector_impact_direction"])
    assert question_tier("whats happening in the market right now?", brief) == "t0"
    needs = validate_brief_plan(brief, "whats happening in the market right now?")
    assert needs == ["market_overview"]


def test_driver_question_keeps_affected_sectors():
    brief = QuestionBrief(drivers=["crude_oil"], evidence_needs=["news_drivers", "exposure_link"])
    needs = validate_brief_plan(brief, "which funds are affected if crude rises?")
    assert "sector_impact_direction" in needs
    assert "news_drivers" in needs


def test_top_sectors_are_a_short_candidate_list():
    top = top_sector_names(50)
    assert len(top) == 50
    assert top[0] == "Banks"
    extra = candidate_sector_names(
        [{"sector_names": ["Oil & Gas Refining & Marketing"]}],
        cap=50,
    )
    assert "Banks" in extra
    assert "Oil & Gas Refining & Marketing" in extra
    assert len(extra) < 80


def test_compact_catalog_is_shorter_than_the_full_one():
    ensure_registry()
    full = registry_prompt_block(compact=False)
    compact = registry_prompt_block(compact=True)
    assert len(compact) < len(full) / 2
    assert "layered_news" in compact


def test_analyst_auto_skips_market_and_keeps_named_funds():
    settings = _Settings()
    market = QuestionBrief(evidence_needs=["market_overview"])
    named = QuestionBrief(funds=["HDFC Flexi Cap"], evidence_needs=["fund_facts_nav", "holding_drivers"])
    profile = QuestionBrief(funds=["DSP India TIGER"], evidence_needs=["fund_facts_nav", "fund_composition"])
    assert analyst_should_run(market, Findings(), settings) is False
    assert analyst_should_run(named, Findings(), settings) is True
    assert analyst_should_run(profile, Findings(), settings) is False


def test_two_random_funds_stay_on_the_profile_path():
    assert random_fund_count("take any two random funds and tell me about them?") == 2
    brief = QuestionBrief(funds=["Fund A", "Fund B"], evidence_needs=["news_drivers", "holding_drivers", "fund_vs_index"])
    needs = validate_brief_plan(brief, "take any two random funds and tell me about them?")
    assert "peer_compare" in needs
    assert "news_drivers" not in needs
    assert "holding_drivers" not in needs
    assert "fund_facts_nav" in needs


def test_pipeline_voice_drops_packet_language():
    from news_rag.insight.interpret import _drop_pipeline_voice

    text = (
        "DSP India TIGER returned -2.16% over one month.\n\n"
        "What the packet shows: if you can supply the attribution table I will write the full narrative."
    )
    cleaned = _drop_pipeline_voice(text)
    assert "packet" not in cleaned.lower()
    assert "-2.16%" in cleaned


def test_verify_retry_facets_for_unavailable_evidence():
    brief = QuestionBrief()
    evidence = EvidenceSet(
        ledger=[LedgerEntry(facet="benchmark", status="unavailable", reason="no_index")]
    )
    result = verify_answer(brief, Findings(), evidence, insight_text="No numbers here.")
    assert "benchmark" in result.retry_facets
