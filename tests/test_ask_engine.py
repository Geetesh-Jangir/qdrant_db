"""Tests for production ask engine (guardrails, decomposition, minimal tools)."""

from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from news_rag.guardrails import ADVICE_DISCLAIMER, check_guardrails
from news_rag.plan_normalize import normalize_query_plan
from news_rag.query_analyzer import decompose_query, reconcile_plan_with_catalog
from news_rag.query_plan import QueryPlan
from news_rag.fund_search import get_fund_index, lookup_extracted_fund


def _mock_llm_plan(payload: dict) -> MagicMock:
    return MagicMock(raw_text=json.dumps(payload))


class TestGuardrails(unittest.TestCase):
    def test_refuse_buy_advice(self):
        r = check_guardrails("Should I buy HDFC Top 100 Fund now?")
        self.assertEqual(r.outcome, "refuse_advice")
        self.assertIn("investment advice", ADVICE_DISCLAIMER)

    def test_allow_historical_crude(self):
        r = check_guardrails("How did crude oil prices fluctuate after the US Iran tensions?")
        self.assertEqual(r.outcome, "pass")


class TestDecomposition(unittest.TestCase):
    def setUp(self):
        get_fund_index()

    @patch("news_rag.query_analyzer.llm_api_key_configured", return_value=True)
    @patch("news_rag.query_analyzer.call_json_llm")
    def test_llm_multi_nav_and_sectors(self, mock_llm, _key):
        mock_llm.return_value = _mock_llm_plan(
            {
                "sub_queries": [
                    {
                        "id": "Q1",
                        "text": "NAV",
                        "answer_style": "one_metric",
                        "needs_reasoning": False,
                        "data_needs": [
                            {"tool": "fund_nav", "fund_raw": "HDFC Large Cap Fund", "scope": "latest_only"}
                        ],
                    },
                    {
                        "id": "Q2",
                        "text": "top 5 sectors",
                        "answer_style": "short_table",
                        "needs_reasoning": False,
                        "data_needs": [
                            {"tool": "fund_sectors", "fund_ref": "Q1", "scope": "top_n", "top_n": 5}
                        ],
                    },
                ]
            }
        )
        plan = decompose_query("What is the NAV of HDFC Large Cap Fund and what are its top 5 sectors?")
        self.assertTrue(plan.source.startswith("llm"))
        self.assertEqual(len(plan.sub_queries), 2)
        tools = [n.tool for sq in plan.sub_queries for n in sq.data_needs]
        self.assertIn("fund_nav", tools)
        self.assertIn("fund_sectors", tools)
        self.assertNotIn("news_search", tools)

    @patch("news_rag.query_analyzer.llm_api_key_configured", return_value=True)
    @patch("news_rag.query_analyzer.call_json_llm")
    def test_llm_performance_defence_reconciled(self, mock_llm, _key):
        mock_llm.return_value = _mock_llm_plan(
            {
                "sub_queries": [
                    {
                        "id": "Q1",
                        "text": "performance",
                        "answer_style": "performance_summary",
                        "needs_reasoning": False,
                        "data_needs": [
                            {"tool": "fund_nav", "fund_raw": "hdfc defence", "scope": "with_returns"},
                            {
                                "tool": "news_search",
                                "depends_on_portfolio": True,
                                "window_days": 30,
                                "semantic_query": "defence fund",
                            },
                        ],
                    }
                ]
            }
        )
        plan = decompose_query("tell me how hdfc defence fund is working in last one month?")
        nav_need = plan.sub_queries[0].data_needs[0]
        self.assertIn("Defence", nav_need.fund_raw)

    @patch("news_rag.query_analyzer.llm_api_key_configured", return_value=False)
    def test_no_llm_fallback(self, _mock):
        plan = decompose_query("What is the NAV of HDFC Top 100 Fund?")
        self.assertTrue(plan.source.startswith("no_llm_fallback"))


