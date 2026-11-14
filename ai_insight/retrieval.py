"""Read-time score gate. Insertion stores every scored entity; this is where quality is applied."""

from __future__ import annotations

from qdrant_client.http import models as rest

from news_rag.qdrant_reader import build_filter

# Digests want a material story. 3 is "material print / policy / flow" on the 0-4 relevance scale.
DIGEST_MIN_RELEVANCE = 3
DIGEST_MIN_IMPACT = 2


def digest_filter(
    *,
    entity_names: list[str] | None,
    published_from: str,
    published_to: str | None = None,
    min_relevance: int = DIGEST_MIN_RELEVANCE,
    min_impact: int | None = DIGEST_MIN_IMPACT,
    direction: str | None = None,
) -> rest.Filter:
    """Qdrant payload has max_relevance and max_impact, not a stored about-score, so those two are the gate.

    Callers still drop event_type price_recap after the scroll, the same way news_rag.qdrant_reader does.
    """
    return build_filter(
        entity_names=entity_names,
        published_from=published_from,
        published_to=published_to,
        min_relevance=min_relevance,
        min_impact=min_impact,
        direction=direction,
    )
