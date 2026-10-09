"""Resolve Google News links, fetch the publisher page, extract article text."""

from __future__ import annotations

from lib.extract import extract_article
from lib.fetch import fetch_url
from lib.google_news import cached_resolve, is_google_news_article_url
from news_pipeline.retry_backoff import sleep_before_attempt
from news_pipeline.services import get_settings


def scrape_one(session, input_url, retries=2):
    settings = get_settings()
    max_attempts = max(1, settings.scrape_max_attempts)
    backoff_base = settings.scrape_backoff_base_sec

    record = {
        "input_url": input_url,
        "title": None,
        "date": None,
        "text": "",
        "status": "ok",
        "error": None,
    }

    resolved_url = input_url
    if is_google_news_article_url(input_url):
        resolved_url, error = cached_resolve(
            session,
            input_url,
            retries=0,
            max_attempts=max_attempts,
            backoff_base_sec=backoff_base,
        )
        if error or not resolved_url:
            record["status"] = "resolve_failed"
            record["error"] = error or "could not resolve Google News URL"
            return record

    referer = input_url if is_google_news_article_url(input_url) else "https://news.google.com/"
    last_error = None
    html = None
    final_url = None
    for attempt in range(max_attempts):
        sleep_before_attempt(attempt, backoff_base)
        final_url, html, error = fetch_url(session, resolved_url, referer=referer, retries=0)
        if not error and html:
            break
        last_error = error or "empty publisher page"
    if not html:
        record["status"] = "fetch_failed"
        record["error"] = last_error
        return record

    extracted = extract_article(html, final_url or resolved_url)
    record.update(
        {
            "title": extracted["title"],
            "date": extracted["date"],
            "text": extracted["text"],
        }
    )
    if extracted["thin"]:
        record["status"] = "extract_thin"
        record["error"] = "extracted text is short; page may be JS-rendered or paywalled"
    return record
