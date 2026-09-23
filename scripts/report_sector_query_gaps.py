"""List aggregate sectors that have no Google query in news_pipeline.config.SECTOR_QUERIES."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_pipeline.config import Settings
from news_pipeline.sources.universe import sector_query_gaps


def main() -> None:
    settings = Settings()
    gaps = sector_query_gaps(settings, limit=0)
    print(f"Sectors in {settings.sectors_csv} without SECTOR_QUERIES entry: {len(gaps)}")
    for name, fund_count in gaps[:50]:
        print(f"  {fund_count:4d}  {name}")
    if len(gaps) > 50:
        print(f"  ... and {len(gaps) - 50} more")


if __name__ == "__main__":
    main()
