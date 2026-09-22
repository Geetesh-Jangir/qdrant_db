"""Resolve Google News links, fetch the publisher page, extract article text."""

from __future__ import annotations

from datetime import datetime, timezone

from lib.extract import extract_article
from lib.fetch import fetch_url
from lib.google_news import is_google_news_article_url, resolve_google_news_url


def scrape_one(session, input_url, retries=2):
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
        resolved_url, error = resolve_google_news_url(session, input_url, retries=retries)
        if error or not resolved_url:
            record["status"] = "resolve_failed"
            record["error"] = error or "could not resolve Google News URL"
            return record

    referer = input_url if is_google_news_article_url(input_url) else "https://news.google.com/"
    final_url, html, error = fetch_url(session, resolved_url, referer=referer, retries=retries)
    if error or not html:
        record["status"] = "fetch_failed"
        record["error"] = error or "empty publisher page"
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
