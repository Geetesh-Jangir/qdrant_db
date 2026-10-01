"""Deterministic unit tests for Smart Ask components (no external network/API required)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from news_rag.answer_contract import AlignmentResult, AnswerContract
from news_rag.fund_search import get_fund_index, lookup_extracted_fund
from news_rag.llm_text import parse_json_from_text
from news_rag.parse import ParsedQuery
from news_rag.query_router import RouterFund, RouterResult
from news_rag.retrieve import retrieve_for_question


class TestSmartAskUnit(unittest.TestCase):
    def setUp(self):
        # Ensure fund index is loaded
        get_fund_index()

    def test_lookup_extracted_fund_isin(self):
        detail, is_ambiguous, close = lookup_extracted_fund(isin="INF879O01027")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["isin"], "INF879O01027")
        self.assertFalse(is_ambiguous)

    def test_lookup_extracted_fund_name(self):
        detail, is_ambiguous, close = lookup_extracted_fund(name="Parag Parikh Flexi Cap")
        self.assertIsNotNone(detail)
        self.assertIn(detail["isin"], ("INF879O01019", "INF879O01027"))
        self.assertFalse(is_ambiguous)

    def test_lookup_extracted_fund_non_fund(self):
        detail, is_ambiguous, close = lookup_extracted_fund(name="Gold Bullion MCX")
        self.assertIsNone(detail)
        self.assertFalse(is_ambiguous)

    def test_parse_json_from_text(self):
        raw_clean = '{"intent": "concept", "fund": {"name": "", "isin": ""}}'
        data = parse_json_from_text(raw_clean)
        self.assertEqual(data["intent"], "concept")

        raw_markdown = 'Here is the parsed query:\n```json\n{"intent": "single_stock", "companies": ["TCS"]}\n```'
        data = parse_json_from_text(raw_markdown)
        self.assertEqual(data["intent"], "single_stock")
        self.assertEqual(data["companies"], ["TCS"])

    def test_router_result_from_dict(self):
        payload = {
            "intent": "fund_nav",
            "fund": {"name": "HDFC Top 100", "isin": "INF179K01BE2"},
            "companies": ["HDFC Bank"],
            "event_focus": "",
            "window_days": 7,
            "asked": ["NAV of HDFC Top 100"],
        }
        res = RouterResult.from_dict(payload)
        self.assertEqual(res.intent, "fund_nav")
        self.assertEqual(res.fund.isin, "INF179K01BE2")
        self.assertEqual(res.fund.name, "HDFC Top 100")
        self.assertEqual(res.window_days, 7)

    def test_answer_contract_defaults(self):
        contract_data = {
            "must_answer": ["Point 1"],
            "forbidden": ["Do not cite NAV"],
            "use_articles": [0, 2],
            "include_nav": False,
            "include_holdings": True,
        }
        contract = AnswerContract.from_dict(contract_data, total_articles=3)
        self.assertEqual(contract.must_answer, ["Point 1"])
        self.assertEqual(contract.forbidden, ["Do not cite NAV"])
        self.assertEqual(contract.use_articles, [0, 2])
        self.assertFalse(contract.include_nav)
        self.assertTrue(contract.include_holdings)

    def test_retrieve_branch_concept_skips_qdrant(self):
        mock_router = RouterResult(
            intent="concept",
            fund=RouterFund(),
            companies=[],
            event_focus="",
            window_days=None,
            asked=["What is NAV?"],
        )
        with patch("news_rag.retrieve.QdrantReader") as mock_reader:
            parsed, articles = retrieve_for_question(
                "What is NAV in mutual funds?",
                router_override=mock_router,
            )
            mock_reader.assert_not_called()
            self.assertEqual(parsed.intent, "concept")
            self.assertEqual(articles, [])

    def test_retrieve_branch_fund_nav_skips_qdrant(self):
        mock_router = RouterResult(
            intent="fund_nav",
            fund=RouterFund(isin="INF879O01027", name="Parag Parikh Flexi Cap"),
            companies=[],
            event_focus="",
            window_days=7,
            asked=["Latest NAV"],
        )
        with patch("news_rag.retrieve.QdrantReader") as mock_reader:
            parsed, articles = retrieve_for_question(
                "What is the latest NAV of Parag Parikh Flexi Cap?",
                router_override=mock_router,
            )
            mock_reader.assert_not_called()
            self.assertEqual(parsed.intent, "fund_nav")
            self.assertIsNotNone(parsed.fund_resolved)
            self.assertEqual(parsed.fund_resolved["isin"], "INF879O01027")
            self.assertEqual(articles, [])


if __name__ == "__main__":
    unittest.main()
