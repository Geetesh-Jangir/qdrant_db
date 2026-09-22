"""Google News RSS search for the last 24 hours, English, India."""

from __future__ import annotations

import logging
import threading
import time
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

from lib.fetch import fetch_url, thread_session
from lib.google_news import resolve_google_news_url
from news_pipeline.config import PUBLISHERS, Settings
from news_pipeline.run_log import get_run_logger
from news_pipeline.textutil import (
    canonical_url,
    host_matches,
    host_of,
    is_english_title,
    parse_time,
    strip_html,
    to_iso,
    utc_now,
    within_news_window,
)

logger = logging.getLogger(__name__)

_rss_lock = threading.Lock()
_last_rss_fetch = 0.0
_RSS_MIN_INTERVAL_SEC = 0.4


def fetch_entity_items(entity: dict, settings: Settings) -> list[dict]:
    now = utc_now()
    rss_url = (
        "https://news.google.com/rss/search?q="
        + quote_plus(f"{entity['query']} when:1d")
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )
    _wait_for_rss_slot()
    session = thread_session()
    _final, body, error = fetch_url(
        session,
        rss_url,
        referer="https://news.google.com/",
        retries=4,
    )
    if error or not body:
        raise RuntimeError(error or "empty Google News RSS response")
    items = _parse_rss(body.encode("utf-8"))
    kept: list[dict] = []
    for item in items:
        if len(kept) >= settings.max_items_per_query:
            break
        title = strip_html(item["title"])
        if not item["link"] or not title or not is_english_title(title):
            continue
        published = parse_time(item["published_raw"])
        if not within_news_window(published, settings.news_window_hours, now):
            continue
        resolved = _resolve_publisher_url(item["link"])
        source = _match_publisher(item["source_url"], item["source_name"], resolved)
        if source is None:
            continue
        url = canonical_url(resolved)
        if not url.startswith("https://"):
            continue
        kept.append(
            {
                "url": url,
                "title": title,
                "source": source,
                "published_at": to_iso(published) if published else None,
                "snippet": strip_html(item["description"])[:500],
                "entity_name": entity["name"],
                "entity_type": entity["type"],
                "fund_count": entity["fund_count"],
                "total_percentage": entity["total_percentage"],
            }
        )
    run_log = get_run_logger()
    if run_log is not None and len(items) > 0 and len(kept) == 0:
        run_log.write(
            f"fetch filter entity={entity['name']} rss_items={len(items)} kept=0 "
            "reason=publisher_or_time_or_language_filters"
        )
    elif run_log is not None and len(items) == 0:
        run_log.write(f"fetch filter entity={entity['name']} rss_items=0 kept=0 reason=empty_rss_feed")
    return kept


def _resolve_publisher_url(link: str) -> str:
    if "news.google.com" not in link:
        return link
    session = thread_session()
    resolved, _error = resolve_google_news_url(session, link, retries=1)
    return resolved or link


def _wait_for_rss_slot() -> None:
    global _last_rss_fetch
    with _rss_lock:
        now = time.monotonic()
        delay = _RSS_MIN_INTERVAL_SEC - (now - _last_rss_fetch)
        if delay > 0:
            time.sleep(delay)
        _last_rss_fetch = time.monotonic()


def _parse_rss(content: bytes) -> list[dict]:
    root = ET.fromstring(content)
    nodes = root.findall("./channel/item")
    if not nodes:
        nodes = [node for node in root.iter() if node.tag.endswith("item")]
    items = []
    for node in nodes:
        source = node.find("source")
        items.append(
            {
                "title": node.findtext("title") or "",
                "link": node.findtext("link") or "",
                "published_raw": node.findtext("pubDate") or "",
                "description": node.findtext("description") or "",
                "source_name": source.text if source is not None and source.text else "",
                "source_url": source.attrib.get("url", "") if source is not None else "",
            }
        )
    return items


def _match_publisher(source_url: str, source_name: str, article_url: str) -> str | None:
    hosts = [host_of(source_url), host_of(article_url)]
    article_host = host_of(article_url)
    label = (source_name or "").lower()
    for publisher in PUBLISHERS:
        if any(host_matches(host, publisher.domain) for host in hosts):
            return publisher.domain
        if article_host == "news.google.com" and any(name in label for name in publisher.names):
            return publisher.domain
    return None
