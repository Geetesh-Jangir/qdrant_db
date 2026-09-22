"""Local Hugging Face embeddings. One model load per process."""

from __future__ import annotations

import time
from pathlib import Path

from news_pipeline.config import QUERY_PREFIX, Settings
from news_pipeline.run_log import get_run_logger

_encoder: "Encoder | None" = None


def _model_cached_on_disk(model_name: str) -> bool:
    slug = model_name.replace("/", "--")
    cache_root = Path.home() / ".cache" / "huggingface" / "hub"
    return (cache_root / f"models--{slug}").is_dir()


class Encoder:
    def __init__(self, settings: Settings) -> None:
        from langchain_huggingface import HuggingFaceEmbeddings

        self._chars = settings.embed_chars
        self._model = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
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
        cached = _model_cached_on_disk(model)
        if run_log is not None:
            if cached:
                run_log.write(
                    f"embedding model loading model={model} cached_on_disk=true device=cpu"
                )
            else:
                run_log.write(
                    f"embedding model loading model={model} cached_on_disk=false "
                    "note=first run downloads weights from Hugging Face (~130MB); "
                    "hub progress may only show in the terminal not this log file"
                )
        started = time.perf_counter()
        _encoder = Encoder(settings)
        if run_log is not None:
            run_log.write(
                f"embedding model ready model={model} load_seconds={round(time.perf_counter() - started, 3)}"
            )
    return _encoder
