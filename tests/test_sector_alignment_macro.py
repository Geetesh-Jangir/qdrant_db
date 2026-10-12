"""Sector alignment classifier and macro impact map validity."""

from __future__ import annotations

import json

import pytest

from news_pipeline.config import SECTOR_QUERIES, repo_root
from news_rag.ask_plan import ALLOWED_PLANNER_TOOLS
from news_rag.macro_impact_map import (
    clear_macro_impact_cache,
    list_macro_drivers,
    macro_impact_entry,
    normalize_driver,
)
from news_rag.query_analyzer import PLANNER_SYSTEM
from news_rag.sector_alignment import (
    return_sign,
    signs_opposite,
)


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_macro_impact_cache()
    yield
    clear_macro_impact_cache()


def test_planner_lists_new_tools():
    assert "sector_holding_alignment" in ALLOWED_PLANNER_TOOLS
    assert "macro_sector_impact" in ALLOWED_PLANNER_TOOLS
    assert "sector_holding_alignment" in PLANNER_SYSTEM
    assert "macro_sector_impact" in PLANNER_SYSTEM


def test_return_sign_and_opposite():
    assert return_sign(1.2) == "up"
    assert return_sign(-0.5) == "down"
    assert return_sign(0.1) == "flat"
    assert return_sign(None) == "unknown"
    assert signs_opposite("up", "down")
    assert not signs_opposite("up", "flat")
    assert not signs_opposite("unknown", "down")


def test_macro_map_sectors_are_valid_labels():
    path = repo_root() / "data/fund_holdings_aggregate/macro_sector_impact.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    allowed = set(SECTOR_QUERIES) | {"Nifty 50"}
    for name, block in (doc.get("by_macro") or {}).items():
        for row in block.get("sectors") or []:
            sector = row.get("sector")
            assert sector in allowed, f"{name}: bad sector {sector}"


def test_macro_impact_o1_lookup():
    drivers = list_macro_drivers()
    assert "rbi_repo" in drivers
    assert "crude_oil" in drivers
    entry = macro_impact_entry("rates", direction="ease")
    assert entry is not None
    assert entry["macro_name"] == "rbi_repo"
    assert entry["direction_requested"] == "ease"
    banks = [s for s in entry["sectors"] if s["sector"] == "Banks"]
    assert banks and banks[0].get("index_ticker") == "^NSEBANK"


def test_normalize_driver_aliases():
    assert normalize_driver("oil") == "crude_oil"
    assert normalize_driver("FII") == "fpi_flows"
