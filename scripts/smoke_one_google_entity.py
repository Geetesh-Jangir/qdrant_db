"""Live smoke: fetch_entity_items for one holding (no Jev/Qdrant)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_pipeline.config import Settings
from news_pipeline.sources.google_news import fetch_entity_items


def main() -> int:
    settings = Settings()
    entity = {
        "name": "HDFC Bank",
        "type": "holding",
        "query": "HDFC Bank",
        "industry": "Banks",
        "fund_count": 100,
        "total_percentage": 5.0,
    }
    print(
        f"fetch_entity_items query={entity['query']} "
        f"when={settings.google_news_when} window_hours={settings.news_window_hours}"
    )
    try:
        items = fetch_entity_items(entity, settings)
    except Exception as exc:
        print(f"RESULT ok=False error={type(exc).__name__}: {exc}")
        return 1
    print(f"RESULT ok=True kept={len(items)}")
    for i, row in enumerate(items[:5], start=1):
        print(f"  [{i}] {row['source']} | {row['title'][:72]}")
        print(f"       {row['url'][:96]}")
    if not items:
        print("  (zero items — empty RSS or publisher/time filters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
