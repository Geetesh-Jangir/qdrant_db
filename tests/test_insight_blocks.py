"""Unit tests for insight compute blocks (no network)."""

from news_rag.insight.blocks.compute import compute_findings
from news_rag.insight.brief import QuestionBrief, SubAsk
from news_rag.insight.gather import EvidenceItem, EvidenceSet, LedgerEntry


def _sample_evidence() -> EvidenceSet:
    ev = EvidenceSet(
        ledger=[
            LedgerEntry("exposure_link", "satisfied"),
            LedgerEntry("fund_composition", "satisfied"),
            LedgerEntry("return_series", "satisfied"),
            LedgerEntry("news_drivers", "satisfied"),
            LedgerEntry("benchmark", "satisfied"),
        ]
    )
    ev.items.append(
        EvidenceItem(
            facet="exposure_link",
            tool="sector_funds",
            entity_key="Automobiles",
            data={
                "rankings": [
                    {
                        "isin": "INF000000001",
                        "fund_name": "Test Consumption Fund",
                        "sector_weight_pct": 18.0,
                        "sector_breakdown": {"Automobiles": 18.0},
                    }
                ]
            },
        )
    )
    ev.items.append(
        EvidenceItem(
            facet="fund_composition",
            tool="fund_composition",
            entity_key="INF000000001",
            data={
                "isin": "INF000000001",
                "fund_name": "Test Consumption Fund",
                "sectors": [
                    {"sector": "Automobiles", "percentage": 18.0},
                    {"sector": "Banks", "percentage": 22.0},
                    {"sector": "FMCG", "percentage": 12.0},
                ],
            },
        )
    )
    ev.items.append(
        EvidenceItem(
            facet="return_series",
            tool="fund_return_series",
            entity_key="INF000000001",
            data={"isin": "INF000000001", "window_pct": -4.5, "monthly": [{"month": "2026-09", "return_pct": -1.2}]},
        )
    )
    ev.items.append(
        EvidenceItem(
            facet="news_drivers",
            tool="sector_news_signal",
            entity_key="Automobiles",
            data={"direction": "positive", "themes": ["GST cuts boost demand"]},
        )
    )
    ev.items.append(
        EvidenceItem(
            facet="benchmark",
            tool="index_series",
            entity_key="Automobiles",
            data={"return_pct": 2.0, "benchmark_label": "Nifty Auto"},
        )
    )
    return ev


def test_compute_findings_other_sectors_and_divergence():
    brief = QuestionBrief(
        goal="auto funds",
        sub_asks=[SubAsk("1", "funds", "list")],
        subjects=[{"role": "sector", "canonical": "Automobiles"}],
        evidence_needs=["exposure_link", "fund_composition", "return_series", "news_drivers", "benchmark"],
    )
    findings = compute_findings(brief, _sample_evidence())
    assert findings.funds
    f = findings.funds[0]
    assert f.other_top_sectors
    assert f.divergence is True
    assert f.relative_to_benchmark_pct is not None
    assert "Test_Consumption_Fund_exposure=18" in findings.evidence_text
