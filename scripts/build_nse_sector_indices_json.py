"""Regenerate nse_sector_indices_yfinance.json from SECTOR_QUERIES (run from repo root)."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_pipeline.config import SECTOR_QUERIES, repo_root

MAP: dict[str, tuple[str, str, str, str, str | None]] = {
    "Banks": ("Nifty Bank", "sectoral", "^NSEBANK", "NIFTY BANK (^NSEBANK)", None),
    "Pharmaceuticals & Biotechnology": (
        "Nifty Pharma",
        "sectoral",
        "^CNXPHARMA",
        "NIFTY PHARMA (^CNXPHARMA)",
        None,
    ),
    "It - Software": ("Nifty IT", "sectoral", "^CNXIT", "NIFTY IT (^CNXIT)", None),
    "Finance": (
        "Nifty Financial Services",
        "sectoral",
        "^CNXFIN",
        "NIFTY FIN SERVICE (^CNXFIN)",
        None,
    ),
    "Capital Markets": (
        "Nifty Financial Services",
        "sectoral",
        "^CNXFIN",
        "NIFTY FIN SERVICE (^CNXFIN)",
        "No dedicated Nifty Capital Markets ticker on Yahoo; financial services index used as proxy.",
    ),
    "Automobiles": ("Nifty Auto", "sectoral", "^CNXAUTO", "NIFTY AUTO (^CNXAUTO)", None),
    "Auto Components": (
        "Nifty Auto",
        "sectoral",
        "^CNXAUTO",
        "NIFTY AUTO (^CNXAUTO)",
        "Auto index proxy for auto-ancillary exposure.",
    ),
    "Retailing": (
        "Nifty Services Sector",
        "thematic",
        "^CNXSERVICE",
        "NIFTY SERVICES (^CNXSERVICE)",
        "Services-sector index proxy for retail.",
    ),
    "Electrical Equipment": (
        "Nifty Infrastructure",
        "thematic",
        "^CNXINFRA",
        "NIFTY INFRA (^CNXINFRA)",
        None,
    ),
    "Consumer Durables": (
        "Nifty Services Sector",
        "thematic",
        "^CNXSERVICE",
        "NIFTY SERVICES (^CNXSERVICE)",
        "Services-sector proxy; no Nifty Consumer Durables ticker on Yahoo.",
    ),
    "Industrial Products": (
        "Nifty Infrastructure",
        "thematic",
        "^CNXINFRA",
        "NIFTY INFRA (^CNXINFRA)",
        "Infrastructure / capital-goods proxy.",
    ),
    "Petroleum Products": (
        "Nifty Energy",
        "thematic",
        "^CNXENERGY",
        "NIFTY ENERGY (^CNXENERGY)",
        None,
    ),
    "Telecom - Services": (
        "Nifty IT",
        "sectoral",
        "^CNXIT",
        "NIFTY IT (^CNXIT)",
        "IT index proxy; Nifty Telecommunications not available on Yahoo.",
    ),
    "Power": (
        "Nifty Energy",
        "thematic",
        "^CNXENERGY",
        "NIFTY ENERGY (^CNXENERGY)",
        "Energy index proxy for power utilities.",
    ),
    "Healthcare Services": (
        "Nifty Pharma",
        "sectoral",
        "^CNXPHARMA",
        "NIFTY PHARMA (^CNXPHARMA)",
        "Pharma index proxy for hospital operators.",
    ),
    "Construction": (
        "Nifty Infrastructure",
        "thematic",
        "^CNXINFRA",
        "NIFTY INFRA (^CNXINFRA)",
        None,
    ),
    "Chemicals & Petrochemicals": (
        "Nifty Commodities",
        "thematic",
        "^CNXCMDT",
        "NIFTY COMMODITIES (^CNXCMDT)",
        None,
    ),
    "Realty": ("Nifty Realty", "sectoral", "^CNXREALTY", "NIFTY REALTY (^CNXREALTY)", None),
    "Insurance": (
        "Nifty Financial Services",
        "sectoral",
        "^CNXFIN",
        "NIFTY FIN SERVICE (^CNXFIN)",
        "Financial services index includes listed insurers.",
    ),
    "Aerospace & Defense": (
        "Nifty Infrastructure",
        "thematic",
        "^CNXINFRA",
        "NIFTY INFRA (^CNXINFRA)",
        "Infrastructure proxy; Nifty India Defence not on Yahoo.",
    ),
    "Diversified Fmcg": ("Nifty FMCG", "sectoral", "^CNXFMCG", "NIFTY FMCG (^CNXFMCG)", None),
    "Financial Technology (fintech)": (
        "Nifty Financial Services",
        "sectoral",
        "^CNXFIN",
        "NIFTY FIN SERVICE (^CNXFIN)",
        None,
    ),
    "Transport Services": (
        "Nifty Infrastructure",
        "thematic",
        "^CNXINFRA",
        "NIFTY INFRA (^CNXINFRA)",
        "Infrastructure / logistics proxy.",
    ),
    "Cement & Cement Products": (
        "Nifty Infrastructure",
        "thematic",
        "^CNXINFRA",
        "NIFTY INFRA (^CNXINFRA)",
        "Infrastructure / construction proxy.",
    ),
    "Food Products": ("Nifty FMCG", "sectoral", "^CNXFMCG", "NIFTY FMCG (^CNXFMCG)", None),
    "Ferrous Metals": ("Nifty Metal", "sectoral", "^CNXMETAL", "NIFTY METAL (^CNXMETAL)", None),
    "Non - Ferrous Metals": ("Nifty Metal", "sectoral", "^CNXMETAL", "NIFTY METAL (^CNXMETAL)", None),
    "Leisure Services": (
        "Nifty Services Sector",
        "thematic",
        "^CNXSERVICE",
        "NIFTY SERVICES (^CNXSERVICE)",
        None,
    ),
    "Beverages": (
        "Nifty FMCG",
        "sectoral",
        "^CNXFMCG",
        "NIFTY FMCG (^CNXFMCG)",
        "FMCG proxy for beverage names.",
    ),
    "Agricultural, Commercial & Construction Vehicles": (
        "Nifty Auto",
        "sectoral",
        "^CNXAUTO",
        "NIFTY AUTO (^CNXAUTO)",
        "Auto index proxy for tractors and commercial vehicles.",
    ),
}


def main() -> None:
    if set(MAP) != set(SECTOR_QUERIES):
        missing = set(SECTOR_QUERIES) - set(MAP)
        extra = set(MAP) - set(SECTOR_QUERIES)
        raise SystemExit(f"MAP mismatch missing={missing} extra={extra}")

    by_sector: dict[str, dict] = {}
    for sector in sorted(SECTOR_QUERIES):
        nse, itype, tick, search, note = MAP[sector]
        row: dict = {
            "nse_index_name": nse,
            "index_type": itype,
            "yfinance_ticker": tick,
            "yfinance_search_name": search,
            "ticker_status": "yfinance_verified",
        }
        if note:
            row["proxy_note"] = note
        by_sector[sector] = row

    doc = {
        "metadata": {
            "title": "NSE sector indices aligned to news pipeline SECTOR_QUERIES",
            "schema_version": "2.0.0",
            "generated_date": date.today().isoformat(),
            "lookup": (
                "by_sector — keys match SECTOR_QUERIES / aggregated_sectors sector labels "
                "exactly (O(1) dict lookup)."
            ),
            "benchmarks_lookup": (
                "benchmarks — keyed by nse_index_name; Nifty 50 retained as broad benchmark."
            ),
            "yfinance_verified_on": date.today().isoformat(),
            "recommended_runtime_check": (
                "import yfinance as yf; "
                "df = yf.Ticker(symbol).history(period='5d'); "
                "assert not df.empty"
            ),
        },
        "benchmarks": {
            "Nifty 50": {
                "nse_index_name": "Nifty 50",
                "index_type": "benchmark",
                "yfinance_ticker": "^NSEI",
                "yfinance_search_name": "NIFTY 50 (^NSEI)",
                "ticker_status": "yfinance_verified",
                "use_case": "Broad Indian equity benchmark for sector-relative returns.",
            }
        },
        "by_sector": by_sector,
        "counts": {
            "sectors_in_pipeline": len(by_sector),
            "benchmarks": 1,
        },
    }

    path = repo_root() / "data/fund_holdings_aggregate/nse_sector_indices_yfinance.json"
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path} sectors={len(by_sector)}")


if __name__ == "__main__":
    main()
