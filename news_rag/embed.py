"""Local BGE embeddings — must match ingest model and QUERY_PREFIX in config."""

from __future__ import annotations

import logging
from typing import Any

from lib.embedding_cache import model_snapshot_exists, prepare_embedding_cache
from lib.hf_auth import configure_huggingface_token, huggingface_model_kwargs
from news_rag.config import QUERY_PREFIX, get_settings

logger = logging.getLogger(__name__)

_encoder: Any | None = None
_embeddings_ready: bool = False


def embeddings_ready() -> bool:
    return _embeddings_ready


def _build_encoder() -> Any:
    settings = get_settings()
    configure_huggingface_token(settings.huggingface_token)
    cache = prepare_embedding_cache(settings.embedding_cache_path())
    model = settings.embedding_model
    model_kwargs = huggingface_model_kwargs(device="cpu", token=settings.huggingface_token)
    if model_snapshot_exists(cache, model):
        logger.info("embedding model cache hit model=%s dir=%s", model, cache)
    else:
        logger.info(
            "embedding model not in project cache yet; downloading model=%s into %s (~130MB once)",
            model,
            cache,
        )

    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name=model,
            cache_folder=str(cache),
            model_kwargs=model_kwargs,
            encode_kwargs={"normalize_embeddings": True},
        )
    except ImportError:
        pass

    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name=model,
            cache_folder=str(cache),
            model_kwargs=model_kwargs,
            encode_kwargs={"normalize_embeddings": True},
        )
    except ImportError:
        pass

    try:
        from sentence_transformers import SentenceTransformer

        class _SentenceTransformerAdapter:
            def __init__(self, model_name: str, cache_folder: str, token: str):
                kwargs: dict = {}
                if token:
                    kwargs["token"] = token
                self._st = SentenceTransformer(
                    model_name, cache_folder=cache_folder, device="cpu", **kwargs
                )

            def embed_query(self, text: str) -> list[float]:
                vec = self._st.encode(text, normalize_embeddings=True)
                return [float(x) for x in vec]

        return _SentenceTransformerAdapter(model, str(cache), settings.huggingface_token)
    except ImportError:
        raise ImportError(
            "No embedding backend found. Please install langchain-huggingface, langchain-community, or sentence-transformers."
        )


def embed_query(text: str) -> list[float]:
    global _encoder, _embeddings_ready
    if _encoder is None:
        _encoder = _build_encoder()
    query = text if text.startswith(QUERY_PREFIX) else QUERY_PREFIX + text
    vec = _encoder.embed_query(query)
    _embeddings_ready = True
    return vec
