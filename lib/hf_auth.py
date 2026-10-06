"""Apply Hugging Face Hub token from settings for model downloads."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_applied = False


def configure_huggingface_token(token: str | None) -> None:
    """Set hub env vars and login once per process (no-op if token empty)."""
    global _applied
    raw = (token or "").strip()
    if not raw:
        return
    os.environ.setdefault("HF_TOKEN", raw)
    os.environ.setdefault("HUGGINGFACE_HUB_TOKEN", raw)
    os.environ.setdefault("HUGGING_FACE_HUB_TOKEN", raw)
    if _applied:
        return
    try:
        from huggingface_hub import login

        login(token=raw, add_to_git_credential=False)
        _applied = True
        logger.debug("Hugging Face hub token configured")
    except Exception as exc:
        logger.warning("Hugging Face login skipped: %s", exc)


def huggingface_model_kwargs(device: str = "cpu", token: str | None = None) -> dict:
    """model_kwargs for HuggingFaceEmbeddings / transformers when a token is set."""
    kwargs: dict = {"device": device}
    raw = (token or os.environ.get("HF_TOKEN") or "").strip()
    if raw:
        kwargs["token"] = raw
    return kwargs
