from news_rag.insight.memory.state import ENTITY_TTL_TURNS, empty_state, expire_stale_entities, push_fund


def test_entity_stack_drops_entries_older_than_ttl():
    state = empty_state("conv-1")
    state["turn_count"] = 10
    push_fund(state, {"name": "Old Fund", "id": "INFOLD"}, period="1 month", facts=["screen"], turn=3)
    push_fund(state, {"name": "Fresh Fund", "id": "INFFRESH"}, period="1 month", facts=["screen"], turn=9)
    expire_stale_entities(state, 10)
    names = [row.get("name") for row in state.get("entity_stack") or []]
    assert "Old Fund" not in names
    assert "Fresh Fund" in names


def test_list_cursor_cleared_when_stale():
    state = empty_state("conv-2")
    state["turn_count"] = 10
    state["list_cursor"] = {"rows": [{"name": "A"}], "filters": {}, "turn": 2}
    expire_stale_entities(state, 10)
    assert state.get("list_cursor") is None


def test_catalog_subjects_expire_investor_subjects_kept():
    state = empty_state("conv-3")
    state["turn_count"] = 10
    frame = state["frame"]
    frame["subjects"] = [{"name": "Catalog Fund", "id": "", "role": "primary"}]
    frame["subjects_turn"] = 3
    frame["subject_kind"] = "single_fund"
    frame["investor_subjects"] = [{"name": "Kotak Contra Fund", "category": "contra"}]
    expire_stale_entities(state, 10)
    assert frame.get("subjects") == []
    assert frame.get("investor_subjects")


def test_entity_ttl_constant_is_reasonable():
    assert 2 <= ENTITY_TTL_TURNS <= 8
