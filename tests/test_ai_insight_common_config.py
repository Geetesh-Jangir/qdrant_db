"""Config, envelope, and display helpers."""

import pytest
from pydantic import ValidationError

from ai_insight.common.config import load_config
from ai_insight.common.display import SECTOR_DISPLAY, fmt_inr_crore, fmt_pct, ordinal
from ai_insight.common.schemas import Envelope, MarketDriverFactsBase
from news_pipeline.config import SECTOR_QUERIES


def test_config_defaults_and_cutoff(tmp_path):
    cfg = load_config(
        {
            "INSIGHTS_DATA_DIR": str(tmp_path),
            "INSIGHTS_LLM_MODEL": "claude-haiku-5-5",
            "INSIGHTS_CUTOFF_IST": "17:10",
            "INSIGHTS_MAX_INGEST_AGE_HOURS": "4",
        }
    )
    assert cfg.llm_model == "claude-haiku-5-5"
    assert cfg.llm_provider == "anthropic"
    assert cfg.cutoff_ist == "17:10"
    assert cfg.max_ingest_age_hours == 4
    assert cfg.holidays_path == tmp_path / "_data" / "nse_holidays.json"


def test_config_rejects_bad_cutoff():
    with pytest.raises(ValueError):
        load_config({"INSIGHTS_CUTOFF_IST": "evening"})


def test_envelope_requires_ist_offset_and_skip_reason():
    with pytest.raises(ValidationError):
        Envelope(insight_id="market_driver_digest", trading_date="2026-11-16", as_of_ist="2026-11-16T12:00:00Z", status="ok")
    with pytest.raises(ValidationError):
        Envelope(
            insight_id="market_driver_digest",
            trading_date="2026-11-16",
            as_of_ist="2026-11-16T17:10:00+05:30",
            status="skipped",
        )


def test_facts_numeric_leaves():
    facts = MarketDriverFactsBase(
        trading_date="2026-11-16",
        window_utc=["2026-11-13T10:00:00Z", "2026-11-16T12:00:00Z"],
        nifty_change_pct=-0.61,
        fii_net_crore=2340,
    )
    leaves = dict(facts.numeric_leaves())
    assert leaves["nifty_change_pct"] == -0.61
    assert leaves["fii_net_crore"] == 2340


def test_sector_display_covers_pipeline_names():
    assert set(SECTOR_DISPLAY) == set(SECTOR_QUERIES)


def test_format_helpers():
    assert fmt_inr_crore(2340) == "₹2,340 crore"
    assert fmt_inr_crore(-1200.5).startswith("-₹")
    assert fmt_pct(-0.61) == "-0.61%"
    assert ordinal(1) == "1st"
    assert ordinal(2) == "2nd"
    assert ordinal(11) == "11th"
    assert ordinal(23) == "23rd"
