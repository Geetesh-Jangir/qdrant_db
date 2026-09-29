"""Historical Gold and Silver price service (INR converted with metrics)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Constants
TROY_OUNCE_TO_GRAMS = 31.1034768
DEFAULT_START_DATE = "2024-01-01"

_ROOT = Path(__file__).resolve().parents[1]
_DATA_DIR = _ROOT / "data"
_METALS_CSV = _DATA_DIR / "metals_prices.csv"
_METALS_JSON = _DATA_DIR / "metals_prices.json"


def _ensure_data_dir() -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR


def fetch_metals_prices(
    start: str = DEFAULT_START_DATE,
    end: str | None = None,
) -> pd.DataFrame:
    """Fetch Gold (GC=F), Silver (SI=F), and USD/INR from Yahoo Finance,
    align dates, convert to standard Indian units (₹/10g gold, ₹/kg silver),
    and compute rolling metrics.
    """
    tickers = ["GC=F", "SI=F", "USDINR=X"]
    data = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False,
    )

    if data.empty:
        raise ValueError("No data returned from Yahoo Finance for tickers: " + ", ".join(tickers))

    close = data["Close"].copy()

    # Forward-fill & backward-fill any trading calendar or timezone differences
    close = close.ffill().bfill()

    close = close.rename(
        columns={
            "GC=F": "gold_usd_oz",
            "SI=F": "silver_usd_oz",
            "USDINR=X": "usd_inr",
        }
    )

    # Convert USD/oz -> INR/oz
    close["gold_inr_oz"] = close["gold_usd_oz"] * close["usd_inr"]
    close["silver_inr_oz"] = close["silver_usd_oz"] * close["usd_inr"]

    # Convert INR/oz -> INR/gram
    close["gold_inr_gram"] = close["gold_inr_oz"] / TROY_OUNCE_TO_GRAMS
    close["silver_inr_gram"] = close["silver_inr_oz"] / TROY_OUNCE_TO_GRAMS

    # Common Indian Units
    close["gold_inr_10g"] = close["gold_inr_gram"] * 10
    close["silver_inr_kg"] = close["silver_inr_gram"] * 1000

    # Percentage changes
    close["gold_1d_pct"] = close["gold_inr_10g"].pct_change() * 100
    close["silver_1d_pct"] = close["silver_inr_kg"].pct_change() * 100
    close["usd_inr_1d_pct"] = close["usd_inr"].pct_change() * 100

    close["gold_7d_pct"] = close["gold_inr_10g"].pct_change(7) * 100
    close["silver_7d_pct"] = close["silver_inr_kg"].pct_change(7) * 100

    close["gold_30d_pct"] = close["gold_inr_10g"].pct_change(30) * 100
    close["silver_30d_pct"] = close["silver_inr_kg"].pct_change(30) * 100

    # Moving Averages
    close["gold_20d_ma"] = close["gold_inr_10g"].rolling(window=20).mean()
    close["silver_20d_ma"] = close["silver_inr_kg"].rolling(window=20).mean()

    # Format Date
    close = close.reset_index()
    close["date"] = close["Date"].dt.strftime("%Y-%m-%d")
    close = close.drop(columns=["Date"])

    # Logical column ordering
    columns = [
        "date",
        "gold_inr_10g",
        "silver_inr_kg",
        "gold_inr_gram",
        "silver_inr_gram",
        "gold_usd_oz",
        "silver_usd_oz",
        "usd_inr",
        "gold_1d_pct",
        "silver_1d_pct",
        "usd_inr_1d_pct",
        "gold_7d_pct",
        "silver_7d_pct",
        "gold_30d_pct",
        "silver_30d_pct",
        "gold_20d_ma",
        "silver_20d_ma",
    ]

    return close[[c for c in columns if c in close.columns]]


def save_metals_history(
    df: pd.DataFrame,
    csv_path: Path = _METALS_CSV,
    json_path: Path = _METALS_JSON,
) -> tuple[Path, Path]:
    """Save metals historical dataframe to CSV and JSON in data/."""
    _ensure_data_dir()
    df.to_csv(csv_path, index=False)

    records = df.to_dict(orient="records")
    latest = records[-1] if records else {}

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "start_date": records[0]["date"] if records else None,
        "end_date": latest.get("date"),
        "latest": latest,
        "records": records,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return csv_path, json_path


def load_metals_history() -> dict[str, Any] | None:
    """Load cached metals history from JSON file."""
    if not _METALS_JSON.is_file():
        return None
    try:
        with open(_METALS_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.warning("Failed to load metals history JSON: %s", exc)
        return None


def get_latest_metals_prices() -> dict[str, Any]:
    """Get the most recent Gold and Silver prices in INR with 1d/7d changes."""
    data = load_metals_history()
    if not data or not data.get("latest"):
        df = fetch_metals_prices()
        save_metals_history(df)
        data = load_metals_history()

    return (data or {}).get("latest", {})


def get_metals_history(days: int = 30) -> list[dict[str, Any]]:
    """Get recent N days of historical metals data."""
    data = load_metals_history()
    if not data or not data.get("records"):
        df = fetch_metals_prices()
        save_metals_history(df)
        data = load_metals_history()

    records = (data or {}).get("records", [])
    if days > 0:
        return records[-days:]
    return records
