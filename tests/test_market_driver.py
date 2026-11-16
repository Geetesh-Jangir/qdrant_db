"""Market driver wording, recap exclusion, and the numbers-only fallback."""

from ai_insight.common.clustering import Cluster
from ai_insight.market_driver_digest.rank import is_index_recap, move_phrase, move_size, pick_drivers


def _cluster(cid, names, title="t"):
    return Cluster(cid, title, [cid], title, cid, 2, 2, {}, [
        {"article": {"title": title, "url": cid, "scraped_text": title}, "entity": {"name": name, "impact": 2}}
        for name in names
    ])


def test_move_thresholds():
    assert move_size(0.1) == "small"
    assert move_size(0.6) == "moderate"
    assert move_size(1.4) == "large"
    assert move_phrase(0.1) == "stayed range-bound"
    assert move_phrase(0.6) == "edged up"
    assert move_phrase(-0.4) == "edged down"
    assert move_phrase(-1.2) == "fell sharply"
    assert move_phrase(1.2) == "rallied"


def test_secondary_is_a_different_entity_and_recaps_wait():
    crude = _cluster("c0", ["Macro - Crude Oil"])
    rupee = _cluster("c1", ["Macro - Rupee / USD"])
    recap = _cluster("c2", ["Macro - Nifty 50", "Macro - Sensex"])
    drivers = pick_drivers([recap, crude, rupee])
    assert not drivers.used_recap_only
    assert drivers.primary.cluster_id in {"c0", "c1"}
    assert drivers.secondary is not None
    assert is_index_recap(recap)
    only = pick_drivers([recap])
    assert only.used_recap_only
    assert only.primary.cluster_id == "c2"
