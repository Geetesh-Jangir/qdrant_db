"""Rebuild aggregated holdings from the rating-patch JSONL.

Output: instrument_name, industry, fund_count only.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "fund_holdings_aggregate" / "allisin_sectors_with_holdings.rating_patch.jsonl"
OUT_CSV = ROOT / "data" / "fund_holdings_aggregate" / "aggregated_holdings.csv"
OUT_MAP = ROOT / "data" / "fund_holdings_aggregate" / "aggregated_holdings_map.json"

_SKIP_NAME_FRAGMENTS = (
    "treps",
    "triparty repo",
    "reverse repo",
    "net receivable",
    "net current asset",
    "cash and cash",
    "cash & cash",
)


def main() -> None:
    print(f"Reading {SRC} ...", flush=True)
    latest: dict[str, dict] = {}
    lines = 0
    with SRC.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            lines += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            isin = row.get("isin")
            holdings = row.get("holdings")
            if not isin or not isinstance(holdings, dict):
                continue
            latest[isin] = holdings

    fund_count: Counter[str] = Counter()
    industry_votes: dict[str, Counter[str]] = defaultdict(Counter)
    display: dict[str, str] = {}

    for holdings in latest.values():
        seen: set[str] = set()
        for name, meta in holdings.items():
            instrument = str(name).strip()
            lowered = instrument.lower()
            if not instrument or instrument in seen:
                continue
            if any(fragment in lowered for fragment in _SKIP_NAME_FRAGMENTS):
                continue
            if not isinstance(meta, dict):
                continue
            industry = str(meta.get("industry") or "").strip()
            if not industry:
                continue
            seen.add(instrument)
            fund_count[instrument] += 1
            if instrument not in display:
                display[instrument] = instrument
            industry_votes[instrument][industry] += 1

    rows = []
    for name, count in fund_count.items():
        votes = industry_votes.get(name)
        industry = votes.most_common(1)[0][0] if votes else ""
        rows.append((display[name], industry, count))
    rows.sort(key=lambda item: (-item[2], item[0].lower()))

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["instrument_name", "industry", "fund_count"])
        writer.writerows(rows)

    mapping = {
        name: {"industry": industry, "fund_count": count} for name, industry, count in rows
    }
    OUT_MAP.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"JSONL rows read: {lines}", flush=True)
    print(f"Unique ISINs: {len(latest)}", flush=True)
    print(f"Holdings: {len(rows)}", flush=True)
    print(f"Written: {OUT_CSV}", flush=True)
    print(f"Written: {OUT_MAP}", flush=True)


if __name__ == "__main__":
    main()
