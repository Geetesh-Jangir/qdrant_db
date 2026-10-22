"""Scrape one news URL with the same stack as the daily pipeline (scrape_bodies)."""

from __future__ import annotations

from typing import Any

from lib.fetch import thread_session
from news_pipeline.scrape.domain_gap import wait_for_domain
from news_pipeline.scrape.engine import scrape_one
from news_pipeline.services import get_settings


class ScrapeArticleError(Exception):
    """Resolve or fetch failed; see `.record` for the scrape_one payload."""

    def __init__(self, message: str, record: dict[str, Any]) -> None:
        super().__init__(message)
        self.record = record


def scrape_article_url(
    url: str,
    *,
    title_fallback: str = "",
    snippet_fallback: str = "",
    respect_domain_gap: bool = True,
    raise_on_thin: bool = False,
) -> dict[str, Any]:
    """
    Fetch and extract article text from a publisher URL or Google News wrapper URL.

    Uses ``scrape_one`` (trafilatura + HTML fallback), optional domain rate gap,
    and the same short-body fallback as ``scrape_bodies`` (title + snippet).

    Returns a dict with at least:
      input_url, title, date, text, status, error

    ``status`` is ``ok`` when extraction succeeded; ``extract_thin`` when text is
    short (paywall / JS / boilerplate). Raises ``ScrapeArticleError`` on
    ``resolve_failed`` or ``fetch_failed``. Raises ``ValueError`` if url is empty.

    Requires ``PYTHONPATH`` repo root and a normal ``.env`` if you rely on
    ``get_settings()`` overrides (scrape_max_attempts, etc.).
    """
    url = (url or "").strip()
    if not url:
        raise ValueError("url is required")

    settings = get_settings()
    if respect_domain_gap:
        wait_for_domain(url, settings.scrape_domain_gap_sec)

    record = scrape_one(thread_session(), url, retries=2)
    status = str(record.get("status") or "")
    if status in ("resolve_failed", "fetch_failed"):
        raise ScrapeArticleError(str(record.get("error") or status), record)

    text = (record.get("text") or "").strip()
    title = (record.get("title") or title_fallback or "").strip()

    if len(text) < settings.min_body_chars:
        snippet = (snippet_fallback or "").strip()
        if snippet:
            text = f"{title}. {snippet}".strip(" .")
        elif title:
            text = title

    out = dict(record)
    out["text"] = text
    out["title"] = title or record.get("title")

    if raise_on_thin and (record.get("status") == "extract_thin" or len(text) < settings.min_body_chars):
        raise ScrapeArticleError(
            str(record.get("error") or "extracted text too short"),
            out,
        )

    return out
