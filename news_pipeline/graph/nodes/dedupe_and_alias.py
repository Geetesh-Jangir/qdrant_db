"""Alias gate, then 80% title dedupe inside one stock or one sector."""

from __future__ import annotations

import logging

from rapidfuzz import fuzz

from news_pipeline.graph.state import PipelineState
from news_pipeline.services import get_settings, get_store
from news_pipeline.sources.matching import matches_entity
from news_pipeline.textutil import normalize_title

logger = logging.getLogger(__name__)


def dedupe_and_alias(state: PipelineState) -> dict:
    settings = get_settings()
    entities = {entity["name"]: entity for entity in state.get("entities") or []}
    candidates = state.get("candidates") or []
    errors = list(state.get("errors") or [])

    aliased = []
    for candidate in candidates:
        kept_matches = []
        for match in candidate["matches"]:
            entity = entities.get(match["name"])
            if entity is None:
                continue
            if matches_entity(candidate["title"], candidate.get("snippet") or "", entity):
                kept_matches.append(match)
        if kept_matches:
            aliased.append({**candidate, "matches": kept_matches})

    store = get_store()
    recent_by_name: dict[str, list[str]] = {}
    for entity in entities.values():
        try:
            recent_by_name[entity["name"]] = store.recent_titles(entity["name"], settings.recent_title_hours)
        except Exception as exc:
            errors.append({"stage": "dedupe_and_alias", "name": entity["name"], "error": str(exc)})
            recent_by_name[entity["name"]] = []

    deduped = _drop_similar_titles(aliased, recent_by_name, settings.title_similarity)
    counts = dict(state.get("counts") or {})
    counts["after_alias"] = len(aliased)
    counts["after_title_dedupe"] = len(deduped)
    logger.info("dedupe_and_alias after_alias=%s after_dedupe=%s", len(aliased), len(deduped))
    return {"candidates": deduped, "counts": counts, "errors": errors}


def _drop_similar_titles(candidates: list[dict], recent_by_name: dict[str, list[str]], threshold: int) -> list[dict]:
    ordered = sorted(candidates, key=lambda row: row.get("published_at") or "", reverse=True)
    seen: dict[str, list[str]] = {name: list(titles) for name, titles in recent_by_name.items()}
    kept: list[dict] = []
    for candidate in ordered:
        matches = []
        for match in candidate["matches"]:
            name = match["name"]
            prior = seen.setdefault(name, [])
            if _is_duplicate(candidate["title"], prior, threshold):
                continue
            prior.append(candidate["title"])
            matches.append(match)
        if matches:
            kept.append({**candidate, "matches": matches})
    return kept


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
