"""Qdrant connection target (local Docker vs Qdrant Cloud)."""

from __future__ import annotations

from urllib.parse import urlparse

from news_pipeline.config import Settings


def qdrant_host(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.netloc:
        return parsed.netloc
    return url.strip().rstrip("/")


def is_qdrant_cloud(url: str) -> bool:
    host = qdrant_host(url).lower()
    return host.endswith(".cloud.qdrant.io") or host.endswith(".qdrant.io")


def validate_qdrant_settings(settings: Settings) -> None:
    url = (settings.qdrant_url or "").strip()
    if not url:
        raise SystemExit("Set QDRANT_URL (Qdrant Cloud cluster URL or http://localhost:6333).")
    if is_qdrant_cloud(url) and not (settings.qdrant_api_key or "").strip():
        raise SystemExit("QDRANT_API_KEY is required when QDRANT_URL points to Qdrant Cloud.")


def qdrant_summary(settings: Settings) -> dict:
    return {
        "url_host": qdrant_host(settings.qdrant_url),
        "collection": settings.collection_name,
        "cloud": is_qdrant_cloud(settings.qdrant_url),
    }
