from __future__ import annotations

import unittest
from unittest.mock import patch

from news_rag.bullion_insights import (
    compose_macro_metals_insight,
    filter_bullion_articles,
    is_macro_bullion_tagged,
    score_bullion_article,
)
from news_rag.final_composer import aggregate_runs, compose_unified_answer
from news_rag.execution import SubQueryRun
from news_rag.query_plan import DataNeed, SubQuery


class TestBullionInsights(unittest.TestCase):
    def test_off_topic_scores_low(self):
        solar = {
            "title": "Solar Industries shares fall",
            "snippet": (
                "Shares of Solar Industries fell 12% after Omnia acquisition for ₹12,951 crore."
            ),
        }
        self.assertLess(score_bullion_article(solar), 2)

    def test_gold_import_scores_high(self):
        art = {
            "title": "Trade deficit narrows",
            "snippet": "Gold imports nearly halved as trade deficit narrowed in August.",
        }
        self.assertGreaterEqual(score_bullion_article(art), 2)

    def test_macro_tagged_news_used_in_compose(self):
        articles = [
            {
                "title": "Solar fall",
                "url": "https://example.com/solar",
                "snippet": "Solar Industries Omnia acquisition shares fell 12%.",
            },
            {
                "title": "Gold imports ease",
                "url": "https://example.com/gold",
                "entity_names": ["Macro - Gold"],
                "snippet": "Gold imports nearly halved; domestic bullion demand cooled after July inflows.",
            },
        ]
        metals = {
            "gold_7d_change_pct": -3.94,
            "silver_7d_change_pct": -6.46,
            "gold_24k_latest_10g": 98000,
            "gold_24k_30d_max_10g": 102000,
            "silver_latest_kg": 110000,
            "silver_30d_max_kg": 118000,
        }
        self.assertTrue(is_macro_bullion_tagged(articles[1]))
        bullets, _summary, sections = compose_macro_metals_insight(articles, metals, [])
        joined = " ".join(bullets).lower()
        self.assertNotIn("solar", joined)
        self.assertIn("gold import", joined)
        self.assertEqual(len(sections), 3)

    def test_macro_metals_unified_no_defence_noise(self):
        run = SubQueryRun(
            sub_query=SubQuery(
                id="Q1",
                text="gold silver",
                answer_style="news_brief",
                needs_reasoning=True,
                data_needs=[DataNeed(tool="metals_spot"), DataNeed(tool="news_search")],
            ),
        )
        run.tool_results = {
            "metals_spot": {
                "ok": True,
                "data": {
                    "gold_7d_change_pct": -3.94,
                    "silver_7d_change_pct": -6.46,
                    "gold_24k_latest_10g": 98000,
                    "gold_24k_30d_max_10g": 102000,
                    "silver_latest_kg": 110000,
                    "silver_30d_max_kg": 118000,
                },
            },
            "news_search": {
                "ok": True,
                "data": {
                    "articles": [
                        {
                            "title": "Solar",
                            "url": "https://example.com/1",
                            "snippet": "Solar Industries Omnia deal shares fell.",
                        },
                        {
                            "title": "Hormuz",
                            "url": "https://example.com/2",
                            "snippet": "Strait of Hormuz tension kept crude elevated.",
                        },
                        {
                            "title": "Gold imports",
                            "url": "https://example.com/3",
                            "snippet": "Gold imports fell sharply; silver weakened on MCX.",
                        },
                    ]
                },
            },
            "sector_funds": {"ok": True, "data": {"rankings": [{"fund_name": "Gold FoF", "sector_weight_pct": 20}]}},
        }
        agg = aggregate_runs(
            [run],
            "gold and silver downfall in my portfolio",
            plan_source="macro_metals",
        )
        with patch("news_rag.final_composer.llm_api_key_configured", return_value=False):
            composed = compose_unified_answer(
                "gold and silver downfall",
                agg,
                plan_source="macro_metals",
            )
        joined = composed.display.lower()
        self.assertNotIn("solar industries", joined)
        self.assertNotIn("hormuz", joined)


if __name__ == "__main__":
    unittest.main()
