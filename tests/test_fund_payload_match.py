from news_rag.insight.capabilities.executor import _fund_payload_matches_fund


def test_rejects_wrong_isin_in_cached_rating_payload():
    data = {
        "fund_name": "HDFC Flexi Cap Fund - Growth",
        "fund_insights": {"isin": "INF209K01LV0", "fund_name": "Aditya Birla Sun Life Banking & PSU Debt Fund - Growth"},
        "rs_rating": {"final_score": 63, "label": "Good Choice", "fund_type": "debt"},
    }
    assert _fund_payload_matches_fund("HDFC Flexi Cap Fund - Growth", data) is False


def test_rejects_mismatched_risk_block_name():
    data = {
        "fund_name": "Invesco India Largecap Fund - Regular Plan - Growth",
        "risk": {"fund_name": "360 ONE Flexicap Fund - Regular Plan - Growth"},
    }
    assert _fund_payload_matches_fund("Invesco India Largecap Fund - Regular Plan - Growth", data) is False


def test_accepts_matching_catalog_isin(monkeypatch):
    class Index:
        def lookup_extracted_fund(self, name="", isin=""):
            return {"isin": "INF179K01608", "fund_name": name}, False, []

    monkeypatch.setattr("news_rag.fund_search.get_fund_index", lambda: Index())
    data = {
        "fund_name": "HDFC Flexi Cap Fund - Growth",
        "fund_insights": {"isin": "INF179K01608", "fund_name": "HDFC Flexi Cap Fund - Growth"},
        "rs_rating": {"final_score": 70, "label": "Recommended"},
    }
    assert _fund_payload_matches_fund("HDFC Flexi Cap Fund - Growth", data) is True
