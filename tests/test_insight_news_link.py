"""News -> fund link (compute), hybrid composer, and brief detectors (no network)."""

from types import SimpleNamespace

from news_rag.insight import interpret as interpret_mod
from news_rag.insight.blocks import compute as compute_mod
from news_rag.insight.blocks.compute import (
    _alignment,
    _news_link_for_fund,
    _tilt,
    compute_findings,
)
from news_rag.insight.brief import QuestionBrief, SubAsk, _detect_drivers, _detect_sector
from news_rag.insight.gather import EvidenceItem, EvidenceSet
from news_rag.insight.interpret import compose_from_findings
from news_rag.insight.news_reader import NewsClaim, NewsRead, SectorCall


# ---------------------------------------------------------------- compute


def test_tilt_and_alignment_rules():
    assert _tilt(20, 2) == "tailwind"
    assert _tilt(2, 20) == "headwind"
    assert _tilt(10, 9) == "mixed"
    assert _tilt(1, 1) == "neutral"
    assert _tilt(0, 0, mixed=20) == "mixed"  # a mixed sector counts half each way

    assert _alignment("tailwind", 20, 5.0) == "aligned"
    assert _alignment("tailwind", 20, -5.0) == "diverged"
    assert _alignment("headwind", 20, -5.0) == "aligned"
    assert _alignment("headwind", 20, 5.0) == "diverged"
    assert _alignment("tailwind", 20, 0.4) == "flat"
    assert _alignment("tailwind", 8, 5.0) == "diluted"  # news touches too little of the fund
    assert _alignment("mixed", 25, 5.0) == "mixed"
    assert _alignment("tailwind", 20, None) == "unknown"


def test_sector_named_both_ways_counts_as_mixed_not_dropped():
    sectors = [
        {"sector": "Automobiles", "percentage": 16.0},
        {"sector": "Banks", "percentage": 20.0},
        {"sector": "Retailing", "percentage": 10.0},
    ]
    pos = [{"name": "Automobiles", "reason": "demand"}, {"name": "Retailing", "reason": "festive"}]
    neg = [{"name": "Automobiles", "reason": "costs"}]
    p, n, m, prow, nrow, mrow = _news_link_for_fund(sectors, pos, neg)
    assert (p, n, m) == (10.0, 0.0, 16.0)
    assert mrow[0]["sector"] == "Automobiles"
    assert prow[0]["sector"] == "Retailing"
    assert nrow == []


def _evidence() -> EvidenceSet:
    ev = EvidenceSet()
    ev.items.append(
        EvidenceItem(
            "exposure_link",
            "sector_funds",
            "Automobiles",
            {
                "rankings": [
                    {"isin": "INF1", "fund_name": "Auto Heavy Fund", "sector_weight_pct": 30.0},
                    {"isin": "INF2", "fund_name": "Bank Heavy Fund", "sector_weight_pct": 12.0},
                ]
            },
        )
    )
    ev.items.append(
        EvidenceItem(
            "fund_composition",
            "fund_composition",
            "INF1",
            {
                "isin": "INF1",
                "sectors": [{"sector": "Automobiles", "percentage": 30.0}, {"sector": "Banks", "percentage": 10.0}],
                "holdings": [{"name": "Maruti Suzuki", "percentage": 8.0}],
            },
        )
    )
    ev.items.append(
        EvidenceItem(
            "fund_composition",
            "fund_composition",
            "INF2",
            {
                "isin": "INF2",
                "sectors": [{"sector": "Banks", "percentage": 40.0}, {"sector": "Automobiles", "percentage": 12.0}],
            },
        )
    )
    ev.items.append(EvidenceItem("return_series", "fund_return_series", "INF1", {"isin": "INF1", "window_pct": 6.0}))
    ev.items.append(EvidenceItem("return_series", "fund_return_series", "INF2", {"isin": "INF2", "window_pct": -3.0}))
    ev.items.append(EvidenceItem("benchmark", "index_series", "Automobiles", {"return_pct": 1.0, "benchmark_label": "Nifty Auto"}))
    return ev


def _read(tone="positive") -> NewsRead:
    return NewsRead(
        tone=tone,
        tone_reason="Festive demand is strong.",
        claims=[
            NewsClaim("Sales rose 36.5% in August.", "positive", 1, "Car sales", "https://x/a", "economictimes.indiatimes.com", "2026-09-16")
        ],
        sectors_positive=[SectorCall("Automobiles", "record sales")],
        mode="llm",
    )


def _brief() -> QuestionBrief:
    return QuestionBrief(
        goal="auto funds",
        sub_asks=[SubAsk("1", "describe", "describe"), SubAsk("2", "funds", "list")],
        subjects=[{"role": "sector", "canonical": "Automobiles"}],
        sector_keys=["Automobiles"],
        wants_funds_flag=True,
    )


