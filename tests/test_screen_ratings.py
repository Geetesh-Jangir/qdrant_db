"""Screened fund lists carry a RupeeStop rating even when the question did not ask for one."""

from news_rag.insight.contracts import ExecutionPlan


def test_screen_rows_get_ratings_by_default(monkeypatch):
    from news_rag.insight.evidence_pack import _attach_rs_ratings_to_screen

    def fake(isin: str, timeout: float = 12.0) -> dict:
        return {"label": "Good", "final_score": 71.5}

    monkeypatch.setattr("news_rag.fund_risk.fetch_public_rating", fake)
    screen = {
        "rankings": [
            {"isin": "INF000000001", "fund_name": "One Fund", "return_1y_pct": 10},
            {"isin": "INF000000002", "fund_name": "Two Fund", "return_1y_pct": 8},
        ]
    }
    _attach_rs_ratings_to_screen(screen, "name any 4 funds", ExecutionPlan())
    assert screen["rankings"][0]["rs_label"] == "Good"
    assert screen["rankings"][0]["final_score"] == 71.5
    assert screen["rankings"][1]["rs_label"] == "Good"
