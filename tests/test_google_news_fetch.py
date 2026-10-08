"""Google News fetch: filter-before-resolve, cache, circuit breaker."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from lib.google_guard import GoogleBlockedError, google_breaker
from lib.url_cache import get_resolved, put_failure, put_resolved
from news_pipeline.config import Settings
from news_pipeline.sources.google_news import fetch_entity_items


RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss><channel>
  <item>
    <title>HDFC Bank results beat estimates</title>
    <link>https://news.google.com/rss/articles/CBMiabc</link>
    <pubDate>Wed, 01 Oct 2026 10:00:00 GMT</pubDate>
    <description><![CDATA[Snippet]]></description>
    <source url="https://www.moneycontrol.com">Moneycontrol</source>
  </item>
  <item>
    <title>Random blog post</title>
    <link>https://news.google.com/rss/articles/CBMixyz</link>
    <pubDate>Wed, 01 Oct 2026 10:00:00 GMT</pubDate>
    <description><![CDATA[Snippet]]></description>
    <source url="https://unknown.example.com">Unknown</source>
  </item>
</channel></rss>
"""


class TestGoogleNewsFetch(unittest.TestCase):
    def setUp(self):
        google_breaker.record_success()
        google_breaker._fails = 0
        google_breaker._until = 0.0

    @patch("news_pipeline.sources.google_news.fetch_url")
    @patch("news_pipeline.sources.google_news.cached_resolve")
    def test_filter_before_resolve_skips_non_allowlisted(self, mock_resolve, mock_fetch):
        mock_fetch.return_value = ("https://news.google.com/rss", RSS_SAMPLE, None)
        mock_resolve.return_value = ("https://www.moneycontrol.com/story", None)
        settings = Settings()
        settings.news_window_hours = 720
        entity = {
            "name": "HDFC Bank",
            "type": "holding",
            "query": "HDFC",
            "industry": "",
            "fund_count": 1,
            "total_percentage": 1.0,
        }
        kept = fetch_entity_items(entity, settings)
        self.assertEqual(len(kept), 1)
        self.assertEqual(mock_resolve.call_count, 1)

    @patch("lib.google_news.resolve_google_news_url")
    def test_cached_resolve_hits_network_once(self, mock_resolve):
        import lib.url_cache as url_cache

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.db"
            url_cache.reset_cache_db()

            with patch.object(url_cache, "_db_path", lambda: db):
                mock_resolve.return_value = ("https://www.livemint.com/a", None)
                wrapper = "https://news.google.com/rss/articles/CBMiabc"
                session = MagicMock()
                from lib.google_news import cached_resolve

                r1, _e1 = cached_resolve(session, wrapper, retries=0)
                r2, _e2 = cached_resolve(session, wrapper, retries=0)
                self.assertEqual(r1, "https://www.livemint.com/a")
                self.assertEqual(r2, "https://www.livemint.com/a")
                self.assertEqual(mock_resolve.call_count, 1)
            url_cache.reset_cache_db()

    def test_cached_failure_skips_retry(self):
        import lib.url_cache as url_cache

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.db"
            url_cache.reset_cache_db()
            wrapper = "https://news.google.com/rss/articles/CBMifail"

            with patch.object(url_cache, "_db_path", lambda: db):
                put_failure(wrapper)
                self.assertEqual(get_resolved(wrapper), "")
            url_cache.reset_cache_db()

    @patch("lib.fetch.make_session")
    def test_google_block_trips_breaker_without_fingerprint_retries(self, mock_make):
        from lib.fetch import fetch_url

        google_breaker._fails = 0
        google_breaker._until = 0.0
        session = MagicMock()
        response = MagicMock()
        response.status_code = 403
        response.url = "https://news.google.com/sorry/index"
        response.text = "unusual traffic"
        response.headers = {}
        session.get.return_value = response
        mock_make.return_value = session

        _final, _body, err = fetch_url(session, "https://news.google.com/rss/search?q=test", retries=2)
        self.assertIsNone(_final)
        self.assertIn("block", (err or "").lower())
        self.assertEqual(session.get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
