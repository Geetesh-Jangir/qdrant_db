"""Offline NL resolution audit for regular-growth-by-amc.md (optional full-universe run)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_rag.fund_search import (  # noqa: E402
    _PLAN_SUFFIX_RE,
    get_fund_index,
    resolve_fund_from_question,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit fund phrase resolution against the catalog")
    parser.add_argument("--limit", type=int, default=0, help="Max schemes (0 = all)")
    args = parser.parse_args()

    idx = get_fund_index()
    idx._ensure_loaded()
    entries = list(idx._entries)
    if args.limit > 0:
        entries = entries[: args.limit]
    misses: list[str] = []
    for entry in entries:
        fname = str(entry.get("fund_name") or "")
        isin = str(entry.get("isin") or "").upper()
        short = _PLAN_SUFFIX_RE.sub("", fname).strip()
        q = f"tell me about {short}"
        detail, ambiguous, _ = resolve_fund_from_question(q)
        if ambiguous or not detail or str(detail.get("isin") or "").upper() != isin:
            misses.append(fname)
    print(f"Checked {len(entries)} schemes; misses={len(misses)}")
    for name in misses[:30]:
        print(f"  - {name}")
    if len(misses) > 30:
        print(f"  ... and {len(misses) - 30} more")
    return 1 if misses else 0


if __name__ == "__main__":
    raise SystemExit(main())