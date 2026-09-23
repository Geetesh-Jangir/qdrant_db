"""Print what is stored in Qdrant (Cloud or local). Writes a separate log + JSON under data/qdrant_inspect/."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_pipeline.config import Settings
from news_pipeline.qdrant_target import qdrant_summary, validate_qdrant_settings
from news_pipeline.storage.qdrant_store import NewsStore
from news_pipeline.textutil import to_iso, utc_now


def _write_log(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def inspect_qdrant(
    *,
    limit: int = 50,
    include_text: bool = False,
    text_preview_chars: int = 200,
) -> tuple[Path, Path]:
    settings = Settings()
    validate_qdrant_settings(settings)

    started = utc_now()
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    out_dir = settings.path(settings.qdrant_inspect_dir)
    log_path = out_dir / f"{stamp}.log"
    json_path = out_dir / f"{stamp}.json"

    store = NewsStore(settings)
    qdrant = qdrant_summary(settings)
    lines: list[str] = [
        f"started_at={to_iso(started)}",
        f"qdrant_host={qdrant['url_host']}",
        f"collection={qdrant['collection']}",
        f"cloud={qdrant['cloud']}",
    ]

    collections = store.list_collections()
    lines.append(f"cluster_collections={collections}")

    if qdrant["collection"] not in collections:
        lines.append(f"error=collection '{qdrant['collection']}' not found on this cluster")
        payload = {
            "started_at": to_iso(started),
            "finished_at": to_iso(datetime.now(timezone.utc)),
            "qdrant": qdrant,
            "cluster_collections": collections,
            "points_count": 0,
            "points": [],
            "error": f"collection '{qdrant['collection']}' not found",
        }
        _write_log(log_path, lines)
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return log_path, json_path

    total = store.points_count()
    lines.append(f"points_count={total}")
    lines.append(f"sample_limit={limit}")
    lines.append("---")

    points = store.scroll_points(limit=limit, include_text=include_text)
    for index, row in enumerate(points, start=1):
        entities = row.get("entity_names") or []
        entity_str = ", ".join(entities[:5])
        if len(entities) > 5:
            entity_str += f" (+{len(entities) - 5} more)"
        industries = row.get("industry_names") or []
        industry_str = ", ".join(industries[:4])
        holdings = row.get("holding_names") or []
        holding_str = ", ".join(holdings[:3])
        lines.append(
            f"[{index}] title={row.get('title', '')!r} "
            f"url={row.get('url', '')} "
            f"source={row.get('source', '')} "
            f"published_at={row.get('published_at', '')} "
            f"impact={row.get('max_impact')} relevance={row.get('max_relevance')} "
            f"primary_industry={row.get('primary_industry', '')!r} "
            f"industries=[{industry_str}] holdings=[{holding_str}] "
            f"entities=[{entity_str}]"
        )
        if include_text:
            text = (row.get("scraped_text") or "").replace("\n", " ").strip()
            if len(text) > text_preview_chars:
                text = text[: text_preview_chars - 3] + "..."
            lines.append(f"     text_preview={text!r}")

    lines.append("---")
    lines.append(f"sampled={len(points)} total_points={total}")
    lines.append(f"log_file={log_path}")
    lines.append(f"json_file={json_path}")

    export_rows = []
    for row in points:
        copy = dict(row)
        if not include_text:
            copy.pop("scraped_text", None)
            copy.pop("entities", None)
        elif copy.get("scraped_text"):
            text = copy["scraped_text"]
            if len(text) > text_preview_chars:
                copy["scraped_text_preview"] = text[:text_preview_chars] + "..."
                copy.pop("scraped_text")
        export_rows.append(copy)

    payload = {
        "started_at": to_iso(started),
        "finished_at": to_iso(datetime.now(timezone.utc)),
        "qdrant": qdrant,
        "cluster_collections": collections,
        "points_count": total,
        "sample_limit": limit,
        "sampled": len(points),
        "points": export_rows,
    }
    _write_log(log_path, lines)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return log_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect points stored in Qdrant (uses .env QDRANT_*).")
    parser.add_argument("--limit", type=int, default=50, help="Max points to sample (default 50)")
    parser.add_argument(
        "--include-text",
        action="store_true",
        help="Include scraped_text preview in log and JSON",
    )
    parser.add_argument(
        "--text-chars",
        type=int,
        default=200,
        help="Max characters of body text when --include-text (default 200)",
    )
    args = parser.parse_args()

    log_path, json_path = inspect_qdrant(
        limit=max(1, args.limit),
        include_text=args.include_text,
        text_preview_chars=max(80, args.text_chars),
    )
    print(f"Wrote log:  {log_path}")
    print(f"Wrote json: {json_path}")


if __name__ == "__main__":
    main()