class TestDefenceFundExtraction(unittest.TestCase):
    def setUp(self):
        get_fund_index()

    def test_extract_hdfc_defence_working(self):
        from news_rag.fund_search import extract_fund_phrase_from_question, resolve_fund_from_question

        q = "tell me how hdfc defence fund is working in last one month?"
        _isin, name = extract_fund_phrase_from_question(q)
        self.assertIn("defence", (name or "").lower())
        detail, amb, _ = resolve_fund_from_question(q)
        self.assertFalse(amb)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["isin"], "INF179KC1GL9")

    def test_shorthand_without_fund_word(self):
        from news_rag.fund_search import resolve_fund_from_question

        detail, amb, _ = resolve_fund_from_question("how is hdfc defence working in the last month")
        self.assertFalse(amb)
        self.assertEqual(detail["isin"], "INF179KC1GL9")

    def test_reconcile_fills_shorthand(self):
        plan = QueryPlan.from_dict(
            {
                "sub_queries": [
                    {
                        "id": "Q1",
                        "text": "nav",
                        "answer_style": "one_metric",
                        "needs_reasoning": False,
                        "data_needs": [{"tool": "fund_nav", "fund_raw": "hdfc defence", "scope": "latest_only"}],
                    }
                ]
            }
        )
        plan = reconcile_plan_with_catalog(plan, "how is hdfc defence doing?")
        self.assertIn("HDFC Defence", plan.sub_queries[0].data_needs[0].fund_raw)


class TestFundFuzzy(unittest.TestCase):
    def setUp(self):
        get_fund_index()

    def test_hdfc_large_cap_name(self):
        detail, amb, _ = lookup_extracted_fund(name="HDFC Large Cap")
        self.assertFalse(amb)
        if detail:
            self.assertIn("HDFC", str(detail.get("fund_short_name") or ""))


