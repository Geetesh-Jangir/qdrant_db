"""Replace holdings.asset_type with holdings.rating in the existing ISIN map.

Keeps sectors and fund metadata. Fetches rating from the fund API.
Resumes via allisin_sectors_with_holdings.rating_patch.jsonl.
"""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from build_allisin_sectors_holdings import ISIN_FILE, MAX_WORKERS, OUT_FILE, fetch_fund, load_isins

PATCH_LOG = OUT_FILE.with_name("allisin_sectors_with_holdings.rating_patch.jsonl")
FLUSH_EVERY = 50
BATCH_SIZE = 200


def load_done_isins(path) -> set[str]:
    done: set[str] = set()
    if not path.is_file():
        return done
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                isin = json.loads(line).get("isin")
            except json.JSONDecodeError:
                continue
            if isin:
                done.add(isin)
    return done


def apply_patch_and_write() -> None:
    print(f"Loading {OUT_FILE} ...", flush=True)
    doc = json.loads(OUT_FILE.read_text(encoding="utf-8"))
    applied = 0
    if PATCH_LOG.is_file():
        with PATCH_LOG.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                isin = row.get("isin")
                holdings = row.get("holdings")
                entry = doc.get(isin)
                if isin and isinstance(entry, dict) and isinstance(holdings, dict):
                    entry["holdings"] = holdings
                    applied += 1
    tmp = OUT_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(OUT_FILE)
    print(f"Applied {applied} holding patches to {OUT_FILE}", flush=True)


def main() -> None:
    all_isins = load_isins(ISIN_FILE)
    done = load_done_isins(PATCH_LOG)
    pending = [isin for isin in all_isins if isin not in done]
    total = len(all_isins)
    print(f"Already patched: {len(done)}  Pending: {len(pending)}", flush=True)

    start = time.time()
    completed = len(done)

    if pending:
        with PATCH_LOG.open("a", encoding="utf-8") as log, ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            for offset in range(0, len(pending), BATCH_SIZE):
                batch = pending[offset : offset + BATCH_SIZE]
                buffer: list[str] = []
                futures = {pool.submit(fetch_fund, isin): isin for isin in batch}
                for fut in as_completed(futures):
                    isin, entry = fut.result()
                    holdings = entry.get("holdings") if isinstance(entry, dict) else {}
                    if not isinstance(holdings, dict):
                        holdings = {}
                    buffer.append(json.dumps({"isin": isin, "holdings": holdings}, ensure_ascii=False))
                    completed += 1
                    if len(buffer) >= FLUSH_EVERY:
                        log.write("\n".join(buffer) + "\n")
                        log.flush()
                        buffer.clear()
                        print(f"  {completed}/{total} ({time.time() - start:.0f}s)", flush=True)
                if buffer:
                    log.write("\n".join(buffer) + "\n")
                    log.flush()
                    print(f"  {completed}/{total} ({time.time() - start:.0f}s)", flush=True)

    print("Writing updated JSON...", flush=True)
    apply_patch_and_write()
    print(f"Elapsed {time.time() - start:.1f}s", flush=True)


if __name__ == "__main__":
    main()
