"""Tests for smart fund-why, composer guardrails, facet aliases, and streaming SSE."""

import asyncio
import json
import pytest

from news_rag.insight.brief import QuestionBrief, _detect_funds, _infer_window_days
from news_rag.insight.facets import canonical_facet, validate_facets
from news_rag.insight.findings import Findings, FundFinding, SectorFinding
from news_rag.insight.gather import EvidenceItem, EvidenceSet
from news_rag.insight.blocks.compute import compute_findings
from news_rag.insight.interpret import check_composer_guardrails
from news_rag.insight.pipeline import compose, stream_insight_pipeline


def test_facet_alias_fund_facts_holdings():
    """Verify facet alias fund_facts_holdings canonicalizes to fund_composition and computes FundFinding."""
    assert canonical_facet("fund_facts_holdings") == "fund_composition"
    assert canonical_facet("fund_holdings") == "fund_composition"
    assert canonical_facet("fund_facts_nav") == "return_series"

    brief = QuestionBrief(
        funds=["HDFC Large Cap Fund"],
        window_days=30,
        window_label="1 month",
        evidence_needs=["fund_facts_holdings", "return_series"],
    )
    ev = EvidenceSet()
    ev.items.append(
        EvidenceItem(
            "fund_composition",
            "fund_composition",
            "INF179K01BE2",
            {
                "isin": "INF179K01BE2",
                "fund_name": "HDFC Top 100 Fund",
                "sectors": [{"sector": "Banks", "percentage": 30.5}],
                "holdings": [{"name": "HDFC Bank", "percentage": 9.5}],
            },
        )
    )
    ev.items.append(
        EvidenceItem(
            "return_series",
            "fund_return_series",
            "INF179K01BE2",
            {"isin": "INF179K01BE2", "window_pct": -2.8},
        )
    )

    # by_facet alias resolution
    assert len(ev.by_facet("fund_facts_holdings")) == 1
    assert len(ev.by_facet("fund_composition")) == 1

    findings = compute_findings(brief, ev, None)
    assert len(findings.funds) == 1
    assert findings.funds[0].isin == "INF179K01BE2"
    assert findings.funds[0].return_window_pct == -2.8


def test_fuzzy_fund_why_detection():
    """Verify 'why is hdfc large cap is down in last one month?' detects fund with 1-month window."""
    q = "why is hdfc large cap is down in last one month?"
    funds = _detect_funds(q)
    assert len(funds) >= 1
    assert any("hdfc" in f.lower() for f in funds)

    days, label = _infer_window_days(q)
    assert days == 30
    assert label == "1 month"


def test_composer_guardrails():
    """Verify guard rail rejection on outlet name, publication date, ungrounded number, advice."""
    packet = {
        "question": "why down",
        "benchmark": {"name": "Nifty 50", "return_pct": -1.5},
        "funds": [{"name": "HDFC Top 100", "return_pct": -2.5}],
    }
    evidence_text = "Nifty 50 -1.5% HDFC Top 100 -2.5%"

    # Clean text
    clean = "HDFC Top 100 moved down 2.5% while Nifty 50 fell 1.5%."
    assert check_composer_guardrails(clean, packet, evidence_text) == []

    # Outlet violation
    outlet = "HDFC Top 100 fell according to Economic Times reports."
    violations = check_composer_guardrails(outlet, packet, evidence_text)
    assert any("outlet" in v.lower() for v in violations)

    # Parenthetical publication citation is a date violation. A bare event date is not.
    date_text = "The fund declined 2.5% (16 Sep)."
    violations = check_composer_guardrails(date_text, packet, evidence_text)
    assert any("dates" in v.lower() for v in violations)
    event_date = "On 16 Sep the fund declined 2.5%."
    assert not any(
        "dates" in v.lower()
        for v in check_composer_guardrails(event_date, packet, evidence_text)
    )

    # Investment advice violation
    advice = "You should sell HDFC Top 100 right now."
    violations = check_composer_guardrails(advice, packet, evidence_text)
    assert any("advice" in v.lower() for v in violations)

    # Ungrounded number violation
    invented = "HDFC Top 100 dropped by 88.9% due to panic."
    violations = check_composer_guardrails(invented, packet, evidence_text)
    assert any("ungrounded" in v.lower() for v in violations)


@pytest.mark.asyncio
async def test_streaming_sse_order(monkeypatch):
    """Verify streaming generator yields status events -> done payload in proper SSE format."""
    from news_rag.insight import pipeline as pipe_mod

    mock_state = {
        "question": "what is happening in the market?",
        "brief": QuestionBrief(window_label="1 month"),
        "evidence": EvidenceSet(),
        "findings": Findings(),
        "news_read": None,
        "pipeline_errors": [],
        "refused": False,
    }
    monkeypatch.setattr(pipe_mod, "run_until_compose", lambda *a, **k: mock_state)
    monkeypatch.setattr(pipe_mod, "llm_api_key_configured", lambda *a, **k: False)

    events = []
    async for packet in stream_insight_pipeline("what is happening in the market?"):
        for line in packet.strip().split("\n\n"):
            if line.startswith("event:"):
                ev_type = line.split("\n")[0].replace("event:", "").strip()
                events.append(ev_type)

    assert "status" in events
    assert "done" in events
    # 'status' must arrive before 'done'
    assert events.index("status") < events.index("done")
