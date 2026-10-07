import unittest

from news_rag.ask_plan import AskPlan, EntityMention, PlannedTool
from news_rag.plan_enrich import enrich_ask_plan


class TestPlanEnrich(unittest.TestCase):
    def test_gold_silver_splits_macro_news(self):
        q = (
            "I am seeing a sudden downfall in gold and silver in my portfolio lately, "
            "what could be the reason for it?"
        )
        plan = AskPlan(
            answer_parts="reasons for gold silver fall",
            tools=[PlannedTool(tool="metals_spot")],
        )
        out = enrich_ask_plan(q, plan)
        self.assertEqual([t.tool for t in out.tools], ["metals_spot"])

    def test_fund_overview_gets_news_tools(self):
        plan = AskPlan(
            answer_parts="HDFC Large Cap Fund overview",
            entities=[EntityMention(raw="HDFC Large Cap Fund", role="fund_scheme")],
            tools=[
                PlannedTool(tool="fund_nav", fund_entity_index=0),
                PlannedTool(tool="fund_top_stocks", fund_entity_index=0),
                PlannedTool(tool="fund_top_sectors", fund_entity_index=0),
            ],
        )
        out = enrich_ask_plan("tell me about hdfc large cap fund?", plan)
        self.assertEqual([t.tool for t in out.tools], ["fund_nav", "fund_top_stocks", "fund_top_sectors"])

    def test_pure_nav_skips_news_enrichment(self):
        plan = AskPlan(
            answer_parts="latest NAV",
            entities=[EntityMention(raw="HDFC Large Cap Fund", role="fund_scheme")],
            tools=[PlannedTool(tool="fund_nav", fund_entity_index=0)],
        )
        out = enrich_ask_plan("What is the NAV of HDFC Large Cap Fund?", plan)
        self.assertFalse(any(t.tool.endswith("_news") for t in out.tools))

    def test_gold_affecting_named_fund_cross_impact(self):
        plan = AskPlan(
            answer_parts="gold impact on PPFAS Flexi Cap",
            entities=[
                EntityMention(
                    raw="PPFAS Flexi Cap Fund",
                    role="fund_scheme",
                    cleaned_phrase="Parag Parikh Flexi Cap Fund",
                )
            ],
            tools=[PlannedTool(tool="fund_nav", fund_entity_index=0)],
        )
        q = "is the gold price movement affecting the ppfas flexi cap fund?"
        out = enrich_ask_plan(q, plan)
        self.assertEqual([t.tool for t in out.tools], ["fund_nav"])
        self.assertNotIn("cross_impact", out.raw_json or {})

    def test_fund_scheme_gets_nav_tool(self):
        plan = AskPlan(
            answer_parts="HDFC Defence Fund outlook",
            entities=[EntityMention(raw="HDFC Defence Fund", role="fund_scheme")],
            tools=[PlannedTool(tool="fund_top_stocks")],
        )
        out = enrich_ask_plan("How is HDFC Defence Fund doing?", plan)
        self.assertEqual([t.tool for t in out.tools], ["fund_top_stocks"])


if __name__ == "__main__":
    unittest.main()
