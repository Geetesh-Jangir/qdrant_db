"""Ask Jev which titles are material. One System One call per entity with all titles in that call."""

from __future__ import annotations

import logging

from collections import defaultdict

from news_pipeline.graph.state import PipelineState
from news_pipeline.graph.timing import merge_llm_usage
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

    macro_rows: list[dict] = []
    for index, candidate in enumerate(candidates):
        if any(is_macro_match(match) for match in candidate.get("matches") or []):
            macro_rows.append({"index": index, "title": candidate["title"]})

    if run_log is not None:
        run_log.write(
            "jev_title_screen started "
            f"candidate_urls={len(candidates)} macro_pool_titles={len(macro_rows)} "
            f"noul_min={settings.title_noul_min} max_scrape_per_entity={settings.max_scrape_per_entity} "
            f"max_scrape_per_industry={settings.max_scrape_per_industry}"
        )

    relevance: dict[tuple[int, str], float] = {}
    title_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"pass": 0, "fail": 0})
    llm_usage = dict(state.get("llm_usage") or {})
    try:
        client = JevClient(settings)
    except JevError as exc:
        errors.append({"stage": "jev_title_screen", "error": str(exc)})
        counts = dict(state.get("counts") or {})
        counts["after_title_jev"] = 0
        if run_log is not None:
            run_log.write(f"jev_title_screen aborted error={exc}")
        return {"candidates": [], "counts": counts, "errors": errors}

    with client:
        for name, entity in entities.items():
            if entity.get("type") == "macro":
                continue
            entity_rows, macro_only = _titles_for_entity(name, candidates, macro_rows)
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
                    f"titles_in_call={len(selected)} from_entity_query={len(entity_rows) - len(macro_only)} "
                    f"from_macro_pool={len(macro_only)}"
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
        for match in candidate["matches"]:
            if is_macro_match(match):
                continue
            score = relevance.get((index, match["name"]))
            if score is None or score < settings.title_noul_min:
                continue
            scored_matches.setdefault(index, []).append({**match, "title_relevance": round(score, 4)})
            by_entity.setdefault(match["name"], []).append((index, score))

    for index, candidate in enumerate(candidates):
        for match in candidate.get("matches") or []:
            if not is_macro_match(match):
                continue
            for entity_name, entity in entities.items():
                if entity.get("type") == "macro":
                    continue
                score = relevance.get((index, entity_name))
                if score is None or score < settings.title_noul_min:
                    continue
                scored_matches.setdefault(index, []).append(
                    {
                        "name": entity_name,
                        "type": entity["type"],
                        "industry": entity.get("industry") or "",
                        "fund_count": entity["fund_count"],
                        "total_percentage": entity["total_percentage"],
                        "title_relevance": round(score, 4),
                    }
                )
                by_entity.setdefault(entity_name, []).append((index, score))

    allowed: set[tuple[int, str]] = set()
    industry_picks: dict[str, int] = defaultdict(int)
    for entity_name, rows in by_entity.items():
        entity = entities.get(entity_name, {})
        industry_key = (entity.get("industry") or entity_name).casefold()
        rows.sort(key=lambda item: item[1], reverse=True)
        picked: list[tuple[int, float]] = []
        for index, score in rows:
            if len(picked) >= settings.max_scrape_per_entity:
                break
            if (
                entity.get("type") == "holding"
                and settings.max_scrape_per_industry > 0
                and industry_picks[industry_key] >= settings.max_scrape_per_industry
            ):
                if run_log is not None:
                    run_log.write(
                        f"jev_title_screen drop entity={entity_name} reason=industry_cap "
                        f"industry={entity.get('industry') or ''} noul={score:.4f} "
                        f"title={clip_log_title(candidates[index]['title'])}"
                    )
                continue
            picked.append((index, score))
            allowed.add((index, entity_name))
            if entity.get("type") == "holding":
                industry_picks[industry_key] += 1
        if run_log is not None:
            passed = len(rows)
            run_log.write(
                f"jev_title_screen entity={entity_name} passed_noul={passed} "
                f"selected_for_scrape={len(picked)} cap={settings.max_scrape_per_entity}"
            )
            for index, score in picked:
                run_log.write(
                    f"jev_title_screen keep entity={entity_name} noul={score:.4f} "
                    f"title={clip_log_title(candidates[index]['title'])} "
                    f"url={candidates[index].get('url', '')}"
                )
            for index, score in rows:
                if (index, entity_name) in allowed:
                    continue
                if score >= settings.title_noul_min and run_log is not None:
                    run_log.write(
                        f"jev_title_screen drop entity={entity_name} reason=not_selected noul={score:.4f} "
                        f"title={clip_log_title(candidates[index]['title'])}"
                    )

    for index, candidate in enumerate(candidates):
        for match in candidate.get("matches") or []:
            if is_macro_match(match):
                continue
            score = relevance.get((index, match["name"]))
            if score is None:
                continue
            if score < settings.title_noul_min and run_log is not None:
                run_log.write(
                    f"jev_title_screen drop entity={match['name']} reason=below_noul "
                    f"noul={score:.4f} min={settings.title_noul_min} "
                    f"title={clip_log_title(candidate['title'])}"
                )

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
    macro_rows: list[dict],
) -> tuple[list[dict], list[dict]]:
    seen: set[int] = set()
    rows: list[dict] = []
    macro_only: list[dict] = []
    for index, candidate in enumerate(candidates):
        for match in candidate.get("matches") or []:
            if is_macro_match(match):
                continue
            if match["name"] == name and index not in seen:
                seen.add(index)
                rows.append({"index": index, "title": candidate["title"]})
    for row in macro_rows:
        if row["index"] not in seen:
            seen.add(row["index"])
            rows.append(row)
            macro_only.append(row)
    return rows, macro_only


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
        errors.append({"stage": "jev_title_screen", "name": name, "error": str(exc)})
        if run_log is not None:
            run_log.write(f"jev_title_screen entity={name} call_failed error={exc}")
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
