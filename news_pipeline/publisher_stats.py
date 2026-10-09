"""Per-publisher URL counts for one calendar day."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from news_pipeline.run_context import get_run_context


class PublisherStats:
    def __init__(self) -> None:
        self._received: dict[str, set[str]] = defaultdict(set)
        self._scraped: dict[str, set[str]] = defaultdict(set)
        self._errors: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))

    def reset(self) -> None:
        self._received.clear()
        self._scraped.clear()
        self._errors.clear()

    def record_received(self, source: str, url: str) -> None:
        if source and url:
            self._received[source].add(url)

    def record_scraped(self, source: str, url: str) -> None:
        if source and url:
            self._scraped[source].add(url)

    def record_scrape_error(self, source: str, url: str, reason: str) -> None:
        if source and url:
            self._errors[source][reason].add(url)

    def build_payload(self) -> dict[str, Any]:
        ctx = get_run_context()
        publishers: list[dict[str, Any]] = []
        total_received = 0
        total_scraped = 0
        total_scrape_errors = 0
        for source in sorted(self._received.keys()):
            received = len(self._received[source])
            if received <= 0:
                continue
            scraped = len(self._scraped.get(source, set()))
            error_urls: set[str] = set()
            error_reasons: dict[str, int] = {}
            for reason, urls in self._errors.get(source, {}).items():
                error_reasons[reason] = len(urls)
                error_urls |= urls
            scrape_errors = len(error_urls)
            total_received += received
            total_scraped += scraped
            total_scrape_errors += scrape_errors
            publishers.append(
                {
                    "source": source,
                    "received": received,
                    "scraped": scraped,
                    "scrape_errors": scrape_errors,
                    "error_reasons": error_reasons,
                }
            )
        return {
            "run_id": ctx.run_id,
            "calendar_day": ctx.calendar_day,
            "news_date_range": ctx.news_date_range,
            "totals": {
                "publishers_with_traffic": len(publishers),
                "urls_received": total_received,
                "urls_scraped": total_scraped,
                "urls_scrape_errors": total_scrape_errors,
            },
            "publishers": publishers,
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.build_payload(), indent=2), encoding="utf-8")


_STATS = PublisherStats()


def get_publisher_stats() -> PublisherStats:
    return _STATS
