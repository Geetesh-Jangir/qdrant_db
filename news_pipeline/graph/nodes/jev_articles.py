"""Score each scraped article with Jev and drop weak matches."""

from __future__ import annotations

import logging

from news_pipeline.graph.state import PipelineState
from news_pipeline.graph.timing import merge_llm_usage
from news_pipeline.jev.client import JevClient, JevError, article_questions, score_match
from news_pipeline.services import get_settings
from news_pipeline.textutil import truncate_words

logger = logging.getLogger(__name__)


def jev_article_scores(state: PipelineState) -> dict:
    settings = get_settings()
    candidates = state.get("candidates") or []
    errors = list(state.get("errors") or [])
    entities = {entity["name"]: entity for entity in state.get("entities") or []}

    if not candidates:
        counts = dict(state.get("counts") or {})
        counts["after_body_jev"] = 0
        return {"candidates": [], "counts": counts, "errors": errors}

    kept = []
    llm_usage = dict(state.get("llm_usage") or {})
    try:
        client = JevClient(settings)
    except JevError as exc:
        errors.append({"stage": "jev_article_scores", "error": str(exc)})
        counts = dict(state.get("counts") or {})
        counts["after_body_jev"] = 0
        return {"candidates": [], "counts": counts, "errors": errors}

    with client:
        for candidate in candidates:
            matches = candidate["matches"]
            state_entities = []
            for match in matches:
                entity = entities.get(match["name"], {})
                state_entities.append(
                    {
                        "name": match["name"],
                        "type": match["type"],
                        "aliases": entity.get("aliases") or [],
                    }
                )
            try:
                answers = client.evaluate(
                    {
                        "title": candidate["title"],
                        "source": candidate["source"],
                        "published_at": candidate["published_at"],
                        "entities": state_entities,
                        "article": truncate_words(candidate["scraped_text"], settings.body_words),
                    },
                    article_questions(matches),
                    stage="jev_article_scores",
                    detail=f"url={candidate.get('url', '')}",
                )
            except JevError as exc:
                errors.append({"stage": "jev_article_scores", "url": candidate["url"], "error": str(exc)})
                continue

            llm_usage = merge_llm_usage(llm_usage, client.last_call_usage())
            scored = []
            for index, match in enumerate(matches):
                result = score_match(answers, index)
                if result["about_this_name"] < settings.about_name_min:
                    continue
                if result["relevance"] < settings.relevance_min:
                    continue
                scored.append({**match, **result})
            if scored:
                kept.append({**candidate, "matches": scored})

    counts = dict(state.get("counts") or {})
    counts["after_body_jev"] = len(kept)
    logger.info("jev_article_scores kept=%s", len(kept))
    return {"candidates": kept, "counts": counts, "errors": errors, "llm_usage": llm_usage}
