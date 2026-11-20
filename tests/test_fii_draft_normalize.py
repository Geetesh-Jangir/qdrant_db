import jsonschema

from ai_insight.fii_dii_flow_narrative.prompt import assemble_fii_body, compact_flow_facts, normalize_fii_draft
from ai_insight.fii_dii_flow_narrative.schema import DRAFT_SCHEMA


def test_v9_single_paragraph_schema():
    raw = {
        "headline": "FII bought ₹100 crore — risk on",
        "paragraph": "On the flow date FIIs were net buyers while the broader index was little changed, which shows buying did not lift the whole market.",
        "chosen_cluster_ids": ["c0"],
        "confidence": "medium",
        "no_clear_driver": False,
        "observations": [
            "FIIs were net buyers while DIIs net sold over the recent window, partially offsetting foreign inflows.",
            "Weekly sector returns diverged, with banks leading while IT lagged.",
        ],
    }
    norm = normalize_fii_draft(raw)
    jsonschema.Draft202012Validator(DRAFT_SCHEMA).validate(norm)
    body = assemble_fii_body(norm)
    assert "\n\n" not in body
    assert "net buyers" in body


def test_legacy_sections_fold_into_paragraph():
    raw = {
        "headline": "x",
        "what_happened": "FIIs bought.",
        "what_explains_it": "Crude eased.",
        "market_and_mf_impact": "Nifty flat.",
        "bottom_line": "Flows are one input.",
        "chosen_cluster_ids": [],
        "confidence": "low",
        "no_clear_driver": True,
    }
    norm = normalize_fii_draft(raw)
    assert "FIIs bought" in norm["paragraph"]
    assert "Crude eased" in norm["paragraph"]


def test_assemble_strips_markup_in_paragraph():
    body = assemble_fii_body({"paragraph": "FIIs bought.</why> Credit growth."})
    assert "</why" not in body
    assert "FIIs bought." in body


def test_compact_flow_facts_excludes_gross_and_bars():
    facts = {
        "trading_date": "2026-11-19",
        "fii_net_crore": 100.0,
        "fii_gross_buy_crore": 999.0,
        "fii_gross_sell_crore": 888.0,
        "bars": [{"date": "2026-11-19", "fii_net": 1}],
    }
    slim = compact_flow_facts(facts)
    assert "fii_gross_buy_crore" not in slim
    assert "bars" not in slim
    assert slim["fii_net_crore"] == 100.0


def test_compact_flow_facts_omits_full_sector_daily_blob():
    facts = {
        "datasets": {
            "fii_dii_daily": [],
            "sector_indices_7d": [{"display": "X", "daily": [1, 2, 3]}],
            "synthesis_hints": {},
        }
    }
    slim = compact_flow_facts(facts)
    assert "sector_indices_7d" not in slim["DATASETS"]
    assert "synthesis_hints" in slim["DATASETS"]


def test_compact_flow_facts_includes_datasets():
    facts = {
        "trading_date": "2026-11-19",
        "fii_net_crore": 100.0,
        "datasets": {"fii_dii_daily": [], "data_limitations": ["flow_lagged: x"]},
        "bars": [],
    }
    slim = compact_flow_facts(facts)
    assert "DATASETS" in slim
    assert slim["data_limitations"] == ["flow_lagged: x"]