"""Ask Jev which titles are material. Keep at most five per name."""

from __future__ import annotations

import logging

from news_pipeline.graph.state import PipelineState
from news_pipeline.graph.timing import merge_llm_usage
from news_pipeline.jev.client import JevClient, JevError, read_noul, title_questions
from news_pipeline.services import get_settings

logger = logging.getLogger(__name__)


def jev_title_screen(state: PipelineState) -> dict:
    settings = get_settings()
    entities = {entity["name"]: entity for entity in state.get("entities") or []}
    candidates = state.get("candidates") or []
    errors = list(state.get("errors") or [])

    by_name: dict[str, list[dict]] = {}
    for index, candidate in enumerate(candidates):
        for match in candidate["matches"]:
            by_name.setdefault(match["name"], []).append({"index": index, "title": candidate["title"]})

    relevance: dict[tuple[int, str], float] = {}
    llm_usage = dict(state.get("llm_usage") or {})
    try:
        client = JevClient(settings)
    except JevError as exc:
        errors.append({"stage": "jev_title_screen", "error": str(exc)})
        counts = dict(state.get("counts") or {})
        counts["after_title_jev"] = 0
        return {"candidates": [], "counts": counts, "errors": errors}

    with client:
        for name, rows in by_name.items():
            entity = entities.get(name)
            if entity is None:
                continue
            rows.sort(key=lambda row: candidates[row["index"]].get("published_at") or "", reverse=True)
            selected = rows[: settings.max_titles_per_jev_call]
            questions_rows = []
            id_to_index = {}
            for local_id, row in enumerate(selected):
                question_id = f"t{local_id}"
                questions_rows.append({"question_id": question_id, "title": row["title"]})
                id_to_index[question_id] = row["index"]
            try:
                answers = client.evaluate(
                    {
                        "name": entity["name"],
                        "type": entity["type"],
                        "aliases": entity["aliases"],
                        "keywords": entity["keywords"],
                    },
                    title_questions(questions_rows, entity),
                    stage="jev_title_screen",
                    detail=f"entity={name}",
                )
            except JevError as exc:
                errors.append({"stage": "jev_title_screen", "name": name, "error": str(exc)})
                continue
            llm_usage = merge_llm_usage(llm_usage, client.last_call_usage())
            for question_id, index in id_to_index.items():
                relevance[(index, name)] = read_noul(answers.get(question_id))

    scored_matches: dict[int, list[dict]] = {}
    by_entity: dict[str, list[tuple[int, float]]] = {}
    for index, candidate in enumerate(candidates):
        for match in candidate["matches"]:
            score = relevance.get((index, match["name"]))
            if score is None or score < settings.title_noul_min:
                continue
            scored_matches.setdefault(index, []).append({**match, "title_relevance": round(score, 4)})
            by_entity.setdefault(match["name"], []).append((index, score))

    allowed: set[tuple[int, str]] = set()
    for name, rows in by_entity.items():
        rows.sort(key=lambda item: item[1], reverse=True)
        for index, _score in rows[: settings.max_scrape_per_entity]:
            allowed.add((index, name))

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
    logger.info("jev_title_screen kept=%s", len(kept))
    return {"candidates": kept, "counts": counts, "errors": errors, "llm_usage": llm_usage}
