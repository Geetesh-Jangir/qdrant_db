import unittest

from news_rag.cross_impact import detect_macro_drivers, is_cross_impact_question


class TestCrossImpact(unittest.TestCase):
    def test_detect_gold_and_impact_wording(self):
        q = "is the gold price movement affecting the ppfas flexi cap fund?"
        self.assertTrue(is_cross_impact_question(q))
        self.assertIn("gold", detect_macro_drivers(q))

    def test_oil_driver(self):
        q = "will crude oil spike impact HDFC Banking Fund?"
        self.assertTrue(is_cross_impact_question(q))
        self.assertIn("oil", detect_macro_drivers(q))


if __name__ == "__main__":
    unittest.main()
