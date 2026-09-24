"""Merge new entity tags and alias URLs onto existing Qdrant points (no duplicate articles)."""

from __future__ import annotations

import logging

from news_pipeline.graph.state import PipelineState
from news_pipeline.graph.timing import merge_llm_usage
from news_pipeline.jev.client import JevClient, JevError, article_questions, score_match
from news_pipeline.models import EntityScore
from news_pipeline.run_log import clip_log_title, get_run_logger
from news_pipeline.services import get_settings, get_store
from news_pipeline.storage.article_merge import merge_stored_article, payload_to_stored
from news_pipeline.textutil import truncate_words

logger = logging.getLogger(__name__)


def merge_entity_links(state: PipelineState) -> dict:
    settings = get_settings()
    errors = list(state.get("errors") or [])
    counts = dict(state.get("counts") or {})
    llm_usage = dict(state.get("llm_usage") or {})
    run_log = get_run_logger()
    entities = {entity["name"]: entity for entity in state.get("entities") or []}

    tasks: list[dict] = []
    for row in state.get("known_merges") or []:
        tasks.append(
            {
                "canonical_url": row["url"],
                "alias_url": None,
                "title": row.get("title") or "",
                "matches": list(row.get("matches") or []),
                "reason": "known_url",
            }
        )
    for row in state.get("canonical_merges") or []:
        tasks.append({**row, "reason": "similar_story"})

    if run_log is not None:
        run_log.write(f"merge_entity_links started tasks={len(tasks)}")

    if not tasks:
        counts["entity_links_merged"] = 0
        return {"counts": counts, "errors": errors, "llm_usage": llm_usage}

    store = get_store()
    merged_count = 0
    try:
        client = JevClient(settings)
    except JevError as exc:
        errors.append({"stage": "merge_entity_links", "error": str(exc)})
        counts["entity_links_merged"] = 0
        return {"counts": counts, "errors": errors, "llm_usage": llm_usage}

    with client:
        for task in tasks:
            canonical_url = task["canonical_url"]
            try:
                retrieved = store.retrieve_article(canonical_url)
            except Exception as exc:
                errors.append({"stage": "merge_entity_links", "url": canonical_url, "error": str(exc)})
                continue
            if retrieved is None:
                if run_log is not None:
                    run_log.write(f"merge_entity_links skip url={canonical_url} reason=not_in_qdrant")
                continue

            payload, vector = retrieved
            try:
                existing = payload_to_stored(payload)
            except Exception as exc:
                errors.append({"stage": "merge_entity_links", "url": canonical_url, "error": str(exc)})
                continue

            new_matches = [
                match
                for match in task.get("matches") or []
                if match["name"] not in existing.entity_names
            ]
            alias_urls: list[str] = []
            alias = (task.get("alias_url") or "").strip()
            if alias and alias != canonical_url:
                alias_urls.append(alias)

            if not new_matches and not alias_urls:
                if run_log is not None:
                    run_log.write(
                        f"merge_entity_links skip url={canonical_url} reason=no_new_entities_or_aliases"
                    )
                continue

            added: list[EntityScore] = []
            if new_matches:
                if run_log is not None:
                    names = ", ".join(m["name"] for m in new_matches)
                    run_log.write(
                        f"merge_entity_links jev_new_entities url={canonical_url} "
                        f"reason={task.get('reason')} entities=[{names}]"
                    )
                try:
                    added, llm_usage = _score_new_entities(
                        client,
                        settings,
                        entities,
                        existing,
                        new_matches,
                        llm_usage,
                        run_log,
                    )
                except JevError as exc:
                    errors.append(
                        {"stage": "merge_entity_links", "url": canonical_url, "error": str(exc)}
                    )
                    continue

            if not added and not alias_urls:
                if run_log is not None:
                    run_log.write(
                        f"merge_entity_links skip url={canonical_url} reason=jev_rejected_new_entities"
                    )
                continue

            merged = merge_stored_article(existing, added, alias_urls=alias_urls)
            store.upsert_one(merged, vector)
            merged_count += 1
            if run_log is not None:
                run_log.write(
                    f"merge_entity_links upserted url={canonical_url} "
                    f"entity_names={merged.entity_names} alias_urls={merged.alias_urls}"
                )

    counts["entity_links_merged"] = merged_count
    logger.info("merge_entity_links merged=%s", merged_count)
    if run_log is not None:
        run_log.write(f"merge_entity_links finished merged={merged_count}")
    return {"counts": counts, "errors": errors, "llm_usage": llm_usage}


def _score_new_entities(
    client: JevClient,
    settings,
    entities: dict[str, dict],
    existing,
    new_matches: list[dict],
    llm_usage: dict,
    run_log,
) -> tuple[list[EntityScore], dict]:
    body = (existing.scraped_text or "").strip()
    if len(body) < settings.min_body_chars:
        raise JevError(f"Stored body too short for merge jev url={existing.url}")

    state_entities = []
    for match in new_matches:
        entity = entities.get(match["name"], {})
        state_entities.append(
            {
                "name": match["name"],
                "type": match["type"],
                "industry": match.get("industry") or entity.get("industry") or "",
                "aliases": entity.get("aliases") or [],
            }
        )

    answers = client.evaluate(
        {
            "title": existing.title,
            "source": existing.source,
            "published_at": existing.published_at,
            "entities": state_entities,
            "article": truncate_words(body, settings.body_words),
        },
        article_questions(new_matches),
        stage="merge_entity_links",
        detail=f"url={existing.url}",
    )
    llm_usage = merge_llm_usage(llm_usage, client.last_call_usage())

    scored: list[EntityScore] = []
    for index, match in enumerate(new_matches):
        result = score_match(answers, index)
        if result["about_this_name"] < settings.about_name_min:
            if run_log is not None:
                run_log.write(
                    f"merge_entity_links drop entity={match['name']} reason=about_name "
                    f"about={result['about_this_name']:.4f}"
                )
            continue
        if result["relevance"] < settings.relevance_min:
            if run_log is not None:
                run_log.write(
                    f"merge_entity_links drop entity={match['name']} reason=relevance "
                    f"relevance={result['relevance']}"
                )
            continue
        title_rel = float(match.get("title_relevance") or 1.0)
        scored.append(
            EntityScore(
                name=match["name"],
                type=match["type"],
                industry=match.get("industry") or "",
                title_relevance=title_rel,
                about_this_name=float(result["about_this_name"]),
                relevance=int(result["relevance"]),
                impact=int(result["impact"]),
                direction=result["direction"],
                event_type=result["event_type"],
                affects_stock=float(result["affects_stock"]),
                affects_sector=float(result["affects_sector"]),
                affects_macro=float(result["affects_macro"]),
            )
        )
    return scored, llm_usage
