from ai_insight.common.sector_indices import load_catalog


def test_one_card_per_index_display():
    specs = load_catalog(include_weak=False)
    by_display: dict[str, int] = {}
    for spec in specs:
        by_display[spec.display] = by_display.get(spec.display, 0) + 1
    assert by_display.get("Nifty Infrastructure", 0) == 1
    assert by_display.get("Nifty IT", 0) == 1
    it = next(s for s in specs if s.display == "Nifty IT")
    assert "It - Software" in it.news_sectors