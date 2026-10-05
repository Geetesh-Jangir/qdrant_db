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
        macro = [t for t in out.tools if t.tool == "macro_news"]
        focuses = {t.search_focus for t in macro}
        self.assertIn("gold", focuses)
        self.assertIn("silver", focuses)
        self.assertTrue(any(t.tool == "sector_funds" for t in out.tools))

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
        news = {t.tool for t in out.tools} & {"holdings_news", "sector_news", "macro_news"}
        self.assertEqual(news, {"holdings_news", "sector_news", "macro_news"})

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
        self.assertIn("cross_impact", out.raw_json)
        self.assertIn("gold", out.raw_json["cross_impact"]["drivers"])
        self.assertTrue(any(t.tool == "metals_spot" for t in out.tools))
        gold_macro = [
            t for t in out.tools if t.tool == "macro_news" and t.search_focus == "gold"
        ]
        self.assertTrue(gold_macro)
        self.assertFalse(any(t.tool == "sector_funds" for t in out.tools))

    def test_fund_scheme_gets_nav_tool(self):
        plan = AskPlan(
            answer_parts="HDFC Defence Fund outlook",
            entities=[EntityMention(raw="HDFC Defence Fund", role="fund_scheme")],
            tools=[PlannedTool(tool="fund_top_stocks")],
        )
        out = enrich_ask_plan("How is HDFC Defence Fund doing?", plan)
        nav_tools = [t for t in out.tools if t.tool == "fund_nav"]
        self.assertEqual(len(nav_tools), 1)
        self.assertEqual(nav_tools[0].fund_entity_index, 0)


if __name__ == "__main__":
    unittest.main()
