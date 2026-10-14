"""Named-fund insight path must not be replaced by sector fund screens."""

from news_rag.insight.blocks.compute import compute_findings
from news_rag.insight.brief import QuestionBrief, validate_brief_plan
from news_rag.insight.gather import EvidenceItem, EvidenceSet
from news_rag.insight.registry import ensure_registry, pick_tool_for_facet


def test_named_fund_brief_strips_exposure_link_from_llm_extras():
    brief = QuestionBrief(
        goal="nippon",
        funds=["Nippon Large Cap Fund"],
        evidence_needs=[
            "fund_facts_nav",
            "exposure_link",
            "fund_composition",
            "return_series",
            "news_drivers",
        ],
    )
    needs = validate_brief_plan(brief, "whats happening with the nippon large cap fund?")
    assert "exposure_link" not in needs
    assert "relationship_trace" not in needs
    assert "fund_facts_nav" in needs
    assert "news_drivers" in needs


def test_news_drivers_prefers_fund_portfolio_for_named_fund():
    ensure_registry()
    ctx = {"fund_names": ["Nippon Large Cap Fund"], "sector_name": "", "drivers": []}
    assert pick_tool_for_facet("news_drivers", ctx).name == "fund_portfolio_news"
    assert pick_tool_for_facet("exposure_link", ctx) is None


def test_compute_uses_named_fund_not_sector_screen():
    ev = EvidenceSet()
    ev.items.append(
        EvidenceItem(
            facet="exposure_link",
            tool="sector_funds",
            entity_key="",
            data={
                "rankings": [
                    {"isin": "INF179KC1HF9", "fund_name": "Random IT Fund", "sector_weight_pct": 40},
                ]
            },
        )
    )
    ev.items.append(
        EvidenceItem(
            facet="fund_composition",
            tool="fund_composition",
            entity_key="INF204K01562",
            data={
                "isin": "INF204K01562",
                "fund_name": "Nippon Large Cap Fund",
                "sectors": [{"sector": "Banks", "percentage": 8.0}],
            },
        )
    )
    ev.items.append(
        EvidenceItem(
            facet="return_series",
            tool="fund_return_series",
            entity_key="INF204K01562",
            data={"isin": "INF204K01562", "window_pct": -1.38},
        )
    )
    brief = QuestionBrief(goal="g", funds=["Nippon Large Cap Fund"])
    findings = compute_findings(brief, ev)
    assert len(findings.funds) == 1
    assert findings.funds[0].isin == "INF204K01562"
    assert findings.funds[0].return_window_pct == -1.38
