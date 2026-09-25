"""Rebuild aggregated_sectors from allisin_sectors_with_holdings.json.

Output columns: sector, fund_count only.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "fund_holdings_aggregate" / "allisin_sectors_with_holdings.json"
OUT_CSV = ROOT / "data" / "fund_holdings_aggregate" / "aggregated_sectors.csv"
OUT_JSON = ROOT / "data" / "fund_holdings_aggregate" / "aggregated_sectors.json"


def main() -> None:
    print(f"Loading {SRC} ...")
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    counts: Counter[str] = Counter()
    funds = 0
    for isin, entry in doc.items():
        if isin == "_meta" or not isinstance(entry, dict):
            continue
        if entry.get("error"):
            continue
        sectors = entry.get("sectors") or {}
        if not isinstance(sectors, dict):
            continue
        funds += 1
        seen: set[str] = set()
        for name, pct in sectors.items():
            sector = str(name).strip()
            if not sector or sector in seen:
                continue
            try:
                if float(pct) <= 0:
                    continue
            except (TypeError, ValueError):
                continue
            seen.add(sector)
            counts[sector] += 1

    rows = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sector", "fund_count"])
        for sector, fund_count in rows:
            writer.writerow([sector, fund_count])

    mapping = {sector: fund_count for sector, fund_count in rows}
    OUT_JSON.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Funds used: {funds}")
    print(f"Sectors: {len(rows)}")
    print(f"Written: {OUT_CSV}")
    print(f"Written: {OUT_JSON}")


if __name__ == "__main__":
    main()
