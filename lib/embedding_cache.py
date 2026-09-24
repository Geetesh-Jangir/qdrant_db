"""Persistent on-disk cache for Hugging Face / sentence-transformers embedding models."""

from __future__ import annotations

import os
from pathlib import Path


def prepare_embedding_cache(cache_dir: Path) -> Path:
    """Point HF and sentence-transformers at a project folder so weights download once."""
    root = cache_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    # Only set if not already configured (respect user/global HF_HOME).
    os.environ.setdefault("HF_HOME", str(root))
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(root / "sentence_transformers"))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(root / "transformers"))
    os.environ.setdefault("HF_HUB_CACHE", str(root / "hub"))
    return root


def model_snapshot_exists(cache_dir: Path, model_name: str) -> bool:
    slug = model_name.replace("/", "--")
    hub = cache_dir / "hub" / f"models--{slug}"
    if hub.is_dir():
        return True
    legacy = Path.home() / ".cache" / "huggingface" / "hub" / f"models--{slug}"
    return legacy.is_dir()