def test_compute_links_news_to_each_fund():
    findings = compute_findings(_brief(), _evidence(), _read())
    by = {f.isin: f for f in findings.funds}
    assert by["INF1"].news_tilt == "tailwind"
    assert by["INF1"].alignment == "aligned"  # tailwind and +6%
    assert by["INF1"].pos_exposure_pct == 30.0
    assert by["INF1"].top_holdings[0]["name"] == "Maruti Suzuki"
    assert by["INF1"].mechanism.startswith("Automobiles: record sales")
    # only 12% of INF2 is touched by the news -> diluted, whatever the return
    assert by["INF2"].alignment == "diluted"
    sec = findings.sector
    assert sec.tone == "positive" and sec.claims[0]["id"] == "c1"
    assert sec.claims[0]["cite"] == "Economic Times, 16 Sep"
    assert "claim_c1=Sales rose 36.5% in August." in findings.evidence_text


def test_compute_works_without_a_news_read():
    findings = compute_findings(_brief(), _evidence(), None)
    assert findings.funds  # still produces fund findings
    assert findings.sector.claims == []


# ---------------------------------------------------------------- interpret


def _llm(parsed):
    return lambda **_k: SimpleNamespace(parsed=parsed, truncated=False)


def _compose(monkeypatch, parsed):
    monkeypatch.setattr(interpret_mod, "llm_api_key_configured", lambda *_a, **_k: True)
    monkeypatch.setattr(interpret_mod, "call_json_llm", _llm(parsed))
    monkeypatch.setattr(interpret_mod, "call_insight_llm", lambda *_a, **_k: None)
    brief = _brief()
    findings = compute_findings(brief, _evidence(), _read())
    return compose_from_findings("q", brief, findings, _evidence()), findings


def test_hybrid_compose_renders_citations_and_keeps_code_numbers(monkeypatch):
    parsed = {
        "headline": "**Automobiles** news is **positive** on record festive sales.",
        "sector_read": "Sales hit a record [c1]. Costs are a risk. It helps carmakers.",
        "fund_lines": {"INF1": "Maruti Suzuki carries the demand news into this fund.", "INF2": "Banks dominate."},
        "closing": "**Auto Heavy Fund** sits most on the tailwind side.",
    }
    out, _ = _compose(monkeypatch, parsed)
    assert out.answer_trace["mode"] == "llm_hybrid"
    assert "Economic Times" not in out.display
    assert "[c1]" not in out.display
    assert "Maruti Suzuki carries the demand news" in out.display
    # numbers/labels come from code, not the model
    assert "Automobiles 30.0%" in out.display
    assert "tailwind" in out.display
    assert out.answer_trace["field_fallbacks"] == []


def test_hybrid_falls_back_per_field(monkeypatch):
    parsed = {
        "headline": "You should buy auto funds now.",  # advice -> fallback
        "sector_read": "Sales are strong.",  # no citation although claims exist -> fallback
        "fund_lines": {"INF1": "Good line about Maruti Suzuki."},  # INF2 missing -> fallback
        "closing": "",
    }
    out, _ = _compose(monkeypatch, parsed)
    fb = out.answer_trace["field_fallbacks"]
    assert "headline" in fb and "sector_read" in fb and "closing" in fb and "fund:INF2" in fb
    assert "buy" not in out.headline.lower()
    assert "Economic Times" not in out.display


def test_invented_number_is_stripped(monkeypatch):
    parsed = {
        "headline": "**Automobiles** is up 99% on record sales.",
        "sector_read": "Sales hit a record [c1].",
        "fund_lines": {"INF1": "Carries demand.", "INF2": "Banks dominate."},
        "closing": "Done.",
    }
    out, _ = _compose(monkeypatch, parsed)
    assert "99" not in out.display


def test_structured_when_llm_returns_nothing(monkeypatch):
    out, _ = _compose(monkeypatch, {})
    assert out.answer_trace["mode"] == "structured"
    assert out.bullets and "Automobiles" in out.display
    assert "Economic Times" not in out.display


# ---------------------------------------------------------------- brief detectors


def test_detect_sector_ignores_driver_words_and_non_sectors():
    assert _detect_sector("Which mutual funds are most affected if crude oil prices keep rising?")[0] == ""
    assert _detect_sector("The market took a hit today")[0] == ""  # 'hit' is not IT
    assert _detect_sector("How is the automobile sector doing?")[0] in ("Automobiles", "Auto Components", "Auto")


def test_detect_drivers():
    drivers, direction = _detect_drivers("What if crude oil prices keep rising?")
    assert "crude_oil" in drivers
    assert direction in ("up", "rise", "higher", "")
