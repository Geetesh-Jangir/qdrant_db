"""Unit tests for sector cluster detection."""

from __future__ import annotations

from new.sector_clusters import (
    MATERIAL_IMPACT_PCT,
    MATERIAL_RANK1_IMPACT_PCT,
    canonical_sector_key,
    detect_sector_clusters,
)


def _row(name: str, industry: str, impact: float) -> dict:
    return {
        "instrument_name": name,
        "industry": industry,
        "impact_1w_pct": impact,
        "percentage": 5.0,
    }


def test_canonical_sector_banks():
    assert canonical_sector_key("Banks") == "Banks"


def test_banking_triple_gainer_cluster():
    gainers = [
        _row("PNB", "Banks", 0.05),
        _row("SBI", "Banks", 0.04),
        _row("HDFC Bank", "Banks", 0.03),
        _row("Reliance", "Petroleum Products", 0.02),
    ]
    clusters, _ = detect_sector_clusters(gainers, [])
    bank = [c for c in clusters if c.sector_key == "Banks" and c.side == "up"]
    assert len(bank) == 1
    assert bank[0].trigger == "pair"
    assert len(bank[0].holdings) == 3


def test_it_pair_loser_cluster():
    losers = [
        _row("Tech Mahindra", "It - Software", -0.04),
        _row("Infosys", "It - Software", -0.03),
    ]
    clusters, _ = detect_sector_clusters([], losers)
    it = [c for c in clusters if c.side == "down"]
    assert len(it) == 1
    assert it[0].sector_key == "It - Software"


def test_banks_split_by_side():
    gainers = [_row("SBI", "Banks", 0.05), _row("PNB", "Banks", 0.04)]
    losers = [_row("Axis Bank", "Banks", -0.04), _row("Kotak Bank", "Banks", -0.03)]
    clusters, _ = detect_sector_clusters(gainers, losers)
    assert len(clusters) == 2
    sides = {c.side for c in clusters if c.sector_key == "Banks"}
    assert sides == {"up", "down"}


def test_material_single_rank1():
    gainers = [
        _row("SBI", "Banks", MATERIAL_RANK1_IMPACT_PCT),
        _row("Reliance", "Petroleum Products", 0.01),
    ]
    clusters, _ = detect_sector_clusters(gainers, [])
    bank = [c for c in clusters if c.sector_key == "Banks"]
    assert len(bank) == 1
    assert bank[0].trigger == "material_single"


def test_material_single_large_impact():
    gainers = [
        _row("Reliance", "Petroleum Products", 0.02),
        _row("SBI", "Banks", MATERIAL_IMPACT_PCT + 0.01),
    ]
    clusters, _ = detect_sector_clusters(gainers, [])
    bank = [c for c in clusters if c.sector_key == "Banks"]
    assert len(bank) == 1
    assert bank[0].trigger == "material_single"