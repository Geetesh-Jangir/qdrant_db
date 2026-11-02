from news_rag.fund_rating_labels import label_tiers_from, label_tiers_up_to, normalize_rs_label
from news_rag.fund_rating_screen import (
    pick_alternate_funds_in_category,
    pick_better_rated_fund_in_category,
    pick_funds_by_label_cascade,
)


def test_label_tiers_from_recommended():
    assert label_tiers_from("Recommended") == [
        "Recommended",
        "Good Choice",
        "Average",
        "Underperformer",
    ]


def test_normalize_rs_label():
    assert normalize_rs_label("good choice") == "Good Choice"
    assert normalize_rs_label("Best in category") == "Best in category"


def test_label_tiers_up_to_good_choice():
    assert label_tiers_up_to("Good Choice") == [
        "Best in category",
        "Recommended",
        "Good Choice",
    ]


def test_pick_funds_by_label_cascade_fills_across_tiers():
    rows = [
        {"isin": "INFA", "fund_name": "A", "rs_label": "Best in category", "final_score": 90},
        {"isin": "INFB", "fund_name": "B", "rs_label": "Recommended", "final_score": 80},
        {"isin": "INFC", "fund_name": "C", "rs_label": "Good Choice", "final_score": 70},
        {"isin": "INFD", "fund_name": "D", "rs_label": "Average", "final_score": 50},
    ]
    picked, _ = pick_funds_by_label_cascade(rows, 3, max_tier="Good Choice")
    assert [r["isin"] for r in picked] == ["INFA", "INFB", "INFC"]


def test_pick_alternate_walks_label_tier():
    payload = {
        "data": {
            "ratings": [
                {"isin": "INFAAA", "fundName": "Fund A", "finalScore": 80, "label": "Recommended"},
                {"isin": "INFBBB", "fundName": "Fund B", "finalScore": 70, "label": "Good Choice"},
            ]
        }
    }

    def fake_fetch(_ft: str, _cat: str) -> dict:
        return payload

    out = pick_alternate_funds_in_category(
        fund_type="hybrid",
        category="aggressive hybrid",
        exclude_isins=["INFAAA"],
        rs_label="Recommended",
        top_n=1,
        fetch=fake_fetch,
    )
    assert out["success"] is True
    assert out["rankings"][0]["isin"] == "INFBBB"
    assert "Good Choice" in out["ranking_note"]


def test_pick_better_rated_prefers_upgrade():
    payload = {
        "data": {
            "ratings": [
                {"isin": "INFKOTAK", "fundName": "Kotak Contra", "finalScore": 75.1, "label": "Recommended"},
                {"isin": "INFBEST", "fundName": "Best Contra", "finalScore": 88.0, "label": "Best in category"},
                {"isin": "INFAVG", "fundName": "Quantum Value", "finalScore": 51.3, "label": "Average"},
            ]
        }
    }

    def fake_fetch(_ft: str, _cat: str) -> dict:
        return payload

    out = pick_better_rated_fund_in_category(
        fund_type="equity",
        category="contra",
        exclude_isins=["INFKOTAK"],
        exclude_names=["kotak contra"],
        anchor_rs_label="Recommended",
        anchor_rs_score=75.1,
        top_n=1,
        fetch=fake_fetch,
    )
    assert out["success"] is True
    assert out["rankings"][0]["isin"] == "INFBEST"
    assert out["rating_pick_mode"] == "upgrade"


def test_pick_better_rated_next_by_score_when_no_upgrade():
    payload = {
        "data": {
            "ratings": [
                {"isin": "INFKOTAK", "fundName": "Kotak Contra", "finalScore": 90.0, "label": "Best in category"},
                {"isin": "INFREC", "fundName": "Other Rec", "finalScore": 80.0, "label": "Recommended"},
                {"isin": "INFGC", "fundName": "Good One", "finalScore": 70.0, "label": "Good Choice"},
            ]
        }
    }

    def fake_fetch(_ft: str, _cat: str) -> dict:
        return payload

    out = pick_better_rated_fund_in_category(
        fund_type="equity",
        category="contra",
        exclude_isins=["INFKOTAK"],
        anchor_rs_label="Best in category",
        anchor_rs_score=90.0,
        top_n=1,
        fetch=fake_fetch,
    )
    assert out["success"] is True
    assert out["rankings"][0]["isin"] == "INFREC"
    assert out["rating_pick_mode"] == "next_by_score"
