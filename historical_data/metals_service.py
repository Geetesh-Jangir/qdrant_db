"""Historical Gold and Silver price service using Snapdata IBJA 30-day feeds.

Source feeds:
- Gold: https://snapdata.dev/api/v1/gold/in/series/30d.csv (IBJA 24K, 22K, 18K in INR/gram)
- Silver: https://snapdata.dev/api/v1/silver/in/series/30d.csv (IBJA Silver in INR/kg)

Optimized for ultra-fast in-memory retrieval and compact storage for LLM prompts.
"""

from __future__ import annotations

import io
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

# Constants & Endpoints
SNAPDATA_GOLD_URL = "https://snapdata.dev/api/v1/gold/in/series/30d.csv"
SNAPDATA_SILVER_URL = "https://snapdata.dev/api/v1/silver/in/series/30d.csv"
CACHE_TTL_SECONDS = 3600.0  # 1 hour in-memory cache

_ROOT = Path(__file__).resolve().parents[1]
_DATA_DIR = _ROOT / "data"
_GOLD_RAW_CSV = _DATA_DIR / "gold_30d.csv"
_SILVER_RAW_CSV = _DATA_DIR / "silver_30d.csv"
_METALS_CSV = _DATA_DIR / "metals_prices.csv"
_METALS_JSON = _DATA_DIR / "metals_prices.json"

# In-memory cache for sub-millisecond retrieval
_IN_MEMORY_CACHE: dict[str, Any] = {
    "cached_at": 0.0,
    "data": None,
    "llm_context": "",
    "latest_spot": {},
}


def _ensure_data_dir() -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DATA_DIR


