"""Deferred: top-N funds by stock holding exposure (not sector_to_isin_weights).

Use per-fund `get_fund_detail` / allisin holdings for named-fund queries.
Market-wide stock discovery will need a holdings→ISIN inverted index built from
allisin_sectors_with_holdings.json (same source as sector_to_isin_weights.json).
"""

from __future__ import annotations

# MVP: stock-channel discovery is intentionally not implemented.
