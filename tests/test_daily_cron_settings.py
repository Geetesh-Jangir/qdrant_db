"""Lightsail daily cron caps (NEWS_PIPELINE_DAILY=1)."""

import os
import unittest

from news_pipeline.config import Settings
from news_pipeline.services import get_settings


class DailyCronSettingsTests(unittest.TestCase):
    def tearDown(self) -> None:
        for key in ("NEWS_PIPELINE_DAILY", "HOLDINGS_LIMIT", "SCRAPE_WORKERS", "FETCH_WORKERS"):
            os.environ.pop(key, None)
        get_settings.cache_clear()

    def test_daily_flag_caps_holdings_and_scrape_workers(self) -> None:
        os.environ["NEWS_PIPELINE_DAILY"] = "1"
        get_settings.cache_clear()
        os.environ["HOLDINGS_LIMIT"] = "500"
        os.environ["SCRAPE_WORKERS"] = "4"
        os.environ["FETCH_WORKERS"] = "4"
        settings = get_settings()
        self.assertEqual(settings.holdings_limit, 250)
        self.assertEqual(settings.scrape_workers, 2)
        self.assertEqual(settings.fetch_workers, 1)


if __name__ == "__main__":
    unittest.main()