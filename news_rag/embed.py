"""Local BGE embeddings — must match ingest model and QUERY_PREFIX in config."""

from __future__ import annotations

import logging
from typing import Any

from lib.embedding_cache import model_snapshot_exists, prepare_embedding_cache
from news_rag.config import QUERY_PREFIX, get_settings

logger = logging.getLogger(__name__)

_encoder: Any | None = None
_embeddings_ready: bool = False


def embeddings_ready() -> bool:
    return _embeddings_ready


def _build_encoder() -> Any:
    from langchain_huggingface import HuggingFaceEmbeddings
    settings = get_settings()
    cache = prepare_embedding_cache(settings.embedding_cache_path())
    model = settings.embedding_model
    if model_snapshot_exists(cache, model):
        logger.info("embedding model cache hit model=%s dir=%s", model, cache)
    else:
        logger.info(
            "embedding model not in project cache yet; downloading model=%s into %s (~130MB once)",
            model,
            cache,
        )
    return HuggingFaceEmbeddings(
        model_name=model,
        cache_folder=str(cache),
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def embed_query(text: str) -> list[float]:
    global _encoder, _embeddings_ready
    if _encoder is None:
        _encoder = _build_encoder()
    query = text if text.startswith(QUERY_PREFIX) else QUERY_PREFIX + text
    vec = _encoder.embed_query(query)
    _embeddings_ready = True
    return vec
