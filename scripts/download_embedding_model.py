"""Download BGE embedding weights once into data/embedding_models (shared by pipeline and RAG)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lib.embedding_cache import model_snapshot_exists, prepare_embedding_cache
from lib.hf_auth import configure_huggingface_token, huggingface_model_kwargs
from news_rag.config import get_settings

MODEL = "BAAI/bge-small-en-v1.5"
CACHE_DIR = _ROOT / "data" / "embedding_models"


def main() -> None:
    cache = prepare_embedding_cache(CACHE_DIR)
    if model_snapshot_exists(cache, MODEL):
        print(f"Model already cached: {MODEL}")
        print(f"Cache directory: {cache}")
        return

    settings = get_settings()
    configure_huggingface_token(settings.huggingface_token)
    print(f"Downloading {MODEL} into {cache} (one-time, ~130MB)...")
    from langchain_huggingface import HuggingFaceEmbeddings

    embedder = HuggingFaceEmbeddings(
        model_name=MODEL,
        cache_folder=str(cache),
        model_kwargs=huggingface_model_kwargs(device="cpu", token=settings.huggingface_token),
        encode_kwargs={"normalize_embeddings": True},
    )
    vector = embedder.embed_query("warmup")
    print(f"Done. Vector length={len(vector)} cache={cache}")


if __name__ == "__main__":
    main()