class TestPlanNormalize(unittest.TestCase):
    def test_split_multi_block_compound(self):
        from news_rag.plan_normalize import normalize_query_plan
        from news_rag.query_plan import QueryPlan

        plan = QueryPlan.from_dict(
            {
                "sub_queries": [
                    {
                        "id": "Q1",
                        "text": "performance and holdings",
                        "answer_style": "multi_block",
                        "needs_reasoning": False,
                        "data_needs": [
                            {"tool": "fund_nav", "fund_raw": "HDFC Defence Fund", "scope": "with_returns"},
                            {"tool": "fund_holdings", "fund_ref": "Q1", "scope": "top_n", "top_n": 5},
                        ],
                    }
                ]
            }
        )
        q = "how is hdfc defence working last month also top 5 holdings"
        norm = normalize_query_plan(plan, q)
        self.assertGreaterEqual(len(norm.sub_queries), 2)
        tools = [n.tool for sq in norm.sub_queries for n in sq.data_needs]
        self.assertIn("fund_nav", tools)
        self.assertIn("fund_holdings", tools)

    def test_normalize_performance_and_crude_not_holdings_list(self):
        q = (
            "tell me how hdfc defence fund is working in last one month and "
            "how is crude related news affecting this fund"
        )
        plan = QueryPlan.from_dict(
            {
                "sub_queries": [
                    {
                        "id": "Q1",
                        "text": "performance",
                        "answer_style": "performance_summary",
                        "needs_reasoning": False,
                        "data_needs": [
                            {"tool": "fund_nav", "fund_raw": "HDFC Defence Fund", "scope": "with_returns"},
                            {
                                "tool": "news_search",
                                "semantic_query": "crude oil impact defence sector",
                                "depends_on_portfolio": True,
                                "window_days": 30,
                            },
                        ],
                    },
                    {
                        "id": "Q2",
                        "text": "holdings",
                        "answer_style": "short_list",
                        "needs_reasoning": False,
                        "data_needs": [
                            {"tool": "fund_holdings", "fund_ref": "Q1", "scope": "top_n", "top_n": 10},
                        ],
                    },
                ]
            }
        )
        norm = normalize_query_plan(plan, q)
        self.assertEqual(len(norm.sub_queries), 2)
        self.assertEqual(norm.sub_queries[0].answer_style, "performance_summary")
        self.assertEqual([n.tool for n in norm.sub_queries[0].data_needs], ["fund_nav"])
        self.assertEqual(norm.sub_queries[1].answer_style, "exposure_note")
        tools2 = [n.tool for n in norm.sub_queries[1].data_needs]
        self.assertIn("news_search", tools2)
        self.assertIn("fund_holdings", tools2)
        self.assertNotIn("short_list", [s.answer_style for s in norm.sub_queries])

    def test_collapse_duplicate_exposure_subqueries(self):
        q = (
            "How has HDFC Defence Fund done over the last one month, and how might "
            "crude-oil related news be affecting it given its holdings?"
        )
        plan = QueryPlan.from_dict(
            {
                "sub_queries": [
                    {
                        "id": "Q1",
                        "text": "performance",
                        "answer_style": "performance_summary",
                        "needs_reasoning": False,
                        "data_needs": [
                            {"tool": "fund_nav", "fund_raw": "HDFC Defence Fund", "scope": "with_returns"},
                        ],
                    },
                    {
                        "id": "Q2",
                        "text": "holdings news",
                        "answer_style": "exposure_note",
                        "needs_reasoning": True,
                        "data_needs": [
                            {"tool": "fund_holdings", "fund_ref": "Q1", "scope": "top_n", "top_n": 8},
                            {
                                "tool": "news_search",
                                "semantic_query": "HDFC Defence Fund holdings news",
                                "depends_on_portfolio": True,
                                "window_days": 30,
                            },
                        ],
                    },
                    {
                        "id": "Q3",
                        "text": "crude impact",
                        "answer_style": "exposure_note",
                        "needs_reasoning": True,
                        "data_needs": [
                            {"tool": "fund_holdings", "fund_ref": "Q1", "scope": "top_n", "top_n": 8},
                            {
                                "tool": "news_search",
                                "semantic_query": "crude oil India",
                                "depends_on_portfolio": True,
                                "window_days": 30,
                            },
                        ],
                    },
                ]
            }
        )
        norm = normalize_query_plan(plan, q)
        self.assertEqual(len(norm.sub_queries), 2)
        exposure = [s for s in norm.sub_queries if s.answer_style == "exposure_note"]
        self.assertEqual(len(exposure), 1)
        self.assertIn("crude", exposure[0].text.lower())


