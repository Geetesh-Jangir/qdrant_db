from __future__ import annotations

import unittest

from news_rag.insights import analyst_line_from_article
from news_rag.snippet_clean import (
    clean_scraped_snippet,
    looks_like_raw_scrape,
    sanitize_analyst_bullet,
)


class TestSnippetClean(unittest.TestCase):
    def test_strips_outlet_and_pti(self):
        raw = (
            "Livemint( with inputs from PTI) Updated8 Sep 2026, 05:01 PM IST "
            "India's oil import bill is set to jump as Brent futures gained over 2%."
        )
        cleaned = clean_scraped_snippet(raw)
        self.assertNotIn("Livemint", cleaned)
        self.assertNotIn("PTI", cleaned)
        self.assertIn("Brent", cleaned)

    def test_strips_min_read_and_weekday_date(self):
        raw = (
            "3 Min Read Shares of Solar Industries India Ltd. fell about 12% on Tuesday, "
            "September 15, after the company's unit agreed to acquire South Africa-based "
            "Omnia Holdings for ₹12,951 crore."
        )
        cleaned = clean_scraped_snippet(raw)
        self.assertNotIn("Min Read", cleaned)
        self.assertNotIn("Tuesday", cleaned)
        self.assertNotIn("September 15", cleaned)
        self.assertIn("Solar Industries", cleaned)
        self.assertIn("12%", cleaned)

    def test_strips_ad_banner_and_publish_timestamp(self):
        raw = (
            "15 Up to ₹50 lakhs | Starts at 9.99% The country's merchandise trade deficit "
            "sharply narrowed from $31.98 billion in July to $26.86 billion in August as "
            "gold imports nearly halved September 21, 2026 / 14:04 IST India's."
        )
        cleaned = clean_scraped_snippet(raw)
        self.assertNotIn("9.99%", cleaned)
        self.assertNotIn("14:04 IST", cleaned)
        self.assertNotIn("September 21, 2026", cleaned)
        self.assertIn("trade deficit", cleaned.lower())

    def test_detects_broken_fragment(self):
        frag = (
            "the domestic futures market during early trading hours on Tuesday, 29 September, "
            "as the deadlock between the US and Iran over the Strait of Hormuz continued to "
            "keep energy costs elevated and maintained pressure on the."
        )
        self.assertTrue(looks_like_raw_scrape(frag))

    def test_sanitize_drops_paste_bullets(self):
        bullet = (
            "3 Min Read Shares of Solar Industries India Ltd. fell about 12% on Tuesday, "
            "September 15, after the company's unit agreed to acquire Omnia Holdings."
        )
        self.assertEqual(sanitize_analyst_bullet(bullet), "")

    def test_analyst_line_paraphrases_solar_deal(self):
        art = {
            "title": "Solar Industries shares fall",
            "snippet": (
                "3 Min Read Shares of Solar Industries India Ltd. fell about 12% on Tuesday, "
                "September 15, after the company's unit agreed to acquire South Africa-based "
                "Omnia Holdings for ₹12,951 crore."
            ),
        }
        line = analyst_line_from_article(art)
        self.assertIn("Solar Industries", line)
        self.assertNotIn("September", line)
        self.assertNotIn("Min Read", line)


if __name__ == "__main__":
    unittest.main()
