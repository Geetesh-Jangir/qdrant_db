from news_rag.insight.entity_candidates import candidates_block, entity_candidates


def test_sector_and_holding_candidates():
    memory = {"holdings_in_chat": [{"name": "Quant Small Cap Fund - Growth", "category": "small cap"}]}
    got = entity_candidates("how are banks doing in my small cap fund", memory)
    assert got["holdings"] == ["Quant Small Cap Fund - Growth"]
    assert got["sectors"]


def test_quant_question_includes_amc_catalog_note():
    got = entity_candidates("why is quant small cap fund falling")
    assert any("AMC token" in line and "Quant" in line for line in got.get("amc_notes") or [])


def test_no_candidates_for_plain_text():
    assert candidates_block("hello there how are you") == ""
