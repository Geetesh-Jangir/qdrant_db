"""Exposure synthesis uses article snippets, not title-only lists."""

from __future__ import annotations

import unittest

from news_rag.synthesizer import _deterministic_exposure


class TestDeterministicExposure(unittest.TestCase):
    def test_uses_snippet_not_title_list(self):
        ctx = {
            "sub_query": "crude oil impact",
            "user_question": "How might crude-oil news affect HDFC Defence Fund?",
            "holdings": [
                {"name": "Bharat Electronics Ltd.", "percentage": 15.2},
                {"name": "Bharat Forge Ltd.", "percentage": 13.4},
            ],
            "sectors": None,
        }
        articles = [
            {
                "title": "OMCs face ₹530 crore daily fuel losses as crude prices surge: Icra",
                "source": "Business Standard",
                "snippet": (
                    "Indian oil marketing companies are estimated to lose about ₹530 crore per day "
                    "on retail fuel sales after Brent crude moved toward $100. Icra said margins "
                    "remain under pressure until pump prices are adjusted."
                ),
                "entity_names": ["Indian Oil Corporation"],
            }
        ]
        text = _deterministic_exposure(ctx, articles_full=articles)
        self.assertTrue("530 crore" in text or "Fuel-marketing" in text or "under-recover" in text.lower())
        self.assertNotIn("Holdings to weigh against those headlines", text)
        self.assertIn("Bharat Electronics", text)
        self.assertNotIn("; OMCs face", text)  # not a semicolon-separated title dump


if __name__ == "__main__":
    unittest.main()
