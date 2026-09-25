"""
Fetch holdings + sectors for each ISIN in PORTFOLIO_JSON (or default portfolio file).

Writes data/fund_holdings_aggregate/portfolio_allisin_holdings.json for CI and
local runs when the full allisin map is not present.
"""

from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from build_allisin_sectors_holdings import MAX_WORKERS, fetch_fund  # noqa: E402

DEFAULT_PORTFOLIO = ROOT / "investor_data" / "mohit" / "portfolio.json"
OUT_FILE = ROOT / "data" / "fund_holdings_aggregate" / "portfolio_allisin_holdings.json"


def _portfolio_path() -> Path:
    raw = (os.environ.get("PORTFOLIO_JSON") or "").strip()
    if raw:
        path = Path(raw)
        return path if path.is_absolute() else ROOT / raw
    return DEFAULT_PORTFOLIO


def load_portfolio_isins(path: Path) -> list[str]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    isins: list[str] = []
    seen: set[str] = set()
    for row in (doc.get("data") or {}).get("holdings") or []:
        isin = str(row.get("isin") or "").strip()
        if not isin or isin in seen:
            continue
        seen.add(isin)
        isins.append(isin)
    if not isins:
        raise SystemExit(f"No ISINs in portfolio file: {path}")
    return isins


def main() -> None:
    portfolio_path = _portfolio_path()
    if not portfolio_path.is_file():
        raise SystemExit(f"Portfolio file not found: {portfolio_path}")

    isins = load_portfolio_isins(portfolio_path)
    print(f"Portfolio: {portfolio_path}")
    print(f"Fetching {len(isins)} ISIN(s) from Rupeestop API ...")

    start = time.time()
    doc: dict = {
        "_meta": {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "portfolio_source": str(portfolio_path.relative_to(ROOT)).replace("\\", "/"),
            "isin_count": len(isins),
        }
    }
    errors = 0
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(isins))) as pool:
        futures = {pool.submit(fetch_fund, isin): isin for isin in isins}
        for fut in as_completed(futures):
            isin, entry = fut.result()
            doc[isin] = entry
            if entry.get("error"):
                errors += 1
                print(f"  error {isin}: {entry.get('error')}")
            else:
                print(f"  ok {isin} holdings={len(entry.get('holdings') or {})}")

    doc["_meta"]["elapsed_seconds"] = round(time.time() - start, 1)
    doc["_meta"]["error_count"] = errors

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Written: {OUT_FILE}")
    if errors:
        raise SystemExit(f"{errors} ISIN(s) failed")


if __name__ == "__main__":
    main()
