#!/usr/bin/env python3
"""CLI script to fetch official IBJA Gold & Silver prices (30 days) from Snapdata and save to data/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root is on sys.path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from historical_data.metals_service import (
    fetch_snapdata_metals,
    format_metals_context_for_llm,
    save_metals_history,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch official IBJA Gold & Silver 30-day series from Snapdata and save to data/."
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=5,
        help="Number of recent records to preview in console (default: 5)",
    )

    args = parser.parse_args()

    print("Fetching 30-day series from Snapdata (Gold & Silver IBJA rates)...")
    try:
        df, raw_gold, raw_silver = fetch_snapdata_metals()
        csv_path, json_path = save_metals_history(df, raw_gold, raw_silver)

        print(f"\nSuccessfully stored {len(df)} daily trading records.")
        print(f"Date range: {df['date'].iloc[0]} to {df['date'].iloc[-1]}")
        print(f"Unified CSV: {csv_path}")
        print(f"JSON Cache:  {json_path}")
        print(f"Raw Gold CSV:   {_ROOT / 'data' / 'gold_30d.csv'}")
        print(f"Raw Silver CSV: {_ROOT / 'data' / 'silver_30d.csv'}")

        print(f"\nPreview (Last {args.preview} records):")
        cols_to_show = [
            c
            for c in [
                "date",
                "gold_24k_inr_10g",
                "gold_22k_inr_10g",
                "gold_18k_inr_10g",
                "silver_inr_kg",
                "gold_1d_pct",
                "silver_1d_pct",
            ]
            if c in df.columns
        ]
        print(df[cols_to_show].tail(args.preview).to_string(index=False))

        print("\nPre-computed LLM Context:")
        print("=" * 60)
        print(format_metals_context_for_llm(force_refresh=True))
        print("=" * 60)

    except Exception as exc:
        print(f"\nError fetching metals history: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
