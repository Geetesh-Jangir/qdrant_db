"""Tests for LLM-only ask engine."""

from __future__ import annotations

import json
import re
import unittest
from unittest.mock import MagicMock, patch

from news_rag.ask_plan import AskPlan, EntityMention, PlannedTool
from news_rag.fund_match import fold_fund_spelling
from news_rag.fund_search import get_fund_index, lookup_extracted_fund
from news_rag.name_resolution import resolve_plan_names
from news_rag.output_judge import JudgeResult
from news_rag.query_analyzer import plan_query


def _mock_llm_plan(payload: dict) -> MagicMock:
    return MagicMock(raw_text=json.dumps(payload))


def _defence_plan(**extra) -> AskPlan:
    return AskPlan(
        answer_parts=extra.get("answer_parts", "HDFC Defence performance"),
        entities=[
            EntityMention(
                raw="hdfc defence",
                role="fund_scheme",
                cleaned_phrase="HDFC Defence Fund",
            )
        ],
        tools=extra.get(
            "tools",
            [
                PlannedTool(tool="fund_nav", fund_entity_index=0),
                PlannedTool(tool="fund_top_stocks", fund_entity_index=0, top_n=5),
            ],
        ),
        declined_parts=extra.get("declined_parts", []),
        sentiment=extra.get("sentiment", "any"),
    )


class TestPlanner(unittest.TestCase):
    @patch("news_rag.query_analyzer.llm_api_key_configured", return_value=True)
    @patch("news_rag.query_analyzer.call_json_llm")
    def test_planner_parses_tools(self, mock_llm, _key):
        mock_llm.return_value = _mock_llm_plan(
            {
                "decline_entirely": False,
                "answer_parts": "NAV and sectors",
                "sentiment": "any",
                "entities": [
                    {
                        "raw": "HDFC Large Cap",
                        "role": "fund_scheme",
                        "cleaned_phrase": "HDFC Large Cap Fund",
                    }
                ],
                "tools": [
                    {"tool": "fund_nav", "fund_entity_index": 0},
                    {"tool": "fund_top_sectors", "fund_entity_index": 0, "top_n": 5},
                ],
            }
        )
        plan = plan_query("What is NAV and top 5 sectors of HDFC Large Cap?")
        tools = [t.tool for t in plan.tools]
        self.assertIn("fund_nav", tools)
        self.assertIn("fund_top_sectors", tools)

    @patch("news_rag.query_analyzer.llm_api_key_configured", return_value=True)
    @patch("news_rag.query_analyzer.call_json_llm")
    def test_mixed_question_keeps_answer_parts(self, mock_llm, _key):
        mock_llm.return_value = _mock_llm_plan(
            {
                "decline_entirely": False,
                "answer_parts": "HDFC Defence performance",
                "declined_parts": ["should I buy"],
                "sentiment": "any",
                "entities": [
                    {"raw": "hdfc defence", "role": "fund_scheme", "cleaned_phrase": "HDFC Defence Fund"}
                ],
                "tools": [{"tool": "fund_nav", "fund_entity_index": 0}],
            }
        )
        plan = plan_query("How is HDFC Defence doing, should I buy it?")
        self.assertFalse(plan.decline_entirely)
        self.assertIn("should I buy", plan.declined_parts[0])


class TestNameResolution(unittest.TestCase):
    def setUp(self):
        get_fund_index()

    def test_defense_spelling_fold(self):
        self.assertIn("defence", fold_fund_spelling("hdfc defense fund").lower())

    def test_resolve_defence_scheme(self):
        plan = _defence_plan()
        names = resolve_plan_names(plan)
        self.assertFalse(names.ambiguous)
        self.assertIsNotNone(names.primary_scheme)
        self.assertIn("Defence", names.schemes[0].canonical_name)

    def test_hdfc_large_cap_without_fund_word(self):
        detail, amb, _ = lookup_extracted_fund(name="HDFC Large Cap")
        self.assertFalse(amb)
        self.assertIsNotNone(detail)


class TestDigestInsightBullets(unittest.TestCase):
    def test_inject_digest_insights_appends_news(self):
        from news_rag.ask_composer import _inject_digest_insights
        from news_rag.news_digest import LayerDigest

        digests = [
            LayerDigest(
                layer="holding",
                focus="holding",
                summary="Bank earnings and RBI liquidity comments weighed on lenders this week.",
                items=[{"meaning": "Higher credit costs at private banks pressured sentiment."}],
            )
        ]
        bullets = ["NAV is ₹100."]
        out = _inject_digest_insights(bullets, digests)
        self.assertGreater(len(out), len(bullets))
        joined = " ".join(out).lower()
        self.assertNotIn("news insight", joined)
        self.assertNotRegex(out[-1], r"^(sector|holding|macro)\s*[:\-]", re.I)
        self.assertIn("credit costs", joined)


