"""Google News RSS search (window from settings.google_news_when), English, India."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

from lib.fetch import fetch_url, thread_session
from lib.google_guard import google_breaker
from lib.google_news import cached_resolve, is_google_news_article_url
from news_pipeline.config import PUBLISHERS, Settings
from news_pipeline.entity_funnel import get_entity_funnel
from news_pipeline.failure_ledger import is_google_exhausted, record_google_failure
from news_pipeline.news_dates import article_in_fetch_window, google_time_query
from news_pipeline.publisher_stats import get_publisher_stats
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
)


def fetch_entity_items(entity: dict, settings: Settings) -> list[dict]:
    google_breaker.assert_allowed()
    now = utc_now()
    time_q = google_time_query(settings)
    rss_url = (
        "https://news.google.com/rss/search?q="
        + quote_plus(f"{entity['query']} {time_q}")
        + "&hl=en-IN&gl=IN&ceid=IN:en"
    )
    funnel = get_entity_funnel()
    ename = entity["name"]
    etype = entity["type"]
    session = thread_session()
    _final, body, error = fetch_url(
        session,
        rss_url,
        referer="https://news.google.com/",
        retries=2,
    )
    if error or not body:
        record_google_failure(
            settings,
            url=rss_url,
            kind="rss_fetch",
            error=error or "empty Google News RSS response",
            entities=[{"name": ename, "type": etype}],
            entity_query=entity.get("query") or "",
        )
        raise RuntimeError(error or "empty Google News RSS response")
    items = _parse_rss(body.encode("utf-8"))
    funnel.bump(ename, etype, "rss_items", len(items))
    kept: list[dict] = []
    dropped_publisher = 0
    dropped_pre_resolve = 0
    resolve_calls = 0
    cap = getattr(settings, "max_items_per_query", 0)

    for item in items:
        title = strip_html(item["title"])
        if not item["link"] or not title or not is_english_title(title):
            dropped_pre_resolve += 1
            continue
        published = parse_time(item["published_raw"])
        if not article_in_fetch_window(published, settings, now):
            dropped_pre_resolve += 1
            continue

        source = _match_publisher(item["source_url"], item["source_name"], item["link"])
        if source is None:
            dropped_publisher += 1
            continue

        wrapper = item["link"]
        if is_google_news_article_url(wrapper) and is_google_exhausted(wrapper, settings):
            funnel.bump(ename, etype, "resolve_failed")
            continue

        resolve_calls += 1
        resolved = _resolve_publisher_url(session, item["link"], settings)
        if not resolved:
            funnel.bump(ename, etype, "resolve_failed")
            record_google_failure(
                settings,
                url=wrapper,
                kind="resolve",
                error="could not resolve Google News URL",
                title=title,
                snippet=strip_html(item["description"])[:500],
                published_at=to_iso(published) if published else None,
                source_name=item.get("source_name") or "",
                entities=[{"name": ename, "type": etype}],
            )
            continue

        url = canonical_url(resolved)
        if not url.startswith("https://"):
            dropped_pre_resolve += 1
            continue
        funnel.bump(ename, etype, "google_kept")
        get_publisher_stats().record_received(source, url)
        kept.append(
            {
                "url": url,
                "title": title,
                "source": source,
                "published_at": to_iso(published) if published else None,
                "snippet": strip_html(item["description"])[:500],
                "entity_name": entity["name"],
                "entity_type": entity["type"],
                "entity_industry": entity.get("industry") or "",
                "fund_count": entity["fund_count"],
                "total_percentage": entity["total_percentage"],
            }
        )

    funnel.bump(ename, etype, "dropped_before_resolve", dropped_pre_resolve + dropped_publisher)

    run_log = get_run_logger()
    if run_log is not None:
        run_log.write(
            f"fetch filter entity={entity['name']} rss_items={len(items)} "
            f"dropped_publisher={dropped_publisher} dropped_pre_resolve={dropped_pre_resolve} "
            f"resolve_calls={resolve_calls} kept={len(kept)} "
            f"max_items_per_query={'unlimited' if cap <= 0 else cap}"
        )
        if len(items) > 0 and len(kept) == 0:
            run_log.write(
                f"fetch filter entity={entity['name']} reason=publisher_or_time_or_language_filters"
            )
        elif len(items) == 0:
            run_log.write(f"fetch filter entity={entity['name']} rss_items=0 kept=0 reason=empty_rss_feed")
    return kept


def _resolve_publisher_url(session, link: str, settings: Settings) -> str | None:
    if "news.google.com" not in link:
        return link
    resolved, _error = cached_resolve(
        session,
        link,
        retries=0,
        max_attempts=settings.scrape_max_attempts,
        backoff_base_sec=settings.scrape_backoff_base_sec,
    )
    return resolved


def _parse_rss(content: bytes) -> list[dict]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []
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
