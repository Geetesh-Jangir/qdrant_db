"""Config variants, sector excludes, and the retrieval gate. No network."""

from news_pipeline.config import MACRO_ENTITIES, MACRO_QUERY_VARIANTS, SECTOR_QUERIES
from news_pipeline.sources.matching import matches_entity
from ai_insight.retrieval import DIGEST_MIN_IMPACT, DIGEST_MIN_RELEVANCE, digest_filter


def test_every_macro_entity_has_a_variant_or_is_gold_or_gst():
    names = {row["name"] for row in MACRO_ENTITIES}
    assert len(names) == len(MACRO_ENTITIES)
    missing = names - set(MACRO_QUERY_VARIANTS)
    assert missing == set()


def test_sector_exclude_drops_nbfc_from_banks():
    banks = {
        "type": "sector",
        "keywords": list(SECTOR_QUERIES["Banks"].keywords),
        "exclude_keywords": list(SECTOR_QUERIES["Banks"].exclude),
        "min_keyword_hits": SECTOR_QUERIES["Banks"].min_hits,
    }
    assert matches_entity("RBI flags bank credit growth", "", banks)
    assert not matches_entity("NBFC bank lending slows", "", banks)


def test_digest_filter_uses_stricter_scores():
    filt = digest_filter(entity_names=["Macro - Nifty 50"], published_from="2026-11-01T00:00:00Z")
    blob = str(filt)
    assert str(DIGEST_MIN_RELEVANCE) in blob
    assert str(DIGEST_MIN_IMPACT) in blob
