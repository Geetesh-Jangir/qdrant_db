from ai_insight.market_driver_digest.prompt import assemble_market_body, normalize_market_draft
from ai_insight.market_driver_digest.schema import DRAFT_SCHEMA
import jsonschema


def test_normalize_maps_legacy_investor_meaning():
    raw = {
        "headline": "Nifty -0.6% today — crude, yields",
        "market_snapshot": "Markets closed lower.",
        "what_happened": "Nifty slipped.",
        "why": "Oil stayed firm.",
        "impacted": "Energy names in focus.",
        "investor_meaning": "Volatility may stay elevated.",
        "what_to_watch": "RBI meeting.",
        "cited_cluster_ids": [],
        "confidence": "medium",
    }
    norm = normalize_market_draft(raw)
    assert norm["investor_relevance"] == "Volatility may stay elevated."
    assert norm["why_may_have_happened"] == "Oil stayed firm."
    jsonschema.Draft202012Validator(DRAFT_SCHEMA).validate(norm)


def test_assemble_market_body_is_one_paragraph():
    body = assemble_market_body(
        {
            "market_snapshot": "Nifty edged up.",
            "what_happened": "Banks led.",
            "why_may_have_happened": "Flows improved.",
            "impacted_how": "",
            "investor_relevance": "",
            "what_to_watch": "",
        }
    )
    assert "\n" not in body
    assert body == "Nifty edged up. Banks led. Flows improved."


def test_assemble_strips_leaked_markup_tags():
    body = assemble_market_body(
        {
            "market_snapshot": "Up today.",
            "what_happened": "Banks strong.</why_may_have_happened>",
            "why_may_have_happened": "Credit growth.",
            "impacted_how": "",
            "investor_relevance": "",
            "what_to_watch": "",
        }
    )
    assert "</why" not in body
    assert "Banks strong." in body