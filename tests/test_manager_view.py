from news_rag.insight.manager_view import (
    build_roster_note,
    enrich_manager_payload,
    infer_manager_roster_focus,
)


def test_infer_roster_focus_current_vs_past():
    assert infer_manager_roster_focus("current fund manager of INF174KA1C68") == "current"
    assert infer_manager_roster_focus("who was the former manager of this fund") == "past"
    assert infer_manager_roster_focus("fund managers of hdfc large cap") == "current"
    assert infer_manager_roster_focus("tell me about its fund manager") == "current"
    assert infer_manager_roster_focus("current and past managers of this fund") == "all"


def test_default_manager_answer_drops_former_managers():
    mgr = {
        "fund_name": "Sample Fund",
        "current": [{"name": "A"}],
        "past": [{"name": "B"}],
    }
    out = enrich_manager_payload(mgr, "tell me about its fund manager")
    assert out["roster_focus"] == "current"
    assert out["display_past"] == []
    assert out["past"] == []
    assert out["display_current"][0]["name"] == "A"


def test_enrich_filters_past_only():
    mgr = {
        "fund_name": "Sample Fund",
        "current": [{"name": "A"}],
        "past": [{"name": "B"}],
    }
    out = enrich_manager_payload(mgr, "previous fund manager of sample fund")
    assert out["roster_focus"] == "past"
    assert out["display_current"] == []
    assert len(out["display_past"]) == 1


def test_roster_note_when_no_past_managers():
    note = build_roster_note(
        "current",
        [{"name": "A", "other_schemes": [{"scheme_name": "X Fund", "from_date": "2024-06-07"}]}],
        [],
        {"inception_date": "2024-06-07"},
        "X Fund",
    )
    assert "No former managers" in note
    assert "2024-06-07" in note
