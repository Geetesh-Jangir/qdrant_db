from news_rag.insight.evidence_pack import repair_investor_insight_prose
from news_rag.insight.fund_display import strip_grounding_holes
from news_rag.insight.grounding import investor_book_cores, strip_ungrounded_numbers
from news_rag.insight.pack_sanitize import sanitize_data_pack_for_composer


def _sample_book():
    return {
        "summary": {
            "invested_inr": 64997.0,
            "aum_inr": 65405.0,
            "gain_loss_inr": 409.0,
            "absolute_return_pct": 0.63,
            "portfolio_xirr_pct": 1.13,
        },
        "holdings": [
            {
                "scheme_name": "Kotak Contra Fund - Regular Plan - Growth",
                "scheme_category": "contra",
                "aum_inr": 12220.5373,
                "invested_inr": 12999.35,
                "gain_loss_inr": -778.81,
                "xirr_pct": -10.71,
                "absolute_return_pct": -5.99,
            },
            {
                "scheme_name": "Invesco India Large & Mid Cap Fund - Regular Plan - Growth",
                "scheme_category": "large & mid cap",
                "aum_inr": 26511.498,
                "invested_inr": 25998.7,
                "gain_loss_inr": 512.8,
                "xirr_pct": 3.59,
                "absolute_return_pct": 1.97,
            },
        ],
    }


def test_investor_book_cores_includes_rounded_allocation_pct():
    pack, _ = sanitize_data_pack_for_composer({"investor_portfolio": _sample_book()})
    inv = pack["investor_portfolio"]
    cores = investor_book_cores(inv)
    assert "41" in cores or "40.53" in cores or any(c.startswith("40") for c in cores)


def test_repair_fills_hollow_allocation_and_holding_bullets():
    pack, _ = sanitize_data_pack_for_composer({"investor_portfolio": _sample_book()})
    inv = pack["investor_portfolio"]
    raw = (
        "- **Kotak Contra Fund - Regular Plan - Growth** (contra): invested and now worth about, a loss of about.\n"
        "- Your AUM is spread across **large & mid cap (about 41%)**, **mid cap (about )**, based on ₹65,405 total AUM."
    )
    fixed = repair_investor_insight_prose(raw, inv)
    assert "worth about" not in fixed
    assert "mid cap (about )" not in fixed
    assert "₹12,999" in fixed or "12999" in fixed.replace(",", "")
    assert "41%" in fixed or "40" in fixed


def test_grounding_keeps_category_weight_in_prose():
    pack, _ = sanitize_data_pack_for_composer({"investor_portfolio": _sample_book()})
    inv = pack["investor_portfolio"]
    import json

    evidence = json.dumps({"DATA": pack}, ensure_ascii=False)
    from news_rag.insight.grounding import cores_in_text, derived_cores

    allowed = cores_in_text(evidence) | derived_cores(cores_in_text(evidence)) | investor_book_cores(inv)
    line = "Weight is about 41% in large & mid cap and 20% in mid cap."
    cleaned = strip_ungrounded_numbers(line, allowed)
    assert "41%" in cleaned
    assert "20%" in cleaned


def test_strip_grounding_holes_drops_empty_bullet():
    text = "- **Fund** (contra): invested and now worth about, a loss of about."
    assert strip_grounding_holes(text).strip() == ""
