"""Check that git-tracked data files exist on the server (run after git pull)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Required for sector screens, fund catalog, metals tools, and stock-name resolution (BHEL, etc.).
REQUIRED = [
    "data/fund_holdings_aggregate/sector_to_isin_weights.json",
    "data/fund_holdings_aggregate/regular-growth-by-amc.md",
    "data/fund_holdings_aggregate/aggregated_holdings_map.json",
    "data/metals_prices.json",
    "data/direct_plan_growth_isins.txt",
]

# Improves sector breakdown and legacy paths; stock holder scans use live RupeeStop API if absent.
OPTIONAL = [
    "data/fund_holdings_aggregate/aggregated_holdings.csv",
    "data/fund_holdings_aggregate/sector_isin_percentages.json",
    "data/fund_holdings_aggregate/portfolio_news_scope.json",
    "data/fund_holdings_aggregate/portfolio_allisin_holdings.json",
    "data/fund_holdings_aggregate/allisin_sectors_with_holdings.json",
    "data/fund_name_embeddings.json",
]


def main() -> int:
    missing: list[str] = []
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            missing.append(rel)
    if missing:
        print("MISSING required files (git pull the deploy branch?):")
        for m in missing:
            print(f"  - {m}")
        print("See data/DEPLOY_DATA.md for what must be in the repo.")
        return 1
    print("OK: required RAG deploy data present.")
    for rel in OPTIONAL:
        path = ROOT / rel
        tag = "ok" if path.is_file() else "skip"
        print(f"  [{tag}] {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