class TestAskEngineIntegration(unittest.TestCase):
    @patch("news_rag.query_analyzer.llm_api_key_configured", return_value=True)
    @patch("news_rag.query_analyzer.call_json_llm")
    @patch("news_rag.tools.retrieve_scoped_news", return_value=[])
    def test_hdfc_defence_performance_and_holdings(self, _news, mock_llm, _key):
        from news_rag.ask_engine import run_ask_engine

        mock_llm.return_value = _mock_llm_plan(
            {
                "sub_queries": [
                    {
                        "id": "Q1",
                        "text": "performance and holdings",
                        "answer_style": "multi_block",
                        "needs_reasoning": False,
                        "data_needs": [
                            {"tool": "fund_nav", "fund_raw": "HDFC Defence Fund", "scope": "with_returns"},
                            {"tool": "fund_holdings", "fund_ref": "Q1", "scope": "top_n", "top_n": 5},
                        ],
                    }
                ]
            }
        )
        out = run_ask_engine(
            "tell me how hdfc defence fund is working in last one month? "
            "also list me out its top 5 holdings"
        )
        insight = out.get("insight") or ""
        self.assertIn("HDFC Defence", insight)
        self.assertIn("1 month", insight.lower())
        self.assertIn("Bharat Electronics", insight)
        self.assertEqual(len(out.get("sections") or []), 2)

    @patch("news_rag.query_analyzer.llm_api_key_configured", return_value=True)
    @patch("news_rag.query_analyzer.call_json_llm")
    @patch("news_rag.tools.retrieve_scoped_news", return_value=[])
    def test_hdfc_defence_performance(self, _news, mock_llm, _key):
        from news_rag.ask_engine import run_ask_engine

        mock_llm.return_value = _mock_llm_plan(
            {
                "sub_queries": [
                    {
                        "id": "Q1",
                        "text": "HDFC Defence last month",
                        "answer_style": "performance_summary",
                        "needs_reasoning": False,
                        "data_needs": [
                            {"tool": "fund_nav", "fund_raw": "HDFC Defence Fund", "scope": "with_returns"},
                            {
                                "tool": "news_search",
                                "depends_on_portfolio": True,
                                "window_days": 30,
                                "semantic_query": "HDFC Defence",
                            },
                        ],
                    }
                ]
            }
        )
        out = run_ask_engine("tell me how hdfc defence fund is working in last one month?")
        self.assertIn("HDFC Defence", out.get("insight") or "")
        self.assertIn("1 month", (out.get("insight") or "").lower())
        self.assertEqual(len(out.get("sections") or []), 1)

    @patch("news_rag.query_analyzer.llm_api_key_configured", return_value=True)
    @patch("news_rag.query_analyzer.call_json_llm")
    @patch("news_rag.tools.retrieve_scoped_news", return_value=[])
    def test_hdfc_defence_performance_and_crude(self, _news, mock_llm, _key):
        from news_rag.ask_engine import run_ask_engine

        mock_llm.return_value = _mock_llm_plan(
            {
                "sub_queries": [
                    {
                        "id": "Q1",
                        "text": "HDFC Defence last month",
                        "answer_style": "performance_summary",
                        "needs_reasoning": False,
                        "data_needs": [
                            {"tool": "fund_nav", "fund_raw": "HDFC Defence Fund", "scope": "with_returns"},
                            {
                                "tool": "news_search",
                                "depends_on_portfolio": True,
                                "window_days": 30,
                                "semantic_query": "crude oil news India",
                            },
                        ],
                    },
                    {
                        "id": "Q2",
                        "text": "holdings",
                        "answer_style": "short_list",
                        "needs_reasoning": False,
                        "data_needs": [
                            {"tool": "fund_holdings", "fund_ref": "Q1", "scope": "top_n", "top_n": 10},
                        ],
                    },
                ]
            }
        )
        q = (
            "tell me how hdfc defence fund is working in last one month and "
            "how is crude related news affecting this fund"
        )
        out = run_ask_engine(q)
        sections = out.get("sections") or []
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].get("style"), "unified_answer")
        bullets = out.get("insight_bullets") or []
        insight = out.get("insight") or ""
        self.assertTrue(bullets or insight)
        lower = insight.lower()
        self.assertTrue("1 month" in lower or "1m" in lower or "last month" in lower)
        self.assertNotIn("Recent news on top holdings", insight)
        self.assertNotIn("Stock Picks Today", insight)
        self.assertNotIn("business-standard.com", insight.lower())

    @patch("news_rag.query_analyzer.llm_api_key_configured", return_value=True)
    @patch("news_rag.query_analyzer.call_json_llm")
    @patch("news_rag.tools.retrieve_scoped_news", return_value=[])
    def test_nav_only_no_news(self, _news, mock_llm, _key):
        from news_rag.ask_engine import run_ask_engine

        mock_llm.return_value = _mock_llm_plan(
            {
                "sub_queries": [
                    {
                        "id": "Q1",
                        "text": "NAV",
                        "answer_style": "one_metric",
                        "needs_reasoning": False,
                        "data_needs": [
                            {"tool": "fund_nav", "fund_raw": "HDFC Top 100 Fund", "scope": "latest_only"}
                        ],
                    }
                ]
            }
        )
        out = run_ask_engine("What is the NAV of HDFC Top 100 Fund?")
        self.assertIn("NAV", out.get("insight") or "")
        self.assertEqual(out.get("intent"), "fund_nav")
        _news.assert_not_called()


if __name__ == "__main__":
    unittest.main()
