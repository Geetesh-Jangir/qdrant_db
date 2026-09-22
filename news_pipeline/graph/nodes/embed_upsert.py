"""Embed title plus the start of the body, then upsert one point per URL."""

from __future__ import annotations

import logging

from news_pipeline.embeddings.encoder import get_encoder
from news_pipeline.graph.state import PipelineState
from news_pipeline.run_log import get_run_logger
from news_pipeline.models import EntityScore, StoredArticle
from news_pipeline.services import get_settings, get_store
from news_pipeline.scrape.workspace import remove_scrape_artifacts_many
from news_pipeline.textutil import embedding_text

logger = logging.getLogger(__name__)


def embed_and_upsert(state: PipelineState) -> dict:
    settings = get_settings()
    candidates = state.get("candidates") or []
    errors = list(state.get("errors") or [])
    counts = dict(state.get("counts") or {})

    articles: list[StoredArticle] = []
    texts: list[str] = []
    for candidate in candidates:
        try:
            article = _to_article(candidate)
        except ValueError as exc:
            errors.append({"stage": "embed_and_upsert", "url": candidate.get("url"), "error": str(exc)})
            continue
        articles.append(article)
        texts.append(embedding_text(article.title, article.scraped_text, settings.embed_chars))

    if not articles:
        counts["upserted"] = 0
        logger.info("embed_and_upsert upserted=0")
        return {"counts": counts, "errors": errors}

    run_log = get_run_logger()
    if run_log is not None:
        run_log.write(f"embedding encode started documents={len(texts)} batch={settings.embed_batch}")

    vectors = get_encoder(settings).embed_documents(texts)

    if run_log is not None:
        run_log.write(f"embedding encode finished vectors={len(vectors)}")
    written = get_store().upsert_articles(articles, vectors)
    removed_files = remove_scrape_artifacts_many(settings, [article.url for article in articles])
    counts["upserted"] = written
    counts["scrape_files_removed"] = removed_files
    logger.info("embed_and_upsert upserted=%s scrape_files_removed=%s", written, removed_files)
    return {"counts": counts, "errors": errors}


def _to_article(candidate: dict) -> StoredArticle:
    entities = []
    for match in candidate["matches"]:
        entities.append(
            EntityScore(
                name=match["name"],
                type=match["type"],
                title_relevance=float(match["title_relevance"]),
                about_this_name=float(match["about_this_name"]),
                relevance=int(match["relevance"]),
                impact=int(match["impact"]),
                direction=match["direction"],
                event_type=match["event_type"],
                affects_stock=float(match["affects_stock"]),
                affects_sector=float(match["affects_sector"]),
                affects_macro=float(match["affects_macro"]),
                fund_count=int(match["fund_count"]),
            )
        )
    if not entities:
        raise ValueError("Article has no scored entities")

    lead = max(entities, key=lambda item: (item.impact, item.relevance, item.about_this_name))
    return StoredArticle(
        url=candidate["url"],
        title=candidate["title"],
        source=candidate["source"],
        scraped_text=candidate["scraped_text"],
        published_at=candidate["published_at"],
        scraped_at=candidate["scraped_at"],
        entity_names=[item.name for item in entities],
        entities=entities,
        max_relevance=max(item.relevance for item in entities),
        max_impact=max(item.impact for item in entities),
        direction=lead.direction,
        event_type=lead.event_type,
    )
