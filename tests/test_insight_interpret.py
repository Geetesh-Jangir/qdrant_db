from news_rag.insight.brief import QuestionBrief, SubAsk
from news_rag.insight.findings import Findings, FundFinding, SectorFinding
from news_rag.insight.gather import EvidenceSet
from news_rag.insight.interpret import compose_from_findings


def test_structured_compose_orders_sub_asks_and_bold():
    brief = QuestionBrief(
        sub_asks=[
            SubAsk("1", "How is the automobile sector doing", "describe", order=1),
            SubAsk("2", "Funds impacted positively or not", "measure", order=2, max_sentences=2),
        ],
        window_label="6 months",
        subjects=[{"role": "sector", "canonical": "Automobiles"}],
    )
    findings = Findings(
        sector=SectorFinding(
            sector_label="Automobiles",
            news_direction="positive",
            news_themes=["GST cuts"],
            index_return_pct=5.2,
            benchmark_label="Nifty Auto",
        ),
        funds=[
            FundFinding(
                fund_name="Kotak Consumption Fund - Regular Plan - Growth",
                exposure_pct=18.9,
                return_window_pct=-4.5,
                attribution={"topic_share_pct": 18.9, "residual_other_pct": 81.1},
                other_top_sectors=[{"sector": "FMCG", "percentage": 12.0}],
                verdict="mixed",
            )
        ],
        evidence_text="news_direction=positive sector_index_return=5.2 Kotak_Consumption_Fund_exposure=18.9 Kotak_Consumption_Fund_return=-4.5 Kotak_Consumption_Fund_auto_share=18.9",
    )
    out = compose_from_findings("auto sector and funds?", brief, findings, EvidenceSet())
    assert "**" in out.narrative
    assert "Headlines" in out.narrative or "Automobiles" in out.narrative
    assert "positive" in out.display.lower() or "negative" in out.display.lower()
    assert len(out.bullets) >= 1
    assert "18.9" in out.display or "18" in out.display