def _agent_run(plan: AskPlan, *, errors: list | None = None):
    from news_rag.ask_agent import AgentRun
    from news_rag.ask_execution import ExecutionBundle, PipelineError
    from news_rag.name_resolution import ResolvedNames

    bundle = ExecutionBundle(names=ResolvedNames())
    for message in errors or []:
        bundle.pipeline_errors.append(PipelineError(stage="tool", tool="macro_news", message=message))
    return AgentRun(
        plan=plan,
        bundle=bundle,
        research={
            "question_reading": {"intent": plan.answer_parts},
            "entities": [],
            "relationships_to_check": [],
            "information_gaps": [],
            "tools": [{"tool": t.tool, "purpose": t.purpose, "depends_on": t.depends_on} for t in plan.tools],
            "rounds": 1,
        },
    )


class TestAskEngineIntegration(unittest.TestCase):
    @patch("news_rag.ask_engine.judge_answer")
    @patch("news_rag.ask_engine.compose_final_answer")
    @patch("news_rag.ask_engine.run_research_agent")
    def test_engine_returns_score_without_hiding_answer(self, mock_agent, mock_compose, mock_judge):
        from news_rag.ask_composer import ComposedAnswer
        from news_rag.ask_engine import run_ask_engine

        mock_agent.return_value = _agent_run(_defence_plan())
        mock_compose.return_value = ComposedAnswer(
            headline="**HDFC Defence** performance context",
            narrative="NAV and returns over the last month.",
            summary="HDFC Defence NAV context",
            display="HDFC Defence NAV context",
            bullets=["1 month return noted"],
            highlight_terms=["HDFC Defence"],
            format_chosen="mixed",
            gaps=["No fresh holdings news."],
        )
        mock_judge.return_value = JudgeResult(
            passed=False,
            scores={"answers_query": 0.4, "grounded": 0.9, "no_advice": 1.0},
            attempt=1,
            raw={},
        )
        out = run_ask_engine("how is hdfc defence fund working?")
        self.assertIn("HDFC Defence", out.get("insight") or "")
        self.assertIn("NAV and returns", out.get("insight_narrative") or "")
        self.assertIsNotNone(out.get("output_score"))
        self.assertIn("question_reading", out.get("research") or {})
        self.assertEqual((out.get("answer_trace") or {}).get("format_chosen"), "mixed")
        self.assertNotEqual(out.get("insight"), "We do not have information related to this query in our data.")

    @patch("news_rag.ask_engine.judge_answer")
    @patch("news_rag.ask_engine.compose_final_answer")
    @patch("news_rag.ask_engine.run_research_agent")
    def test_tool_failure_surfaces_pipeline_errors(self, mock_agent, mock_compose, mock_judge):
        from news_rag.ask_composer import ComposedAnswer
        from news_rag.ask_engine import run_ask_engine

        mock_agent.return_value = _agent_run(
            AskPlan(
                answer_parts="macro",
                tools=[PlannedTool(tool="macro_news", semantic_query="crude oil India")],
            ),
            errors=["qdrant down"],
        )

        def _compose(*_a, **_k):
            return ComposedAnswer(summary="partial", display="partial")

        mock_compose.side_effect = _compose
        mock_judge.return_value = JudgeResult(passed=True, scores={"grounded": 0.9}, attempt=1, raw={})
        out = run_ask_engine("crude oil impact on sectors")
        errs = out.get("pipeline_errors") or []
        self.assertTrue(any("qdrant" in (e.get("message") or "").lower() for e in errs))
        self.assertIn("research", out)
        self.assertIn("answer_trace", out)

    @patch("news_rag.ask_engine.judge_answer")
    @patch("news_rag.ask_engine.compose_final_answer")
    @patch("news_rag.ask_engine.run_research_agent")
    def test_unusable_judge_scores_do_not_retry_agent(self, mock_agent, mock_compose, mock_judge):
        from news_rag.ask_composer import ComposedAnswer
        from news_rag.ask_engine import run_ask_engine

        mock_agent.return_value = _agent_run(_defence_plan())
        mock_compose.return_value = ComposedAnswer(
            headline="HDFC Defence",
            display="HDFC Defence NAV context",
            summary="HDFC Defence NAV context",
        )
        mock_judge.return_value = JudgeResult(
            passed=False,
            scores={"answers_query": 0.0, "grounded": 0.0, "on_topic": 0.0},
            attempt=1,
            raw={},
            usable=False,
        )
        out = run_ask_engine("how is hdfc defence fund working?")
        self.assertEqual(mock_agent.call_count, 1)
        self.assertIn("HDFC Defence", out.get("insight") or "")


if __name__ == "__main__":
    unittest.main()
