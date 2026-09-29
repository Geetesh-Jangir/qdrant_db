#!/usr/bin/env python3
"""CLI script to fetch historical Gold & Silver prices in INR and save to data/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root is on sys.path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from historical_data.metals_service import (
    fetch_metals_prices,
    save_metals_history,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch historical Gold, Silver, and USD/INR prices and save INR conversions to data/."
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2024-01-01",
        help="Start date in YYYY-MM-DD format (default: 2024-01-01)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End date in YYYY-MM-DD format (default: latest available)",
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=5,
        help="Number of recent records to preview in console (default: 5)",
    )

    args = parser.parse_args()

    print(f"Fetching Gold (GC=F), Silver (SI=F), and USDINR=X from {args.start} to {args.end or 'latest'}...")
    try:
        df = fetch_metals_prices(start=args.start, end=args.end)
        csv_path, json_path = save_metals_history(df)

        print(f"\nSuccessfully fetched {len(df)} daily trading records.")
        print(f"Data range: {df['date'].iloc[0]} to {df['date'].iloc[-1]}")
        print(f"\nSaved Files:")
        print(f"  - CSV:  {csv_path} ({csv_path.stat().st_size:,} bytes)")
        print(f"  - JSON: {json_path} ({json_path.stat().st_size:,} bytes)")

        if args.preview > 0:
            print(f"\n--- Latest {args.preview} Days (Indian Units) ---")
            preview_cols = [
                "date",
                "gold_inr_10g",
                "silver_inr_kg",
                "usd_inr",
                "gold_1d_pct",
                "silver_1d_pct",
            ]
            print(df[preview_cols].tail(args.preview).to_string(index=False))

            latest = df.iloc[-1]
            print("\n--- Current Spot Recap ---")
            print(f"  Gold (₹/10g):   ₹{latest['gold_inr_10g']:,.2f} ({latest['gold_1d_pct']:+.2f}%)")
            print(f"  Silver (₹/kg):  ₹{latest['silver_inr_kg']:,.2f} ({latest['silver_1d_pct']:+.2f}%)")
            print(f"  USD/INR:        ₹{latest['usd_inr']:.2f}")

    except Exception as exc:
        print(f"\nError fetching metals history: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
