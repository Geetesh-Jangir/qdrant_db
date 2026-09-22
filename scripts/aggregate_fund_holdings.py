"""
Fetch fund data for each ISIN and aggregate sectors (>3%) and holdings (>2%).
"""
from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE = "https://backend.rupeestop.com/api/v1/app/fund/"
SECTOR_THRESHOLD = 3.0
HOLDING_THRESHOLD = 2.0
MAX_WORKERS = 12
REQUEST_TIMEOUT = 60

ROOT = Path(__file__).resolve().parents[1]
ISIN_FILE = ROOT / "data" / "direct_plan_growth_isins.txt"
OUT_DIR = ROOT / "data" / "fund_holdings_aggregate"


def normalize_sector(name: str) -> str:
    s = name.strip()
    s = re.sub(r"\s+", " ", s)
    s = s.lower()
    s = re.sub(r"\bit\s*-\s*software\b", "it - software", s)
    s = re.sub(r"\bfintech\b", "fintech", s)
    s = re.sub(r"\band\b", "&", s)
    s = re.sub(r"\s*&\s*", " & ", s)
    return s.strip()


def clean_display_name(name: str) -> str:
    s = name.strip()
    s = re.sub(r"[£$‡]", "", s)
    s = re.sub(r"[!#^~]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_holding(name: str) -> str:
    s = name.strip()
    s = re.sub(r"[£$‡]", "", s)
    s = re.sub(r"[!#^~]+", "", s)
    s = re.sub(r"\s+", " ", s)
    s = s.lower()
    s = re.sub(r"\blimited\b", "ltd", s)
    s = re.sub(r"\bltd\.?\b", "ltd", s)
    s = re.sub(r"\bco\.?\b", "co", s)
    s = re.sub(r"\bcorp\.?\b", "corp", s)
    s = re.sub(r"\bcorporation\b", "corp", s)
    s = re.sub(r"\bordinary shares\b", "", s)
    s = re.sub(r"[^\w\s&/-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Cash / repo lines often differ only by date or label
    if s.startswith("treps") or s == "treps":
        return "treps"
    if "triparty repo" in s or s.startswith("triparty repo"):
        return "triparty repo"
    if s.startswith("reverse repo"):
        return "reverse repo"
    if "clearing corporation of india" in s:
        return "clearing corporation of india ltd"
    if s in ("net current assets", "net receivables / (payables)", "net receivables/(payables)"):
        return s
    return s


def load_isins(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    isins = []
    seen = set()
    for line in lines:
        isin = line.strip()
        if not isin or isin in seen:
            continue
        seen.add(isin)
        isins.append(isin)
    return isins


def fetch_fund(isin: str) -> dict | None:
    url = f"{API_BASE}{isin}"
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "rupeestop-aggregate/1.0"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read().decode("utf-8")
        payload = json.loads(body)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
        return {"isin": isin, "error": str(e)}

    if not payload.get("success"):
        return {"isin": isin, "error": payload.get("message", "unknown error")}

    data = payload.get("data") or {}
    identity = data.get("identity") or {}
    fund_name = identity.get("fund_name") or identity.get("fund_short_name") or isin

    sectors_raw = (data.get("allocations") or {}).get("sector_from_holdings") or []
    holdings_raw = (data.get("portfolio") or {}).get("holdings") or []

    sectors = []
    for item in sectors_raw:
        sector = item.get("sector")
        pct = item.get("percentage")
        if sector is None or pct is None:
            continue
        try:
            pct_f = float(pct)
        except (TypeError, ValueError):
            continue
        if pct_f > SECTOR_THRESHOLD:
            sectors.append({"sector": sector.strip(), "percentage": round(pct_f, 4)})

    holdings = []
    for item in holdings_raw:
        rating = (item.get("rating") or "").strip().lower()
        if rating != "equity":
            continue
        name = item.get("instrument_name")
        pct = item.get("percentage")
        if not name or pct is None:
            continue
        try:
            pct_f = float(pct)
        except (TypeError, ValueError):
            continue
        if pct_f <= HOLDING_THRESHOLD:
            continue
        holdings.append(
            {
                "instrument_name": name.strip(),
                "percentage": round(pct_f, 4),
            }
        )

    return {
        "isin": isin,
        "fund_name": fund_name,
        "sectors_above_3pct": sectors,
        "holdings_above_2pct": holdings,
    }


def run():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    isins = load_isins(ISIN_FILE)
    print(f"Loaded {len(isins)} ISINs from {ISIN_FILE}")

    ok_count = 0
    errors: list[dict] = []

    sector_agg: dict[str, dict] = defaultdict(
        lambda: {"total_percentage": 0.0, "fund_count": 0, "display_name": ""}
    )
    holding_agg: dict[str, dict] = defaultdict(
        lambda: {"total_percentage": 0.0, "fund_count": 0, "display_name": ""}
    )

    start = time.time()
    done = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(fetch_fund, isin): isin for isin in isins}
        for fut in as_completed(futures):
            done += 1
            if done % 100 == 0 or done == len(isins):
                elapsed = time.time() - start
                print(f"  {done}/{len(isins)} ({elapsed:.0f}s)")

            result = fut.result()
            if result is None:
                continue
            if "error" in result:
                errors.append({"isin": result["isin"], "error": result["error"]})
                continue

            ok_count += 1

            for s in result["sectors_above_3pct"]:
                key = normalize_sector(s["sector"])
                entry = sector_agg[key]
                if not entry["display_name"]:
                    entry["display_name"] = clean_display_name(s["sector"])
                entry["total_percentage"] += s["percentage"]
                entry["fund_count"] += 1

            for h in result["holdings_above_2pct"]:
                key = normalize_holding(h["instrument_name"])
                entry = holding_agg[key]
                clean = clean_display_name(h["instrument_name"])
                if not entry["display_name"]:
                    entry["display_name"] = clean
                elif _has_markers(entry["display_name"]) and not _has_markers(clean):
                    entry["display_name"] = clean
                entry["total_percentage"] += h["percentage"]
                entry["fund_count"] += 1

    def finalize_agg(agg: dict[str, dict]) -> list[dict]:
        rows = []
        for _key, value in agg.items():
            rows.append(
                {
                    "name": value["display_name"],
                    "total_percentage": round(value["total_percentage"], 4),
                    "fund_count": value["fund_count"],
                }
            )
        rows.sort(key=lambda item: (-item["total_percentage"], item["name"].lower()))
        return rows

    sectors_summary = finalize_agg(sector_agg)
    holdings_summary = finalize_agg(holding_agg)

    sectors_csv = OUT_DIR / "aggregated_sectors.csv"
    with sectors_csv.open("w", encoding="utf-8") as handle:
        handle.write("sector,total_percentage,fund_count\n")
        for row in sectors_summary:
            name = row["name"].replace('"', '""')
            handle.write(f'"{name}",{row["total_percentage"]},{row["fund_count"]}\n')

    holdings_csv = OUT_DIR / "aggregated_holdings.csv"
    with holdings_csv.open("w", encoding="utf-8") as handle:
        handle.write("instrument_name,total_percentage,fund_count\n")
        for row in holdings_summary:
            name = row["name"].replace('"', '""')
            handle.write(f'"{name}",{row["total_percentage"]},{row["fund_count"]}\n')

    print(f"\nDone in {time.time() - start:.1f}s")
    print(f"  OK: {ok_count}  Errors: {len(errors)}")
    print(f"  Sectors: {len(sectors_summary)}  Holdings: {len(holdings_summary)}")
    print(f"  Written: {sectors_csv}")
    print(f"  Written: {holdings_csv}")


def _has_markers(name: str) -> bool:
    return any(char in name for char in "!#^~‡$£")


if __name__ == "__main__":
    run()
