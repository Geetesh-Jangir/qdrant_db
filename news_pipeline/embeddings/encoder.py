"""Local Hugging Face embeddings. One model load per process."""

from __future__ import annotations

import time

from lib.embedding_cache import model_snapshot_exists, prepare_embedding_cache
from news_pipeline.config import QUERY_PREFIX, Settings
from news_pipeline.run_log import get_run_logger

_encoder: "Encoder | None" = None


class Encoder:
    def __init__(self, settings: Settings) -> None:
        from langchain_huggingface import HuggingFaceEmbeddings

        cache = prepare_embedding_cache(settings.path(settings.embedding_cache_dir))
        self._chars = settings.embed_chars
        self._model = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            cache_folder=str(cache),
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self._batch = settings.embed_batch

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch):
            chunk = texts[start : start + self._batch]
            vectors.extend(self._model.embed_documents(chunk))
        return vectors

    def embed_query(self, query: str) -> list[float]:
        text = query if query.startswith(QUERY_PREFIX) else QUERY_PREFIX + query
        return self._model.embed_query(text)


def get_encoder(settings: Settings) -> Encoder:
    global _encoder
    if _encoder is None:
        run_log = get_run_logger()
        model = settings.embedding_model
        cache = settings.path(settings.embedding_cache_dir)
        cached = model_snapshot_exists(cache, model)
        if run_log is not None:
            if cached:
                run_log.write(
                    f"embedding model loading model={model} cached_on_disk=true device=cpu"
                )
            else:
                run_log.write(
                    f"embedding model loading model={model} cached_on_disk=false "
                    f"note=first run downloads weights into {cache} (~130MB once); "
                    "hub progress may only show in the terminal not this log file"
                )
        started = time.perf_counter()
        _encoder = Encoder(settings)
        if run_log is not None:
            run_log.write(
                f"embedding model ready model={model} load_seconds={round(time.perf_counter() - started, 3)}"
            )
    return _encoder
