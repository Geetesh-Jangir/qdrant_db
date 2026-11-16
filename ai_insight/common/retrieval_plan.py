"""Per-section news retrieval over a rolling window. Fresh Qdrant each run."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from news_pipeline.textutil import parse_time

from ai_insight.common.clustering import cluster_rows, rank_clusters
from ai_insight.common.config import CommonConfig, load_config
from ai_insight.common.evidence import enforce_prompt_budget, pick_evidence
from ai_insight.common.qdrant_access import GateConfig, fetch_entity_rows
from ai_insight.common.time_ist import ist_now, rolling_window, session_window

SectionId = Literal[
    "market_driver_digest",
    "fii_dii_flow_narrative",
    "sector_leaderboard",
    "sector_index_insights",
    "additional_insights",
]

RELAXED_GATE = GateConfig(min_relevance=2, min_impact=2, min_about=0.5)


@dataclass
class SectionRetrieval:
    rows: list[dict[str, Any]]
    clusters: list[Any]
    evidence: list[Any]
    window: tuple[str, str]
    today_window: tuple[str, str]
    diagnostics: dict[str, Any] = field(default_factory=dict)


def plan_window(ctx, section: SectionId) -> tuple[tuple[str, str], tuple[str, str]]:
    cfg = ctx.config
    days = max(1, cfg.news_window_days)
    now = ist_now() if ctx.live else None
    week = rolling_window(ctx.trading_date, days=days, now=now, config=cfg)
    today = session_window(ctx.trading_date, now=now, config=cfg)
    return week, today


def fetch_section(
    ctx,
    section: SectionId,
    *,
    sector_names: list[str] | None = None,
    client: Any = None,
) -> SectionRetrieval:
    from ai_insight.common import entity_retrieval

    if section == "market_driver_digest":
        pack = entity_retrieval.fetch_market_driver(ctx, client=client)
    elif section == "fii_dii_flow_narrative":
        pack = entity_retrieval.fetch_fii_dii(ctx, client=client)
    elif section == "sector_index_insights" and sector_names:
        pack = entity_retrieval.fetch_sector_index(ctx, sector_names, client=client)
    else:
        pack = _fetch_section_broad(ctx, section, sector_names=sector_names, client=client)
    if ctx.artifacts is not None:
        ctx.artifacts.write_json(
            "evidence_meta.json",
            [
                {
                    "cluster_id": item.cluster_id,
                    "title": item.title,
                    "url": item.url,
                    "source": item.source,
                    "published_at": item.published_at,
                    "entity": item.entity,
                    "impact": item.impact,
                    "direction": item.direction,
                    "text_chars": len(item.full_text or ""),
                }
                for item in pack.evidence
            ],
        )
    return pack


def _fetch_section_broad(
    ctx,
    section: SectionId,
    *,
    sector_names: list[str] | None = None,
    client: Any = None,
) -> SectionRetrieval:
    week, today = plan_window(ctx, section)
    cfg = ctx.config
    names = sector_names
    specs: list[tuple[str, list[str] | None]] = []
    if section in {"additional_insights"}:
        specs.append(("macro", None))
        specs.append(("sector", None))
    elif section == "sector_leaderboard":
        specs.append(("sector", None))
        specs.append(("macro", None))
    elif section == "sector_index_insights":
        specs.append(("sector", names))
        specs.append(("macro", None))
    rows: list[dict[str, Any]] = []
    diag: dict[str, Any] = {}
    gate = RELAXED_GATE

    def one(entity_type: str, entity_names: list[str] | None) -> None:
        result = fetch_entity_rows(
            entity_type,
            week,
            entity_names,
            gate=gate,
            client=client,
            log=ctx.log,
        )
        diag[f"{entity_type}:{len(entity_names or [])}"] = {
            "passed": result.diagnostics.entities_passed,
            "scanned": result.diagnostics.articles_scanned,
        }
        rows.extend(_tag_rows(result.rows, week, today))

    workers = min(3, len(specs))
    if workers <= 1:
        for entity_type, entity_names in specs:
            one(entity_type, entity_names)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(one, t, n) for t, n in specs]
            for future in as_completed(futures):
                future.result()

    top = max(6, cfg.max_clusters)
    clusters = rank_clusters(cluster_rows(rows, top_clusters=top * 2))[:top]
    per = max(3, cfg.per_cluster_articles)
    evidence = pick_evidence(clusters, per_cluster=per)
    evidence, dropped = enforce_prompt_budget(evidence, cfg.max_prompt_chars)
    diag["dropped_for_budget"] = len(dropped)
    return SectionRetrieval(rows, clusters, evidence, week, today, diag)


def _tag_rows(rows: list[dict], week: tuple[str, str], today: tuple[str, str]) -> list[dict]:
    end = _parse(week[1])
    today_start = _parse(today[0])
    out: list[dict] = []
    for row in rows:
        article = row.get("article") or {}
        pub = parse_time(str(article.get("published_at") or ""))
        tagged = dict(row)
        if pub is not None:
            tagged["age_days"] = max(0, (end.date() - pub.astimezone(end.tzinfo).date()).days)
            tagged["is_today"] = pub >= today_start
        else:
            tagged["age_days"] = None
            tagged["is_today"] = False
        out.append(tagged)
    return out


def _parse(value: str) -> datetime:
    from news_pipeline.textutil import parse_time

    parsed = parse_time(value)
    if parsed is None:
        raise ValueError(value)
    return parsed