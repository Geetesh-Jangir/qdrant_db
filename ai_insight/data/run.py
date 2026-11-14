"""Fetch every numeric series and write data/ai_insight/latest.json."""

from __future__ import annotations

import json
from pathlib import Path

from ai_insight.data.base import FiiDiiSnapshot, NumericRecord
from ai_insight.data.nse_fii_dii import fetch_fii_dii_snapshot
from ai_insight.data.macro_data import get_macro_snapshot, write_snapshot
from ai_insight.data.official import fetch_official, numeric_from_fii_dii_snapshot
from ai_insight.data.ask_market_bridge import fetch_ask_market_records, write_ask_market_snapshot
from ai_insight.data.yfinance_source import fetch_yfinance

# News-only on purpose (no traded / official numeric series in this job).
NEWS_ONLY = (
    "Macro - Silver",
    "Macro - Natural Gas",
    "Macro - RBI Repo Rate",
    "Macro - SEBI",
    "Macro - Tariffs & Trade",
    "Macro - Geopolitical Risk",
)


def fetch_all(fii_dii: FiiDiiSnapshot | None = None) -> list[NumericRecord]:
    snap = fii_dii if fii_dii is not None else fetch_fii_dii_snapshot()
    return (
        fetch_yfinance()
        + fetch_ask_market_records()
        + [numeric_from_fii_dii_snapshot(snap)]
        + fetch_official(include_fii=False)
    )


def write_fii_dii(snap: FiiDiiSnapshot, root: Path) -> Path:
    path = root / "data" / "ai_insight" / "fii_dii_latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap.as_dict(), indent=2), encoding="utf-8")
    return path


def write_latest(
    records: list[NumericRecord],
    root: Path,
    *,
    fii_dii: FiiDiiSnapshot | None = None,
) -> Path:
    path = root / "data" / "ai_insight" / "latest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "records": [row.as_dict() for row in records],
        "fii_dii": fii_dii.as_dict() if fii_dii else None,
        "news_only": list(NEWS_ONLY),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def main() -> None:
    from news_pipeline.config import repo_root

    fii_dii = fetch_fii_dii_snapshot()
    records = fetch_all(fii_dii)
    root = repo_root()
    fii_path = write_fii_dii(fii_dii, root)
    path = write_latest(records, root, fii_dii=fii_dii)
    macro_path = write_snapshot(get_macro_snapshot(), root)
    ask_market_path = write_ask_market_snapshot(root)
    print(f"wrote {macro_path}")
    print(f"wrote {ask_market_path}")
    ok = [row.entity for row in records if row.status == "ok"]
    missing = [f"{row.entity}: {row.detail}" for row in records if row.status != "ok"]
    print(f"wrote {path}")
    print(f"wrote {fii_path} (FII/DII buy/sell/net)")
    if fii_dii.status == "ok":
        print(
            f"  date={fii_dii.trade_date} "
            f"FII net={fii_dii.fii.net_inr_crore} DII net={fii_dii.dii.net_inr_crore}"
        )
    print("available:", ", ".join(ok) or "(none)")
    print("unavailable:")
    for line in missing:
        print(" -", line)
    print("news only (no numeric fetch):", ", ".join(NEWS_ONLY))


if __name__ == "__main__":
    main()
