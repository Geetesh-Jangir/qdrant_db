"""Ask Jev which titles are material. One System One call per entity with all titles in that call."""

from __future__ import annotations

import logging

from collections import defaultdict

from news_pipeline.entity_funnel import get_entity_funnel
from news_pipeline.graph.state import PipelineState
from news_pipeline.graph.timing import merge_llm_usage
from news_pipeline.error_summary import fetch_window_fields
from news_pipeline.jev.client import JevClient, JevError, read_noul, title_questions
from news_pipeline.run_log import clip_log_title, get_run_logger
from news_pipeline.services import get_settings
from news_pipeline.sources.macro_news import is_macro_match

logger = logging.getLogger(__name__)


def jev_title_screen(state: PipelineState) -> dict:
    settings = get_settings()
    entities = {entity["name"]: entity for entity in state.get("entities") or []}
    candidates = state.get("candidates") or []
    errors = list(state.get("errors") or [])
    run_log = get_run_logger()

    if run_log is not None:
        run_log.write(
            "jev_title_screen started "
            f"candidate_urls={len(candidates)} entities={len(entities)}"
        )

    relevance: dict[tuple[int, str], float] = {}
    title_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"pass": 0, "fail": 0})
    llm_usage = dict(state.get("llm_usage") or {})
    try:
        client = JevClient(settings)
    except JevError as exc:
        window = fetch_window_fields(settings)
        errors.append(
            {
                "source": "jev",
                "stage": "jev_title_screen",
                "error": str(exc),
                "dates": window["dates"],
                "window": window["window"],
            }
        )
        counts = dict(state.get("counts") or {})
        counts["after_title_jev"] = 0
        if run_log is not None:
            run_log.write(f"jev_title_screen aborted error={exc}")
        return {"candidates": [], "counts": counts, "errors": errors}

    with client:
        for name, entity in entities.items():
            entity_rows = _titles_for_entity(name, candidates)
            entity_rows.sort(
                key=lambda row: candidates[row["index"]].get("published_at") or "",
                reverse=True,
            )
            selected = _cap_titles(entity_rows, settings.max_titles_per_jev_call)
            if not selected:
                if run_log is not None:
                    run_log.write(f"jev_title_screen entity={name} type={entity['type']} titles=0 skipped")
                continue

            if run_log is not None:
                run_log.write(
                    f"jev_title_screen entity={name} type={entity['type']} "
                    f"titles_in_call={len(selected)}"
                )

            llm_usage = _score_entity_titles(
                client,
                entity,
                name,
                selected,
                candidates,
                relevance,
                title_stats,
                errors,
                llm_usage,
                run_log,
                settings,
            )

    scored_matches: dict[int, list[dict]] = {}
    by_entity: dict[str, list[tuple[int, float]]] = {}
    for index, candidate in enumerate(candidates):
        for match in candidate.get("matches") or []:
            score = relevance.get((index, match["name"]))
            if score is None:
                score = 0.5
            scored_matches.setdefault(index, []).append({**match, "title_relevance": round(score, 4)})
            by_entity.setdefault(match["name"], []).append((index, score))

    allowed: set[tuple[int, str]] = set()
    for entity_name, rows in by_entity.items():
        rows.sort(key=lambda item: item[1], reverse=True)
        for index, score in rows:
            allowed.add((index, entity_name))

    kept = []
    for index, candidate in enumerate(candidates):
        matches = [
            match
            for match in scored_matches.get(index, [])
            if (index, match["name"]) in allowed
        ]
        if matches:
            kept.append({**candidate, "matches": matches})

    counts = dict(state.get("counts") or {})
    counts["after_title_jev"] = len(kept)
    funnel = get_entity_funnel()
    for candidate in kept:
        for match in candidate.get("matches") or []:
            if match.get("name"):
                funnel.bump(match["name"], match.get("type") or "", "after_title_jev")
    if run_log is not None:
        run_log.write(f"jev_title_screen finished unique_urls_kept={len(kept)}")
        for industry, stats in sorted(title_stats.items()):
            run_log.write(
                f"jev_title_screen industry_stats industry={industry} "
                f"pass={stats['pass']} fail={stats['fail']}"
            )
    logger.info("jev_title_screen kept=%s", len(kept))
    return {"candidates": kept, "counts": counts, "errors": errors, "llm_usage": llm_usage}


def _cap_titles(rows: list[dict], max_titles: int) -> list[dict]:
    if max_titles <= 0:
        return rows
    return rows[:max_titles]


def _titles_for_entity(
    name: str,
    candidates: list[dict],
) -> list[dict]:
    seen: set[int] = set()
    rows: list[dict] = []
    for index, candidate in enumerate(candidates):
        for match in candidate.get("matches") or []:
            if match["name"] == name and index not in seen:
                seen.add(index)
                rows.append({"index": index, "title": candidate["title"]})
    return rows


def _entity_state(entity: dict) -> dict:
    return {
        "name": entity["name"],
        "type": entity["type"],
        "industry": entity.get("industry") or "",
        "aliases": entity["aliases"],
        "keywords": entity["keywords"],
    }


def _score_entity_titles(
    client: JevClient,
    entity: dict,
    name: str,
    rows: list[dict],
    candidates: list[dict],
    relevance: dict[tuple[int, str], float],
    title_stats: dict[str, dict[str, int]],
    errors: list[dict],
    llm_usage: dict,
    run_log,
    settings,
) -> dict:
    questions_rows = []
    id_to_index: dict[str, int] = {}
    for local_id, row in enumerate(rows):
        question_id = f"t{local_id}"
        questions_rows.append({"question_id": question_id, "title": row["title"]})
        id_to_index[question_id] = row["index"]
    try:
        answers = client.evaluate(
            _entity_state(entity),
            title_questions(questions_rows, entity),
            stage="jev_title_screen",
            detail=f"entity={name} titles={len(rows)}",
        )
    except JevError as exc:
        window = fetch_window_fields(settings)
        errors.append(
            {
                "source": "jev",
                "stage": "jev_title_screen",
                "name": name,
                "entities": [name],
                "error": str(exc),
                "dates": window["dates"],
                "window": window["window"],
            }
        )
        if run_log is not None:
            run_log.write(
                f"jev_title_screen entity={name} call_failed "
                f"dates={window['dates'] or 'relative_window'} error={exc}"
            )
        return llm_usage

    llm_usage = merge_llm_usage(llm_usage, client.last_call_usage())
    industry_key = (entity.get("industry") or name).strip() or name
    for question_id, index in id_to_index.items():
        score = read_noul(answers.get(question_id))
        relevance[(index, name)] = score
        if score >= settings.title_noul_min:
            title_stats[industry_key]["pass"] += 1
        else:
            title_stats[industry_key]["fail"] += 1
        if run_log is not None:
            verdict = "pass" if score >= settings.title_noul_min else "fail"
            run_log.write(
                f"jev_title_screen result entity={name} verdict={verdict} noul={score:.4f} "
                f"title={clip_log_title(candidates[index]['title'])}"
            )
    return llm_usage
