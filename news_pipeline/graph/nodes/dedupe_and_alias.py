"""Title dedupe per entity; similar stories merge onto a canonical URL instead of dropping entities."""

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
    story_index: list[dict] = []
    if settings.news_corpus_mode:
        try:
            story_index = store.corpus_entries(
                settings.corpus_title_dedupe_hours,
                settings.corpus_title_dedupe_limit,
            )
            if run_log is not None:
                hours_label = (
                    "all"
                    if settings.corpus_title_dedupe_hours <= 0
                    else str(settings.corpus_title_dedupe_hours)
                )
                limit_label = (
                    "unlimited"
                    if settings.corpus_title_dedupe_limit <= 0
                    else str(settings.corpus_title_dedupe_limit)
                )
                run_log.write(
                    "dedupe_and_alias corpus_entries_loaded "
                    f"count={len(story_index)} hours={hours_label} limit={limit_label}"
                )
        except Exception as exc:
            errors.append({"stage": "dedupe_and_alias", "error": str(exc), "scope": "corpus_entries"})
            if run_log is not None:
                run_log.write(f"dedupe_and_alias corpus_entries_load_fail error={exc}")

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

    deduped, dropped, canonical_merges = _dedupe_candidates(
        candidates,
        recent_by_name,
        story_index,
        settings.title_similarity,
        run_log,
    )
    counts = dict(state.get("counts") or {})
    counts["after_alias"] = len(candidates)
    counts["after_title_dedupe"] = len(deduped)
    counts["title_dedupe_dropped"] = dropped
    counts["canonical_story_merges"] = len(canonical_merges)
    if run_log is not None:
        run_log.write(
            f"dedupe_and_alias finished urls_before={len(candidates)} urls_after={len(deduped)} "
            f"urls_dropped={dropped} canonical_merges={len(canonical_merges)}"
        )
    logger.info("dedupe_and_alias before_dedupe=%s after_dedupe=%s", len(candidates), len(deduped))
    return {
        "candidates": deduped,
        "canonical_merges": canonical_merges,
        "counts": counts,
        "errors": errors,
    }


def _dedupe_candidates(
    candidates: list[dict],
    recent_by_name: dict[str, list[str]],
    story_index: list[dict],
    threshold: int,
    run_log,
) -> tuple[list[dict], int, list[dict]]:
    ordered = sorted(candidates, key=lambda row: row.get("published_at") or "", reverse=True)
    seen: dict[str, list[str]] = {name: list(titles) for name, titles in recent_by_name.items()}
    run_stories: list[dict] = list(story_index)
    kept_by_url: dict[str, dict] = {}
    kept: list[dict] = []
    dropped_urls = 0
    canonical_merges: list[dict] = []

    for candidate in ordered:
        canonical = _find_story_match(candidate["title"], run_stories, threshold)
        if canonical and canonical["url"] != candidate["url"]:
            if canonical["url"] in kept_by_url:
                _absorb_into_candidate(kept_by_url[canonical["url"]], candidate, run_log)
            else:
                canonical_merges.append(
                    {
                        "canonical_url": canonical["url"],
                        "alias_url": candidate["url"],
                        "title": candidate["title"],
                        "source": candidate.get("source") or "",
                        "published_at": candidate.get("published_at"),
                        "matches": list(candidate.get("matches") or []),
                    }
                )
                if run_log is not None:
                    run_log.write(
                        "dedupe_and_alias redirect_story "
                        f"alias_url={candidate.get('url', '')} canonical_url={canonical['url']} "
                        f"title={clip_log_title(candidate['title'])}"
                    )
            continue

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
            row = {**candidate, "matches": matches}
            if "_alias_urls" not in row:
                row["_alias_urls"] = []
            kept.append(row)
            kept_by_url[row["url"]] = row
            run_stories.append({"title": candidate["title"], "url": candidate["url"]})
        else:
            dropped_urls += 1
            if run_log is not None:
                run_log.write(
                    f"dedupe_and_alias drop_url reason=all_matches_deduped "
                    f"title={clip_log_title(candidate['title'])} url={candidate.get('url', '')}"
                )
    return kept, dropped_urls, canonical_merges


def _absorb_into_candidate(target: dict, source: dict, run_log) -> None:
    aliases = list(target.get("_alias_urls") or [])
    alias = (source.get("url") or "").strip()
    if alias and alias != target["url"] and alias not in aliases:
        aliases.append(alias)
    target["_alias_urls"] = aliases
    existing_names = {m["name"] for m in target.get("matches") or []}
    for match in source.get("matches") or []:
        if match["name"] not in existing_names:
            target.setdefault("matches", []).append(match)
            existing_names.add(match["name"])
    if run_log is not None:
        names = ", ".join(m["name"] for m in source.get("matches") or [])
        run_log.write(
            "dedupe_and_alias absorb_same_run_story "
            f"canonical_url={target.get('url', '')} alias_url={alias} merged_matches=[{names}]"
        )


def _find_story_match(title: str, stories: list[dict], threshold: int) -> dict | None:
    for story in stories:
        if _is_duplicate(title, [story["title"]], threshold):
            return story
    return None


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