def fetch_snapdata_metals() -> tuple[pd.DataFrame, str, str]:
    """Download the 30-day Gold and Silver CSVs from Snapdata and merge into a unified DataFrame.

    Returns:
        tuple of (processed_df, raw_gold_csv_text, raw_silver_csv_text)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/csv,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        r_gold = requests.get(SNAPDATA_GOLD_URL, headers=headers, timeout=15)
        r_gold.raise_for_status()
        raw_gold_text = r_gold.text

        r_silver = requests.get(SNAPDATA_SILVER_URL, headers=headers, timeout=15)
        r_silver.raise_for_status()
        raw_silver_text = r_silver.text
    except Exception as exc:
        logger.error("Failed to download metals data from Snapdata: %s", exc)
        raise

    # Parse raw CSVs
    df_g_raw = pd.read_csv(io.StringIO(raw_gold_text))
    df_s_raw = pd.read_csv(io.StringIO(raw_silver_text))

    # Filter out nulls/non-trading placeholders
    df_g_valid = df_g_raw[df_g_raw["value"].notna()].copy()
    df_s_valid = df_s_raw[df_s_raw["value"].notna()].copy()

    # Pivot Gold by instrument (XAU.24K, XAU.22K, XAU.18K)
    g_pivot = df_g_valid.pivot(index="date", columns="instrument", values="value")

    df_merged = pd.DataFrame(index=g_pivot.index)
    if "XAU.24K" in g_pivot.columns:
        df_merged["gold_24k_inr_gram"] = g_pivot["XAU.24K"]
        df_merged["gold_24k_inr_10g"] = g_pivot["XAU.24K"] * 10
    if "XAU.22K" in g_pivot.columns:
        df_merged["gold_22k_inr_gram"] = g_pivot["XAU.22K"]
        df_merged["gold_22k_inr_10g"] = g_pivot["XAU.22K"] * 10
    if "XAU.18K" in g_pivot.columns:
        df_merged["gold_18k_inr_gram"] = g_pivot["XAU.18K"]
        df_merged["gold_18k_inr_10g"] = g_pivot["XAU.18K"] * 10

    # Silver (XAG is in INR/kg)
    s_clean = df_s_valid.set_index("date")[["value"]].rename(columns={"value": "silver_inr_kg"})
    s_clean["silver_inr_gram"] = s_clean["silver_inr_kg"] / 1000.0

    df_merged = df_merged.join(s_clean, how="outer").sort_index()
    df_merged = df_merged.ffill().bfill()

    # Standard default aliases (primary gold = 24K)
    df_merged["gold_inr_10g"] = df_merged.get("gold_24k_inr_10g", 0.0)
    df_merged["gold_inr_gram"] = df_merged.get("gold_24k_inr_gram", 0.0)

    # Returns & Momentum
    df_merged["gold_1d_pct"] = df_merged["gold_24k_inr_10g"].pct_change() * 100
    df_merged["silver_1d_pct"] = df_merged["silver_inr_kg"].pct_change() * 100
    df_merged["gold_7d_pct"] = df_merged["gold_24k_inr_10g"].pct_change(7) * 100
    df_merged["silver_7d_pct"] = df_merged["silver_inr_kg"].pct_change(7) * 100

    # Moving averages
    df_merged["gold_20d_ma"] = df_merged["gold_24k_inr_10g"].rolling(window=min(20, len(df_merged)), min_periods=1).mean()
    df_merged["silver_20d_ma"] = df_merged["silver_inr_kg"].rolling(window=min(20, len(df_merged)), min_periods=1).mean()

    # Reset index so 'date' is a column
    df_merged = df_merged.reset_index().rename(columns={"index": "date"})

    return df_merged.round(2), raw_gold_text, raw_silver_text


def save_metals_history(
    df: pd.DataFrame,
    raw_gold_text: str | None = None,
    raw_silver_text: str | None = None,
) -> tuple[Path, Path]:
    """Save raw Snapdata CSVs, unified CSV, and structured JSON to disk and refresh in-memory cache."""
    _ensure_data_dir()

    # Save raw CSVs if provided
    if raw_gold_text:
        _GOLD_RAW_CSV.write_text(raw_gold_text, encoding="utf-8")
    if raw_silver_text:
        _SILVER_RAW_CSV.write_text(raw_silver_text, encoding="utf-8")

    # Save unified CSV
    df.to_csv(_METALS_CSV, index=False)

    # Prepare JSON structure
    latest_row = df.iloc[-1].to_dict() if not df.empty else {}
    records = df.to_dict(orient="records")

    # Metrics summary
    summary = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source": "IBJA via Snapdata (https://snapdata.dev)",
        "count": len(records),
        "latest": latest_row,
    }

    if not df.empty:
        summary["recap"] = {
            "gold_24k_latest_10g": float(latest_row.get("gold_24k_inr_10g", 0.0)),
            "gold_22k_latest_10g": float(latest_row.get("gold_22k_inr_10g", 0.0)),
            "gold_18k_latest_10g": float(latest_row.get("gold_18k_inr_10g", 0.0)),
            "silver_latest_kg": float(latest_row.get("silver_inr_kg", 0.0)),
            "gold_1d_change_pct": float(latest_row.get("gold_1d_pct", 0.0)) if pd.notna(latest_row.get("gold_1d_pct")) else 0.0,
            "silver_1d_change_pct": float(latest_row.get("silver_1d_pct", 0.0)) if pd.notna(latest_row.get("silver_1d_pct")) else 0.0,
            "gold_7d_change_pct": float(latest_row.get("gold_7d_pct", 0.0)) if pd.notna(latest_row.get("gold_7d_pct")) else 0.0,
            "silver_7d_change_pct": float(latest_row.get("silver_7d_pct", 0.0)) if pd.notna(latest_row.get("silver_7d_pct")) else 0.0,
            "gold_24k_30d_min_10g": float(df["gold_24k_inr_10g"].min()),
            "gold_24k_30d_max_10g": float(df["gold_24k_inr_10g"].max()),
            "silver_30d_min_kg": float(df["silver_inr_kg"].min()),
            "silver_30d_max_kg": float(df["silver_inr_kg"].max()),
        }

    payload = {
        "summary": summary,
        "history": records,
    }

    with open(_METALS_JSON, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # Invalidate & populate in-memory cache
    _IN_MEMORY_CACHE["cached_at"] = time.time()
    _IN_MEMORY_CACHE["data"] = payload
    _IN_MEMORY_CACHE["latest_spot"] = summary.get("recap", {})
    _IN_MEMORY_CACHE["llm_context"] = _build_llm_context(payload)

    logger.info("Saved Snapdata metals prices (%d rows) to %s and %s", len(df), _METALS_CSV, _METALS_JSON)
    return _METALS_CSV, _METALS_JSON


def load_metals_history(force_refresh: bool = False) -> dict[str, Any]:
    """Load metals history with high-performance in-memory caching."""
    now = time.time()

    if not force_refresh and _IN_MEMORY_CACHE["data"] is not None:
        if (now - _IN_MEMORY_CACHE["cached_at"]) < CACHE_TTL_SECONDS:
            return _IN_MEMORY_CACHE["data"]

    # Try loading from JSON disk file
    if not force_refresh and _METALS_JSON.exists():
        try:
            with open(_METALS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            _IN_MEMORY_CACHE["cached_at"] = now
            _IN_MEMORY_CACHE["data"] = data
            _IN_MEMORY_CACHE["latest_spot"] = data.get("summary", {}).get("recap", {})
            _IN_MEMORY_CACHE["llm_context"] = _build_llm_context(data)
            return data
        except Exception as exc:
            logger.warning("Error reading %s, will refetch: %s", _METALS_JSON, exc)

    # Download fresh from Snapdata
    df, raw_gold, raw_silver = fetch_snapdata_metals()
    save_metals_history(df, raw_gold, raw_silver)
    return _IN_MEMORY_CACHE["data"]


def get_latest_metals_spot() -> dict[str, Any]:
    """Ultra-fast (<0.1ms) access to latest spot prices and trends."""
    if _IN_MEMORY_CACHE["data"] is None or (time.time() - _IN_MEMORY_CACHE["cached_at"]) >= CACHE_TTL_SECONDS:
        load_metals_history()
    return _IN_MEMORY_CACHE.get("latest_spot", {})


def _build_llm_context(data: dict[str, Any]) -> str:
    """Format a dense, informative context snippet for LLM prompts strictly focusing on 24K Gold and Silver."""
    summary = data.get("summary", {})
    recap = summary.get("recap", {})
    latest = summary.get("latest", {})
    latest_date = latest.get("date", "N/A")

    if not recap:
        return ""

    lines = [
        "### Official 30-Day Bullion Benchmark Rates (India - IBJA Official Benchmark)",
        f"- **Benchmark As-Of Date**: {latest_date} (Source: India Bullion and Jewellers Association via Snapdata)",
        f"- **Pure Gold (24 Karat - XAU.24K.INR - 999 Purity)**: ₹{recap.get('gold_24k_latest_10g', 0):,.2f} per 10 grams (₹{latest.get('gold_24k_inr_gram', 0):,.2f} per gram)",
        f"- **Silver (XAG.INR.KG)**: ₹{recap.get('silver_latest_kg', 0):,.2f} per kilogram (₹{latest.get('silver_inr_gram', 0):,.2f} per gram)",
        f"- **1-Day Price Movement**: 24K Gold {recap.get('gold_1d_change_pct', 0):+.2f}% | Silver {recap.get('silver_1d_change_pct', 0):+.2f}%",
        f"- **7-Day Price Trend**: 24K Gold {recap.get('gold_7d_change_pct', 0):+.2f}% | Silver {recap.get('silver_7d_change_pct', 0):+.2f}%",
        f"- **30-Day Trading Range**: 24K Gold ₹{recap.get('gold_24k_30d_min_10g', 0):,.2f} (Low) - ₹{recap.get('gold_24k_30d_max_10g', 0):,.2f} (High) per 10g | Silver ₹{recap.get('silver_30d_min_kg', 0):,.2f} (Low) - ₹{recap.get('silver_30d_max_kg', 0):,.2f} (High) per kg",
    ]
    return "\n".join(lines)


def format_metals_context_for_llm(force_refresh: bool = False) -> str:
    """Return pre-computed LLM prompt context block in microseconds."""
    now = time.time()
    if not force_refresh and _IN_MEMORY_CACHE.get("llm_context"):
        if (now - _IN_MEMORY_CACHE["cached_at"]) < CACHE_TTL_SECONDS:
            return _IN_MEMORY_CACHE["llm_context"]

    data = load_metals_history(force_refresh=force_refresh)
    return _build_llm_context(data)
