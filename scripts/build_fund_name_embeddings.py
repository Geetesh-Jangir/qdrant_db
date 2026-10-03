"""Build ISIN -> embedding vector cache for fund short names (optional, for fuzzy fallback)."""

from __future__ import annotations

import json
from pathlib import Path

from news_rag.embed import embed_query
from news_rag.fund_search import get_fund_index

_REPO = Path(__file__).resolve().parents[1]
OUT = _REPO / "data" / "fund_name_embeddings.json"


def main() -> None:
    index = get_fund_index()
    index._ensure_loaded()
    out: dict[str, list[float]] = {}
    for entry in index._entries:
        isin = str(entry.get("isin") or "").upper()
        name = str(entry.get("fund_short_name") or entry.get("fund_name") or "")
        if not isin or not name:
            continue
        out[isin] = embed_query(name)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out), encoding="utf-8")
    print(f"wrote {len(out)} embeddings to {OUT}")


if __name__ == "__main__":
    main()
