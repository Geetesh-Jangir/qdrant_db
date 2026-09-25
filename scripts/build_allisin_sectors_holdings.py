"""
Fetch sectors + holdings for every ISIN in allisin.txt.

Writes data/fund_holdings_aggregate/allisin_sectors_with_holdings.json
keyed by ISIN for O(1) lookup after json.load.

Resumes from allisin_sectors_with_holdings.checkpoint.jsonl.
"""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE = "https://backend.rupeestop.com/api/v1/app/fund/"
MAX_WORKERS = 12
REQUEST_TIMEOUT = 60
FLUSH_EVERY = 50

ROOT = Path(__file__).resolve().parents[1]
ISIN_FILE = ROOT / "data" / "fund_holdings_aggregate" / "allisin.txt"
OUT_DIR = ROOT / "data" / "fund_holdings_aggregate"
OUT_FILE = OUT_DIR / "allisin_sectors_with_holdings.json"
CHECKPOINT_FILE = OUT_DIR / "allisin_sectors_with_holdings.checkpoint.jsonl"


def load_isins(path: Path) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        isin = line.strip()
        if not isin or isin in seen:
            continue
        seen.add(isin)
        out.append(isin)
    return out


def _pct(value: object) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def fetch_fund(isin: str) -> tuple[str, dict]:
    url = f"{API_BASE}{isin}"
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "rupeestop-isin-map/1.0"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return isin, {"sectors": {}, "holdings": {}, "error": str(exc)}

    if not payload.get("success"):
        return isin, {
            "sectors": {},
            "holdings": {},
            "error": payload.get("message") or "unknown error",
        }

    data = payload.get("data") or {}
    identity = data.get("identity") or {}
    as_on = (data.get("as_on") or {}).get("metrics") or ""

    sectors: dict[str, float] = {}
    for item in (data.get("allocations") or {}).get("sector_from_holdings") or []:
        name = str(item.get("sector") or "").strip()
        pct = _pct(item.get("percentage"))
        if name and pct is not None:
            sectors[name] = pct

    holdings: dict[str, dict] = {}
    for item in (data.get("portfolio") or {}).get("holdings") or []:
        name = str(item.get("instrument_name") or "").strip()
        pct = _pct(item.get("percentage"))
        if not name or pct is None:
            continue
        key = name
        if key in holdings:
            extra = str(item.get("rating") or "").strip()
            key = f"{name} | {extra}" if extra else name
            n = 2
            while key in holdings:
                key = f"{name} | {n}"
                n += 1
        industry = item.get("industry")
        holdings[key] = {
            "percentage": pct,
            "industry": "" if industry is None else str(industry).strip(),
            "rating": "" if item.get("rating") is None else str(item.get("rating")).strip(),
        }

    return isin, {
        "as_on": as_on,
        "fund_short_name": identity.get("fund_short_name") or identity.get("fund_name") or "",
        "category": identity.get("category") or "",
        "scheme_type": identity.get("scheme_type") or "",
        "sectors": sectors,
        "holdings": holdings,
    }


def load_done_isins(path: Path) -> set[str]:
    done: set[str] = set()
    if not path.is_file():
        return done
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            isin = row.get("isin")
            if isin:
                done.add(isin)
    return done


def write_final(checkpoint_path: Path, total: int, elapsed: float) -> tuple[int, int]:
    doc: dict = {
        "_meta": {
            "version": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "isin_source": str(ISIN_FILE.relative_to(ROOT)).replace("\\", "/"),
            "api": API_BASE + "{isin}",
            "sector_path": "data.allocations.sector_from_holdings",
            "holdings_path": "data.portfolio.holdings",
            "total_isins": total,
            "elapsed_seconds": round(elapsed, 1),
        }
    }
    ok = 0
    err = 0
    if checkpoint_path.is_file():
        with checkpoint_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                isin = row.get("isin")
                entry = row.get("entry")
                if not isin or not isinstance(entry, dict):
                    continue
                doc[isin] = entry
                if entry.get("error"):
                    err += 1
                else:
                    ok += 1
    doc["_meta"]["stored_count"] = ok + err
    doc["_meta"]["ok_count"] = ok
    doc["_meta"]["error_count"] = err
    OUT_FILE.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return ok, err


def run(*, limit: int | None, fresh: bool) -> None:
    isins = load_isins(ISIN_FILE)
    if limit is not None:
        isins = isins[:limit]
    total = len(isins)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if fresh and CHECKPOINT_FILE.is_file():
        CHECKPOINT_FILE.unlink()

    done = load_done_isins(CHECKPOINT_FILE)
    pending = [isin for isin in isins if isin not in done]
    print(f"Total ISINs: {total}  Checkpointed: {len(done)}  Pending: {len(pending)}", flush=True)

    start = time.time()
    if pending:
        completed = len(done)
        buffer: list[str] = []
        with CHECKPOINT_FILE.open("a", encoding="utf-8") as ck, ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futures = {pool.submit(fetch_fund, isin): isin for isin in pending}
            for fut in as_completed(futures):
                isin, entry = fut.result()
                buffer.append(json.dumps({"isin": isin, "entry": entry}, ensure_ascii=False))
                completed += 1
                if len(buffer) >= FLUSH_EVERY or completed == total:
                    ck.write("\n".join(buffer) + "\n")
                    ck.flush()
                    buffer.clear()
                    elapsed = time.time() - start
                    print(f"  {completed}/{total} ({elapsed:.0f}s)", flush=True)
        if buffer:
            with CHECKPOINT_FILE.open("a", encoding="utf-8") as ck:
                ck.write("\n".join(buffer) + "\n")

    elapsed = time.time() - start
    print("Writing final JSON...")
    ok, err = write_final(CHECKPOINT_FILE, total, elapsed)
    print(f"\nDone in {elapsed:.1f}s")
    print(f"  OK: {ok}  Errors: {err}")
    print(f"  Written: {OUT_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build allisin_sectors_with_holdings.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    run(limit=args.limit, fresh=args.fresh)


if __name__ == "__main__":
    main()
