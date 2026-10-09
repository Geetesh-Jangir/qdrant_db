"""Per-entity counts through the ingest funnel."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from news_pipeline.run_context import get_run_context


def _empty_row(name: str, entity_type: str) -> dict[str, Any]:
    return {
        "name": name,
        "type": entity_type,
        "rss_items": 0,
        "dropped_before_resolve": 0,
        "resolve_failed": 0,
        "google_kept": 0,
        "skipped_existing": 0,
        "title_dedupe_dropped": 0,
        "after_title_dedupe": 0,
        "after_title_jev": 0,
        "scrape_dropped": 0,
        "scrape_drop_reasons": {},
        "scraped": 0,
        "after_body_jev": 0,
        "upserted": 0,
    }


class EntityFunnel:
    def __init__(self) -> None:
        self._rows: dict[tuple[str, str], dict[str, Any]] = {}

    def reset(self) -> None:
        self._rows.clear()

    def _row(self, name: str, entity_type: str) -> dict[str, Any]:
        key = (name, entity_type)
        if key not in self._rows:
            self._rows[key] = _empty_row(name, entity_type)
        return self._rows[key]

    def bump(self, name: str, entity_type: str, field: str, amount: int = 1) -> None:
        row = self._row(name, entity_type)
        row[field] = int(row.get(field) or 0) + amount

    def bump_scrape_drop(self, name: str, entity_type: str, reason: str) -> None:
        self.bump(name, entity_type, "scrape_dropped")
        row = self._row(name, entity_type)
        reasons = row.setdefault("scrape_drop_reasons", {})
        reasons[reason] = int(reasons.get(reason) or 0) + 1

    def match_entities(self, candidate: dict) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for match in candidate.get("matches") or []:
            if match.get("name"):
                out.append((match["name"], match.get("type") or ""))
        if not out and candidate.get("entity_name"):
            out.append((candidate["entity_name"], candidate.get("entity_type") or ""))
        return out

    def write(self, path: Path) -> None:
        ctx = get_run_context()
        entities = sorted(self._rows.values(), key=lambda r: (r["type"], r["name"]))
        payload = {
            "run_id": ctx.run_id,
            "calendar_day": ctx.calendar_day,
            "news_date_range": ctx.news_date_range,
            "entities": entities,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


_FUNNEL = EntityFunnel()


def get_entity_funnel() -> EntityFunnel:
    return _FUNNEL
