from __future__ import annotations

import unittest
from unittest.mock import patch

from news_rag.ask_composer import ComposedAnswer
from news_rag.ask_plan import AskPlan, EntityMention, PlannedTool
from news_rag.fund_search import is_macro_metals_question, resolve_fund_from_question
from news_rag.macro_plans import try_macro_metals_plan, try_preset_plan
from news_rag.output_judge import JudgeResult


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


def _plan_for_question(question: str) -> AskPlan:
    lower = question.lower()
    if "gold" in lower or "silver" in lower:
        return AskPlan(
            answer_parts="gold silver move",
            tools=[PlannedTool(tool="metals_spot"), PlannedTool(tool="macro_news", semantic_query="gold silver India")],
        )
    if "barrell" in lower or "crude" in lower or "energy" in lower:
        return AskPlan(
            answer_parts="crude sectors",
            sentiment="any",
            tools=[
                PlannedTool(tool="sector_news", semantic_query="crude oil India sectors energy"),
                PlannedTool(tool="macro_news", semantic_query="crude oil India"),
            ],
            affected_funds="after_news",
        )
    if "defence" in lower or "defense" in lower:
        return AskPlan(
            answer_parts="HDFC Defence insights",
            entities=[
                EntityMention("HDFC Defence", "fund_scheme", "HDFC Defence Fund"),
            ],
            tools=[
                PlannedTool(tool="fund_nav", fund_entity_index=0),
                PlannedTool(tool="holdings_news", fund_entity_index=0, semantic_query="defence sector India"),
            ],
        )
    if "hot in the market" in lower or "market doing" in lower:
        return AskPlan(
            answer_parts="market pulse",
            tools=[PlannedTool(tool="macro_news", semantic_query="India equity market themes")],
        )
    return AskPlan(
        answer_parts="sector tape",
        tools=[PlannedTool(tool="sector_news", semantic_query="India sectors performance last month")],
    )


class TestFiveHarnessQueries(unittest.TestCase):
    def test_preset_helpers_still_exist(self):
        self.assertEqual(try_preset_plan(QUERIES["metals"]).source, "macro_metals")
        self.assertEqual(try_preset_plan(QUERIES["crude"]).source, "preset_crude_energy")

    def test_no_scheme_ambiguity_on_macro(self):
        for key in ("metals", "crude", "pulse", "sectors"):
            detail, amb, _ = resolve_fund_from_question(QUERIES[key])
            self.assertIsNone(detail, key)
            self.assertFalse(amb, key)

    def test_is_macro_metals(self):
        self.assertTrue(is_macro_metals_question(QUERIES["metals"]))
        self.assertIsNotNone(try_macro_metals_plan(QUERIES["metals"]))

    @patch("news_rag.ask_engine.judge_answer")
    @patch("news_rag.ask_engine.compose_final_answer")
    @patch("news_rag.ask_engine.run_research_agent")
    @patch("news_rag.tools.run_metals_spot")
    def test_ask_engine_not_clarification(self, mock_metals, mock_agent, mock_compose, mock_judge):
        from news_rag.ask_agent import AgentRun
        from news_rag.ask_execution import ExecutionBundle
        from news_rag.name_resolution import ResolvedNames

        mock_metals.return_value = {"ok": True, "data": {"gold_7d_change_pct": -2.0}, "error": "", "elapsed_ms": 1}
        mock_agent.side_effect = lambda q, **_: AgentRun(
            plan=_plan_for_question(q),
            bundle=ExecutionBundle(names=ResolvedNames()),
            research={"rounds": 1},
        )
        mock_compose.return_value = ComposedAnswer(
            headline="**Gold** and **silver** moves",
            narrative="Market context summary",
            summary="ok",
            display="Market context summary",
        )
        mock_judge.return_value = JudgeResult(passed=True, scores={"answers_query": 0.9}, attempt=1, raw={})
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

    @patch("news_rag.ask_engine.judge_answer")
    @patch("news_rag.ask_engine.compose_final_answer")
    @patch("news_rag.ask_engine.run_research_agent")
    def test_defence_insights_unified(self, mock_agent, mock_compose, mock_judge):
        from news_rag.ask_agent import AgentRun
        from news_rag.ask_execution import ExecutionBundle
        from news_rag.name_resolution import ResolvedNames

        mock_agent.side_effect = lambda q, **_: AgentRun(
            plan=_plan_for_question(q),
            bundle=ExecutionBundle(names=ResolvedNames()),
            research={"rounds": 1},
        )
        mock_compose.return_value = ComposedAnswer(
            headline="HDFC Defence NAV and news",
            narrative="Fund context from data.",
            summary="HDFC Defence NAV and news",
            display="HDFC Defence NAV and news",
        )
        mock_judge.return_value = JudgeResult(passed=True, scores={}, attempt=1, raw={})
        from news_rag.ask_engine import run_ask_engine

        out = run_ask_engine(QUERIES["defence"])
        self.assertNotEqual(out.get("outcome"), "clarification")
        insight = (out.get("insight") or "").lower()
        self.assertTrue("hdfc" in insight or "defence" in insight or "nav" in insight)


if __name__ == "__main__":
    unittest.main()
