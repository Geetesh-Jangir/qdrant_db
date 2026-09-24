"""Merge entity tags and alias URLs onto an existing StoredArticle."""

from __future__ import annotations

from news_pipeline.models import EntityScore, StoredArticle


def merge_stored_article(
    existing: StoredArticle,
    added_entities: list[EntityScore],
    *,
    alias_urls: list[str] | None = None,
) -> StoredArticle:
    if not added_entities and not alias_urls:
        return existing

    by_name = {item.name: item for item in existing.entities}
    for item in added_entities:
        by_name[item.name] = item
    entities = list(by_name.values())

    aliases = list(existing.alias_urls)
    for url in alias_urls or []:
        cleaned = (url or "").strip()
        if cleaned and cleaned != existing.url and cleaned not in aliases:
            aliases.append(cleaned)

    lead = max(entities, key=lambda item: (item.impact, item.relevance, item.about_this_name))
    industries = sorted({item.industry for item in entities if item.industry})
    holding_names = sorted({item.name for item in entities if item.type == "holding"})
    sector_names = sorted({item.name for item in entities if item.type == "sector"})
    primary_industry = lead.industry or (industries[0] if len(industries) == 1 else "")
    if not primary_industry and industries:
        primary_industry = industries[0]

    return StoredArticle(
        url=existing.url,
        title=existing.title,
        source=existing.source,
        scraped_text=existing.scraped_text,
        published_at=existing.published_at,
        scraped_at=existing.scraped_at,
        entity_names=[item.name for item in entities],
        industry_names=industries,
        primary_industry=primary_industry,
        holding_names=holding_names,
        sector_names=sector_names,
        entities=entities,
        max_relevance=max(item.relevance for item in entities),
        max_impact=max(item.impact for item in entities),
        direction=lead.direction,
        event_type=lead.event_type,
        alias_urls=aliases,
    )


def payload_to_stored(data: dict) -> StoredArticle:
    payload = dict(data)
    payload["alias_urls"] = list(payload.get("alias_urls") or [])
    return StoredArticle.model_validate(payload)
