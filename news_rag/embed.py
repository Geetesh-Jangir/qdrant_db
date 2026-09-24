"""Local BGE embeddings — must match ingest model and QUERY_PREFIX in config."""

from __future__ import annotations

import logging

from langchain_huggingface import HuggingFaceEmbeddings

from lib.embedding_cache import model_snapshot_exists, prepare_embedding_cache
from news_rag.config import QUERY_PREFIX, get_settings

logger = logging.getLogger(__name__)

_encoder: HuggingFaceEmbeddings | None = None


def _build_encoder() -> HuggingFaceEmbeddings:
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
    global _encoder
    if _encoder is None:
        _encoder = _build_encoder()
    query = text if text.startswith(QUERY_PREFIX) else QUERY_PREFIX + text
    return _encoder.embed_query(query)
