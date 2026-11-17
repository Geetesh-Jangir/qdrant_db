"""Build stock_multi_query_sector.xlsx for top-N holdings without rewriting curated rows."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from news_pipeline.sources.stock_multi_query import MAX_STOCK_UNIVERSE, multi_query_for
from news_pipeline.sources.universe import canonical_key

XLSX = ROOT / "data/fund_holdings_aggregate/stock_multi_query_sector.xlsx"
CSV_OUT = ROOT / "data/fund_holdings_aggregate/stock_multi_query_sector.csv"
CSV = ROOT / "data/fund_holdings_aggregate/aggregated_holdings.csv"


def load_top_holdings(limit: int) -> list[dict]:
    grouped: dict[str, dict] = {}
    with CSV.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            raw_name = (row.get("instrument_name") or "").strip()
            if not raw_name:
                continue
            key = canonical_key(raw_name)
            if not key:
                continue
            fund_count = int(float(row.get("fund_count") or 0))
            industry = (row.get("industry") or "").strip()
            existing = grouped.get(key)
            if existing is None:
                grouped[key] = {
                    "name": raw_name,
                    "industry": industry,
                    "fund_count": fund_count,
                }
                continue
            if fund_count > existing["fund_count"]:
                existing["name"] = raw_name
                existing["fund_count"] = fund_count
            if not existing.get("industry") and industry:
                existing["industry"] = industry

    return sorted(
        grouped.values(),
        key=lambda item: (-item["fund_count"], item["name"].lower()),
    )[:limit]


def main() -> None:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else MAX_STOCK_UNIVERSE
    limit = min(limit, MAX_STOCK_UNIVERSE)
    curated = pd.read_excel(XLSX)
    expected = ("Stock Name", "Multi-Query", "Sector")
    if tuple(curated.columns) != expected:
        raise SystemExit(f"unexpected columns: {tuple(curated.columns)}")

    by_key: dict[str, dict[str, str]] = {}
    for _, row in curated.iterrows():
        key = canonical_key(str(row["Stock Name"]))
        by_key[key] = {
            "Stock Name": str(row["Stock Name"]),
            "Multi-Query": str(row["Multi-Query"]),
            "Sector": str(row["Sector"]),
        }

    top = load_top_holdings(limit)
    out_rows: list[dict[str, str]] = []
    added = 0
    for item in top:
        key = canonical_key(item["name"])
        kept = by_key.get(key)
        if kept is not None:
            out_rows.append(dict(kept))
            continue
        added += 1
        out_rows.append(
            {
                "Stock Name": item["name"],
                "Multi-Query": multi_query_for(item["name"]),
                "Sector": item.get("industry") or "",
            }
        )

    if len(out_rows) != limit:
        raise SystemExit(f"expected {limit} rows, got {len(out_rows)}")
    frame = pd.DataFrame(out_rows)
    frame.to_excel(XLSX, index=False)
    frame.to_csv(CSV_OUT, index=False, encoding="utf-8")
    print(f"wrote {len(out_rows)} rows to {XLSX.name} and {CSV_OUT.name} ({len(by_key)} curated keys, {added} new)")


if __name__ == "__main__":
    main()