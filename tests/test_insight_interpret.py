from unittest.mock import patch

from news_rag.insight.brief import QuestionBrief, SubAsk
from news_rag.insight.findings import Findings, FundFinding, SectorFinding
from news_rag.insight.gather import EvidenceSet
from news_rag.insight.interpret import _dedupe_parenthetical_cites, compose_from_findings


def test_dedupe_repeated_citations():
    text = "FIIs sold (Economic Times, 10 Oct; Economic Times, 10 Oct) sharply."
    assert _dedupe_parenthetical_cites(text).count("Economic Times, 10 Oct") == 1


def test_render_citations_strips_outlets():
    from news_rag.insight.interpret import _render_citations

    text, n = _render_citations(
        "Sales rose [c1] per Economic Times reports.",
        {"c1": {"cite": "Economic Times, 10 Oct"}},
    )
    assert "Economic Times" not in text
    assert n == 1


def test_named_fund_why_uses_sector_drag_not_macro():
    brief = QuestionBrief(
        window_label="1 month",
        funds=["HDFC Large Cap Fund"],
        subjects=[{"role": "fund_scheme", "canonical": "HDFC Large Cap Fund"}],
    )
    findings = Findings(
        sector=SectorFinding(sector_label="sector", tone="negative", tone_reason="FII selling"),
        funds=[
            FundFinding(
                fund_name="HDFC Large Cap Fund",
                isin="INF1",
                return_window_pct=-3.6,
                drag_sectors=[
                    {
                        "sector": "Banks",
                        "weight_pct": 30.1,
                        "index_return_pct": -4.2,
                        "index_label": "Nifty Bank",
                        "same_direction": True,
                        "news": "Bank stocks fell after the rate move",
                        "holdings": [
                            {"name": "ICICI Bank", "weight_pct": 9.0, "return_pct": -3.1, "diverged": False, "news": ""}
                        ],
                    }
                ],
            )
        ],
            evidence_text="Banks -4.2 -3.6 30.1 30 9.0 9 -3.1",
    )
    out = compose_from_findings(
        "why is hdfc large cap down in the last one month?",
        brief,
        findings,
        EvidenceSet(),
    )
    assert "Banks" in out.display
    assert "Nifty Bank" in out.display
    assert "does not reach" not in out.display.lower()
    assert "moved the other way" not in out.display.lower()
    assert "3.1%" in out.display
    assert "What happened" in out.display
    assert "added to the sector move" in out.display
    assert "ICICI Bank" in out.display


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


@patch("news_rag.insight.interpret.llm_api_key_configured", return_value=False)
def test_market_sector_lists_in_display_without_funds(_mock_llm):
    q = "what is happening in the market and which sectors are going down?"
    brief = QuestionBrief(
        sub_asks=[
            SubAsk("1", "What is happening in the market right now", "describe", order=1),
            SubAsk("2", "Which sectors are going down", "list", order=2),
        ],
        window_label="1 week",
        direction="negative",
    )
    findings = Findings(
        sector=SectorFinding(
            sector_label="sector",
            news_direction="negative",
            tone="negative",
            tone_reason="FII selling and high crude hurt sentiment.",
            claims=[
                {
                    "id": "c1",
                    "text": "FIIs sold for eight weeks.",
                    "sentiment": "negative",
                    "cite": "Economic Times, 10 Oct",
                }
            ],
            sectors_negative=[
                {"name": "Steel", "reason": "input costs and weak demand"},
                {"name": "Oil & Gas Refining & Marketing", "reason": "crude spike"},
            ],
            sectors_positive=[{"name": "Banks", "reason": "rate cycle support"}],
        ),
        evidence_text="Steel Oil FII selling",
    )
    out = compose_from_findings(q, brief, findings, EvidenceSet())
    assert "Steel" in out.display
    assert "weighing on" in out.display.lower() or "under pressure" in out.display.lower()
    assert "no funds" not in out.display.lower()
    assert "steel" in out.closing_summary.lower()
