"""Title dedupe per entity. Alias matching removed — Jev screens titles instead."""

from __future__ import annotations

import logging

from rapidfuzz import fuzz

from news_pipeline.graph.state import PipelineState
from news_pipeline.run_log import clip_log_title, get_run_logger
from news_pipeline.services import get_settings, get_store
from news_pipeline.textutil import normalize_title

logger = logging.getLogger(__name__)


def dedupe_and_alias(state: PipelineState) -> dict:
    settings = get_settings()
    entities = {entity["name"]: entity for entity in state.get("entities") or []}
    candidates = state.get("candidates") or []
    errors = list(state.get("errors") or [])
    run_log = get_run_logger()

    if run_log is not None:
        run_log.write(
            "dedupe_and_alias started "
            f"candidate_urls={len(candidates)} title_similarity={settings.title_similarity} "
            f"recent_title_hours={settings.recent_title_hours} alias_gate=off"
        )

    store = get_store()
    recent_by_name: dict[str, list[str]] = {}
    for entity in entities.values():
        try:
            recent = store.recent_titles(entity["name"], settings.recent_title_hours)
            recent_by_name[entity["name"]] = recent
            if run_log is not None:
                run_log.write(
                    f"dedupe_and_alias recent_titles entity={entity['name']} count={len(recent)}"
                )
        except Exception as exc:
            errors.append({"stage": "dedupe_and_alias", "name": entity["name"], "error": str(exc)})
            recent_by_name[entity["name"]] = []

    deduped, dropped = _drop_similar_titles(candidates, recent_by_name, settings.title_similarity, run_log)
    counts = dict(state.get("counts") or {})
    counts["after_alias"] = len(candidates)
    counts["after_title_dedupe"] = len(deduped)
    counts["title_dedupe_dropped"] = dropped
    if run_log is not None:
        run_log.write(
            f"dedupe_and_alias finished urls_before={len(candidates)} urls_after={len(deduped)} "
            f"urls_dropped={dropped}"
        )
    logger.info("dedupe_and_alias before_dedupe=%s after_dedupe=%s", len(candidates), len(deduped))
    return {"candidates": deduped, "counts": counts, "errors": errors}


def _drop_similar_titles(
    candidates: list[dict],
    recent_by_name: dict[str, list[str]],
    threshold: int,
    run_log,
) -> tuple[list[dict], int]:
    ordered = sorted(candidates, key=lambda row: row.get("published_at") or "", reverse=True)
    seen: dict[str, list[str]] = {name: list(titles) for name, titles in recent_by_name.items()}
    kept: list[dict] = []
    dropped_urls = 0
    for candidate in ordered:
        matches = []
        for match in candidate["matches"]:
            name = match["name"]
            prior = seen.setdefault(name, [])
            if _is_duplicate(candidate["title"], prior, threshold):
                if run_log is not None:
                    run_log.write(
                        f"dedupe_and_alias drop_match entity={name} reason=similar_title "
                        f"title={clip_log_title(candidate['title'])} url={candidate.get('url', '')}"
                    )
                continue
            prior.append(candidate["title"])
            matches.append(match)
        if matches:
            kept.append({**candidate, "matches": matches})
        else:
            dropped_urls += 1
            if run_log is not None:
                run_log.write(
                    f"dedupe_and_alias drop_url reason=all_matches_deduped "
                    f"title={clip_log_title(candidate['title'])} url={candidate.get('url', '')}"
                )
    return kept, dropped_urls


def _is_duplicate(title: str, prior_titles: list[str], threshold: int) -> bool:
    current = normalize_title(title)
    if not current:
        return False
    for prior in prior_titles:
        other = normalize_title(prior)
        if not other:
            continue
        if current == other:
            return True
        if min(len(current), len(other)) < 18:
            continue
        if fuzz.token_set_ratio(current, other) >= threshold:
            return True
    return False
