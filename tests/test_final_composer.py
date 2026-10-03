from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from news_rag.execution import SubQueryRun
from news_rag.final_composer import aggregate_runs, compose_unified_answer, should_unify_compose
from news_rag.query_plan import DataNeed, QueryPlan, SubQuery


class TestFinalComposer(unittest.TestCase):
    def test_should_unify_performance_and_exposure(self):
        plan = QueryPlan(
            sub_queries=[
                SubQuery(
                    id="Q1",
                    text="perf",
                    answer_style="performance_summary",
                    needs_reasoning=False,
                    data_needs=[],
                ),
                SubQuery(
                    id="Q2",
                    text="crude",
                    answer_style="exposure_note",
                    needs_reasoning=True,
                    data_needs=[],
                ),
            ]
        )
        self.assertTrue(should_unify_compose(plan))

    def test_deterministic_unified_no_publisher(self):
        run = SubQueryRun(
            sub_query=SubQuery(
                id="Q1",
                text="",
                answer_style="performance_summary",
                needs_reasoning=False,
                data_needs=[],
            ),
        )
        run.tool_results = {
            "fund_nav": {
                "ok": True,
                "data": {
                    "fund_name": "HDFC Defence Fund",
                    "nav": 29.136,
                    "nav_date": "2026-10-01",
                    "returns": {"1m": -3.88},
                },
            },
            "fund_holdings": {
                "ok": True,
                "data": {"rows": [{"name": "Bharat Electronics Ltd.", "percentage": 15.2}]},
            },
            "news_search": {
                "ok": True,
                "data": {
                    "articles": [
                        {
                            "title": "Crude surges",
                            "url": "https://example.com/1",
                            "source": "business-standard.com",
                            "snippet": "Brent crude moved toward $99 per barrel on supply fears.",
                        }
                    ]
                },
            },
        }
        agg = aggregate_runs([run], "crude impact on HDFC Defence Fund")
        composed = compose_unified_answer("How is HDFC Defence doing and crude news?", agg)
        self.assertIn("Bharat Electronics", composed.display)
        self.assertNotIn("business-standard", composed.display.lower())
        self.assertNotIn("Livemint", composed.display)
        self.assertNotIn("PTI repo", composed.display)
        self.assertTrue(composed.bullets)
        self.assertTrue(
            any("Fuel-marketing" in b or "Crude near" in b or "Performance" in b for b in composed.bullets)
        )


if __name__ == "__main__":
    unittest.main()
