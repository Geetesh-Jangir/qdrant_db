from __future__ import annotations

import unittest
from unittest.mock import patch

from news_rag.fund_search import is_macro_metals_question, resolve_fund_from_question
from news_rag.guardrails import check_guardrails
from news_rag.macro_plans import (
    try_preset_plan,
    try_macro_metals_plan,
)
from news_rag.query_analyzer import decompose_query


QUERIES = {
    "metals": (
        "I am seeing a sudden downfall in gold and silver in my portfolio lately, "
        "what could be the reason for it? and does it affect any mutual funds as well?"
    ),
    "crude": (
        "Lately the news about barrell prices is all over, which sectors are it affecting "
        "including the energy and what it means for the funds which are highly invested in the sector?"
    ),
    "defence": "I have invested in the HDFC Defence fund, what insights do you have for me for this fund?",
    "pulse": "Tell me what is hot in the market right now? what to focus on? how's the market doing currently",
    "sectors": "What are sectors from last month that are doing postive and which are ones negative, and why?",
}


class TestFiveHarnessQueries(unittest.TestCase):
    def test_guardrails_pass_all(self):
        for q in QUERIES.values():
            self.assertEqual(check_guardrails(q).outcome, "pass", q)

    def test_preset_sources(self):
        self.assertEqual(try_preset_plan(QUERIES["metals"]).source, "macro_metals")
        self.assertEqual(try_preset_plan(QUERIES["crude"]).source, "preset_crude_energy")
        self.assertEqual(try_preset_plan(QUERIES["defence"]).source, "preset_fund_insights")
        self.assertEqual(try_preset_plan(QUERIES["pulse"]).source, "preset_market_pulse")
        self.assertEqual(try_preset_plan(QUERIES["sectors"]).source, "preset_sector_tape")

    def test_no_scheme_ambiguity_on_macro(self):
        for key in ("metals", "crude", "pulse", "sectors"):
            detail, amb, _ = resolve_fund_from_question(QUERIES[key])
            self.assertIsNone(detail, key)
            self.assertFalse(amb, key)

    def test_decompose_uses_presets(self):
        for key, source in (
            ("metals", "macro_metals"),
            ("crude", "preset_crude_energy"),
            ("defence", "preset_fund_insights"),
            ("pulse", "preset_market_pulse"),
            ("sectors", "preset_sector_tape"),
        ):
            plan = decompose_query(QUERIES[key])
            self.assertIn(source, plan.source, key)

    def test_is_macro_metals(self):
        self.assertTrue(is_macro_metals_question(QUERIES["metals"]))
        self.assertIsNotNone(try_macro_metals_plan(QUERIES["metals"]))

    @patch("news_rag.bullion_retrieve.retrieve_bullion_macro_news", return_value=[])
    @patch("news_rag.tools.retrieve_scoped_news", return_value=[])
    @patch("news_rag.tools.run_metals_spot")
    def test_ask_engine_not_clarification(self, mock_metals, _news, _bullion):
        mock_metals.return_value = {"ok": True, "data": {"gold_7d_change_pct": -2.0}, "error": "", "elapsed_ms": 1}
        from news_rag.ask_engine import run_ask_engine

        for key in ("metals", "crude", "pulse", "sectors"):
            out = run_ask_engine(QUERIES[key])
            self.assertNotEqual(out.get("outcome"), "clarification", key)
            self.assertFalse(
                str(out.get("insight") or "").startswith("Your query matched multiple funds"),
                key,
            )
            sections = out.get("sections") or []
            self.assertEqual(len(sections), 1, key)
            self.assertEqual(sections[0].get("style"), "unified_answer", key)

    @patch("news_rag.tools.retrieve_scoped_news", return_value=[])
    def test_defence_insights_unified(self, _news):
        from news_rag.ask_engine import run_ask_engine

        out = run_ask_engine(QUERIES["defence"])
        self.assertNotEqual(out.get("outcome"), "clarification")
        insight = (out.get("insight") or "").lower()
        self.assertTrue("hdfc" in insight or "defence" in insight or "nav" in insight)


if __name__ == "__main__":
    unittest.main()
