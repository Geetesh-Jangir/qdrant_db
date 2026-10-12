"""O(1) macro driver → sector impact rules (see macro_sector_impact.json)."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from lib.nse_sector_indices import sector_yfinance_ticker
from news_pipeline.config import SECTOR_QUERIES, repo_root

DEFAULT_JSON = "data/fund_holdings_aggregate/macro_sector_impact.json"
NIFTY_50 = "Nifty 50"

_DRIVER_ALIASES: dict[str, str] = {
    "rbi": "rbi_repo",
    "repo": "rbi_repo",
    "rates": "rbi_repo",
    "monetary_policy": "rbi_repo",
    "liquidity": "rbi_liquidity",
    "crude": "crude_oil",
    "oil": "crude_oil",
    "brent": "crude_oil",
    "petroleum": "crude_oil",
    "rupee": "usd_inr",
    "usd_inr": "usd_inr",
    "forex": "usd_inr",
    "currency": "usd_inr",
    "gsec": "gsec_10y",
    "bond_yield": "gsec_10y",
    "10y": "gsec_10y",
    "cpi": "cpi_inflation",
    "inflation": "cpi_inflation",
    "wpi": "cpi_inflation",
    "fed": "us_fed_yields",
    "treasury": "us_fed_yields",
    "fpi": "fpi_flows",
    "fii": "fpi_flows",
    "gdp": "growth_indicators",
    "pmi": "growth_indicators",
    "iip": "growth_indicators",
    "monsoon": "monsoon",
    "rainfall": "monsoon",
    "food_inflation": "food_inflation",
    "capex": "govt_capex",
    "budget": "govt_capex",
    "fiscal": "govt_capex",
}

_DIRECTION_ALIASES: dict[str, str] = {
    "cut": "ease",
    "hike": "tighten",
    "ease": "ease",
    "easing": "ease",
    "tighten": "tighten",
    "tightening": "tighten",
    "up": "up",
    "rise": "up",
    "rises": "up",
    "higher": "up",
    "surge": "up",
    "down": "down",
    "fall": "down",
    "falls": "down",
    "lower": "down",
    "weaken": "weaken",
    "depreciate": "weaken",
    "strengthen": "strengthen",
    "appreciate": "strengthen",
    "inflow": "inflow",
    "outflow": "outflow",
    "accelerate": "accelerate",
    "weak": "weak",
    "good": "good",
    "poor": "poor",
    "deficient": "poor",
    "higher_capex": "higher",
    "lower_capex": "lower",
}


@lru_cache(maxsize=1)
def _document(path: str | None = None) -> dict[str, Any]:
    rel = path or DEFAULT_JSON
    full = repo_root() / rel
    with full.open(encoding="utf-8") as handle:
        return json.load(handle)


def clear_macro_impact_cache() -> None:
    _document.cache_clear()


def normalize_driver(driver: str) -> str:
    raw = re.sub(r"[^a-z0-9_]+", "_", (driver or "").strip().lower()).strip("_")
    return _DRIVER_ALIASES.get(raw, raw)


def normalize_direction(direction: str) -> str:
    raw = (direction or "").strip().lower()
    return _DIRECTION_ALIASES.get(raw, raw)


def list_macro_drivers() -> list[str]:
    by_macro = _document().get("by_macro") or {}
    return sorted(by_macro.keys())


def _valid_sectors() -> set[str]:
    return set(SECTOR_QUERIES.keys()) | {NIFTY_50}


def macro_impact_entry(
    driver: str,
    *,
    direction: str | None = None,
    path: str | None = None,
) -> dict[str, Any] | None:
    """Return macro driver metadata and sector rows; enrich with index tickers."""
    key = normalize_driver(driver)
    doc = _document(path)
    by_macro = doc.get("by_macro") or {}
    row = by_macro.get(key)
    if not row:
        return None

    dir_norm = normalize_direction(direction) if direction else ""
    sectors_out: list[dict[str, Any]] = []
    for item in row.get("sectors") or []:
        if not isinstance(item, dict):
            continue
        sector = str(item.get("sector") or "").strip()
        if sector not in _valid_sectors():
            continue
        enriched = dict(item)
        if sector == NIFTY_50:
            from lib.nse_sector_indices import benchmark_entry, NIFTY_50_KEY

            bench = benchmark_entry(NIFTY_50_KEY, path=None)
            enriched["index_ticker"] = (bench or {}).get("yfinance_ticker")
        else:
            enriched["index_ticker"] = sector_yfinance_ticker(sector)
        pos_when = str(item.get("positive_when") or "").strip()
        neg_when = str(item.get("negative_when") or "").strip()
        impact_type = str(item.get("impact_type") or "mixed").strip()
        expected: str | None = None
        if dir_norm:
            if dir_norm == pos_when:
                expected = "positive"
            elif dir_norm == neg_when:
                expected = "negative"
            elif impact_type == "mixed":
                expected = "mixed"
        enriched["expected_sign"] = expected
        sectors_out.append(enriched)

    return {
        "macro_name": key,
        "display_name": row.get("display_name") or key,
        "search_keywords": list(row.get("search_keywords") or []),
        "directions": list(row.get("directions") or []),
        "direction_requested": dir_norm or None,
        "sectors": sectors_out,
    }


def run_macro_sector_impact(
    *,
    driver: str,
    direction: str = "",
) -> dict[str, Any]:
    import time

    started = time.perf_counter()
    entry = macro_impact_entry(driver, direction=direction or None)
    elapsed = (time.perf_counter() - started) * 1000
    if not entry:
        return {
            "ok": False,
            "data": None,
            "error": f"Unknown macro driver: {driver}",
            "elapsed_ms": elapsed,
        }
    return {"ok": True, "data": entry, "error": "", "elapsed_ms": elapsed}
