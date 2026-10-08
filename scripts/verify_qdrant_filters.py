"""Audit Qdrant payload filters (entity, date, relevance, source, direction, impact)."""

from __future__ import annotations

import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_pipeline.config import Settings
from news_pipeline.qdrant_target import validate_qdrant_settings
from news_pipeline.storage.qdrant_store import NewsStore
from news_pipeline.textutil import to_iso, utc_now
from news_rag.qdrant_reader import QdrantReader, build_filter


def _check_rows(label: str, rows: list[dict], *, expect_entity: str | None = None, **checks) -> list[str]:
    issues: list[str] = []
    if not rows and checks.get("allow_empty"):
        return issues
    if not rows:
        issues.append(f"{label}: no rows returned")
        return issues
    for i, row in enumerate(rows[:50]):
        rel = int(row.get("max_relevance") or 0)
        min_rel = checks.get("min_relevance", 2)
        if rel < min_rel:
            issues.append(f"{label}[{i}] max_relevance={rel} < {min_rel}")
        pub = row.get("published_at") or ""
        if checks.get("published_from") and pub and pub < checks["published_from"]:
            issues.append(f"{label}[{i}] published_at {pub} before {checks['published_from']}")
        if checks.get("published_to") and pub and pub > checks["published_to"]:
            issues.append(f"{label}[{i}] published_at {pub} after {checks['published_to']}")
        if checks.get("source") and row.get("source") != checks["source"]:
            issues.append(f"{label}[{i}] source={row.get('source')} != {checks['source']}")
        if checks.get("direction") and row.get("direction") != checks["direction"]:
            issues.append(f"{label}[{i}] direction={row.get('direction')} != {checks['direction']}")
        if checks.get("min_impact") is not None:
            imp = int(row.get("max_impact") or 0)
            if imp < checks["min_impact"]:
                issues.append(f"{label}[{i}] max_impact={imp} < {checks['min_impact']}")
        if expect_entity:
            names = {str(n) for n in (row.get("entity_names") or [])}
            if expect_entity not in names:
                issues.append(
                    f"{label}[{i}] entity_names missing {expect_entity!r}: {list(names)[:5]}"
                )
    return issues


def main() -> int:
    settings = Settings()
    validate_qdrant_settings(settings)
    store = NewsStore(settings)
    reader = QdrantReader()

    total = store.points_count()
    print(f"collection={settings.collection_name} points={total}")
    if total == 0:
        print("SKIP: empty collection")
        return 1

    sample = store.scroll_points(limit=200, include_text=False)
    entity_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    direction_counts: Counter[str] = Counter()
    for row in sample:
        for name in row.get("entity_names") or []:
            entity_counts[str(name)] += 1
        if row.get("source"):
            source_counts[str(row["source"])] += 1
        if row.get("direction"):
            direction_counts[str(row["direction"])] += 1

    top_entity = entity_counts.most_common(1)[0][0] if entity_counts else None
    other_entity = None
    for name, _ in entity_counts.most_common(20):
        if name != top_entity:
            other_entity = name
            break
    top_source = source_counts.most_common(1)[0][0] if source_counts else None
    top_direction = direction_counts.most_common(1)[0][0] if direction_counts else None

    print(f"sample_size={len(sample)} unique_entities_in_sample={len(entity_counts)}")
    print(f"probe_entity_a={top_entity!r} probe_entity_b={other_entity!r}")
    print(f"probe_source={top_source!r} probe_direction={top_direction!r}")

    published_from = to_iso(utc_now() - timedelta(days=30))
    published_to = to_iso(utc_now())

    all_issues: list[str] = []

    if top_entity:
        rows = store.list_articles(entity_names=[top_entity], published_from=published_from, limit=30)
        all_issues.extend(
            _check_rows(
                "entity_filter_store",
                rows,
                expect_entity=top_entity,
                published_from=published_from,
                min_relevance=2,
            )
        )
        filt = build_filter(
            entity_names=[top_entity],
            published_from=published_from,
            published_to=published_to,
            min_relevance=2,
        )
        rag_rows = reader.scroll_filtered(filt, 30)
        all_issues.extend(
            _check_rows(
                "entity_filter_rag",
                rag_rows,
                expect_entity=top_entity,
                published_from=published_from,
                published_to=published_to,
                min_relevance=2,
            )
        )
        print(f"entity_filter hits store={len(rows)} rag={len(rag_rows)}")

        if other_entity:
            rows_b = store.list_articles(entity_names=[other_entity], published_from=published_from, limit=15)
            leak = [
                r
                for r in rows_b
                if top_entity in (r.get("entity_names") or []) and other_entity not in (r.get("entity_names") or [])
            ]
            if leak:
                all_issues.append(f"entity_isolation: {len(leak)} rows matched B filter but lack B")
            cross = [r for r in rows if other_entity in (r.get("entity_names") or [])]
            print(f"entity_cross: A-filter rows also tagged B={len(cross)} (multi-entity articles OK)")

    rows_broad = store.list_articles(published_from=published_from, limit=20)
    all_issues.extend(
        _check_rows(
            "broad_no_entity",
            rows_broad,
            published_from=published_from,
            min_relevance=2,
            allow_empty=False,
        )
    )
    print(f"broad_filter hits={len(rows_broad)}")

    if top_source:
        rows = store.list_articles(
            published_from=published_from, source=top_source, limit=15
        )
        all_issues.extend(
            _check_rows(
                "source_filter",
                rows,
                source=top_source,
                published_from=published_from,
                min_relevance=2,
                allow_empty=True,
            )
        )
        print(f"source_filter source={top_source} hits={len(rows)}")

    if top_direction:
        rows = store.list_articles(
            published_from=published_from, direction=top_direction, limit=15
        )
        all_issues.extend(
            _check_rows(
                "direction_filter",
                rows,
                direction=top_direction,
                published_from=published_from,
                min_relevance=2,
                allow_empty=True,
            )
        )
        print(f"direction_filter direction={top_direction} hits={len(rows)}")

    rows_imp = store.list_articles(
        published_from=published_from, min_impact=2, limit=15
    )
    all_issues.extend(
        _check_rows(
            "impact_filter",
            rows_imp,
            published_from=published_from,
            min_relevance=2,
            min_impact=2,
            allow_empty=True,
        )
    )
    print(f"impact_filter min_impact=2 hits={len(rows_imp)}")

    # sector_names: indexed in pipeline but NOT in RAG build_filter — document only
    sector_tagged = [r for r in sample if r.get("sector_names")]
    print(
        f"sector_names payload present on {len(sector_tagged)}/{len(sample)} sample points "
        "(RAG build_filter does not filter by sector_names; topic match is post-filter)"
    )

    print("---")
    if all_issues:
        print(f"FAIL issues={len(all_issues)}")
        for line in all_issues[:25]:
            print(" ", line)
        if len(all_issues) > 25:
            print(f"  ... +{len(all_issues) - 25} more")
        return 1
    print("PASS all checked filters match returned payloads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
