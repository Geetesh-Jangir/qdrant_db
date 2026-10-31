from news_rag.insight.capabilities.catalog import validate_capability_args
from news_rag.insight.capabilities.executor import _run_screen_funds_by_exposure


def test_validate_capability_args_keeps_rating_screen():
    out = validate_capability_args(
        "screen_funds_by_exposure",
        {"top_n": 1, "rating_screen": True, "focus_question": "flexi cap"},
    )
    assert out.get("rating_screen") is True


def test_rating_screen_uses_forced_category_spec(monkeypatch):
    calls: list[tuple[str, str]] = []

    def fake_fetch(fund_type: str, category: str) -> dict:
        calls.append((fund_type, category))
        return {
            "data": {
                "ratings": [
                    {
                        "isin": "INFTEST01",
                        "fundName": "ICICI Prudential Flexi Cap Fund - Growth",
                        "schemeCategory": "flexi cap",
                        "finalScore": 78.0,
                        "label": "Best in category",
                        "inputs": {"trailing1Y": 12.0},
                    }
                ]
            }
        }

    monkeypatch.setattr(
        "news_rag.fund_rating_screen.fetch_category_ratings",
        fake_fetch,
    )
    out = _run_screen_funds_by_exposure(
        {"top_n": 1, "rating_screen": True},
        {"question": "what this flexi cap holds"},
    )
    assert out["ok"] is True
    data = out["data"]
    assert data.get("screen_type") == "rs_rating"
    assert calls == [("equity", "flexi cap")]
    assert "ICICI" in data["rankings"][0]["fund_name"]


def test_rating_screen_uses_focus_question_not_full_compare_question(monkeypatch):
    calls: list[tuple[str, str]] = []

    def fake_fetch(fund_type: str, category: str) -> dict:
        calls.append((fund_type, category))
        return {"data": {"ratings": []}}

    monkeypatch.setattr(
        "news_rag.fund_rating_screen.fetch_category_ratings",
        fake_fetch,
    )

    def fake_catalog(_args, _ctx, question: str) -> dict:
        return {
            "ok": True,
            "data": {
                "rankings": [{"fund_name": f"Example {question}", "category": question, "return_1y_pct": 1.0}],
                "ranking_note": "Catalog fallback",
            },
        }

    monkeypatch.setattr(
        "news_rag.insight.capabilities.executor._run_catalog_screen_fallback",
        fake_catalog,
    )

    out = _run_screen_funds_by_exposure(
        {
            "top_n": 1,
            "rating_screen": True,
            "focus_question": "aggressive hybrid",
        },
        {"question": "compare a conservative hybrid and aggressive hybrid fund"},
    )
    assert calls
    assert all(pair == ("hybrid", "aggressive hybrid") for pair in calls)
    assert out["ok"] is True
    assert "aggressive hybrid" in out["data"]["rankings"][0]["fund_name"].lower()


def test_finalize_screen_adds_returns_for_compare_question(monkeypatch):
    monkeypatch.setattr(
        "news_rag.tools.enrich_rankings_with_nav",
        lambda rows, **kwargs: [{**rows[0], "return_1y_pct": 5.0, "return_1m_pct": 0.5}],
    )

    def fake_detail(isin: str) -> dict:
        return {
            "returns": {"1y": 5.0, "1m": 0.5},
            "expense_ratio": {"regular": 1.2},
        }

    class FakeIndex:
        def get_fund_detail(self, isin: str) -> dict:
            return fake_detail(isin)

    monkeypatch.setattr("news_rag.fund_search.get_fund_index", lambda: FakeIndex())

    from news_rag.insight.capabilities.executor import _finalize_screen_payload

    out = _finalize_screen_payload(
        {
            "rankings": [{"isin": "INFTEST99", "fund_name": "Test Hybrid Fund"}],
            "success": True,
        },
        {"question": "compare a conservative hybrid and aggressive hybrid fund"},
    )
    row = out["rankings"][0]
    assert row.get("return_1y_pct") == 5.0
    assert row.get("expense_ratio") == 1.2
