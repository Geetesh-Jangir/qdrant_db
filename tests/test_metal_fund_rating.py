"""Unnamed gold and silver fund lists use the category rating API."""

from news_rag.fund_rating_categories import GOLD_SCHEME_CATEGORIES, SILVER_SCHEME_CATEGORIES
from news_rag.fund_rating_screen import (
    ensure_quality_fund_list,
    fetch_category_ratings,
    parse_rating_screen,
    run_rating_list,
)
from news_rag.insight.contracts import ExecutionPlan, ToolCall


def _rating(isin: str, *, label: str, score: float, category: str) -> dict:
    return {
        "isin": isin,
        "fundName": isin,
        "schemeCategory": category,
        "finalScore": score,
        "label": label,
        "inputs": {},
        "pillars": {},
    }


def _payload(*rows: dict) -> dict:
    return {"data": {"ratings": list(rows)}}


def test_gold_fund_list_uses_only_gold_scheme_categories():
    spec = parse_rating_screen("can you tell me names of 4 gold funds")
    assert spec is not None
    assert spec.fund_type == "others"
    assert spec.count == 4
    assert spec.spread_categories is True
    assert spec.walk_categories == GOLD_SCHEME_CATEGORIES
    assert "silver etf" not in spec.walk_categories
    assert "large cap" not in spec.walk_categories


def test_silver_fund_list_does_not_include_gold_etf():
    spec = parse_rating_screen("show me random silver funds")
    assert spec is not None
    assert spec.random_sample is True
    assert spec.walk_categories == SILVER_SCHEME_CATEGORIES
    assert "gold etf" not in spec.walk_categories


def test_gold_etf_only_stays_on_the_etf_category():
    spec = parse_rating_screen("show me 3 gold etfs")
    assert spec is not None
    assert spec.walk_categories == ("gold etf",)


def test_gold_list_spreads_etf_and_fund_of_funds():
    called: list[str] = []

    def fetch(fund_type: str, category: str) -> dict:
        assert fund_type == "others"
        called.append(category)
        return _payload(
            _rating(f"INF{category[:4].upper()}A", label="Best in category", score=80, category=category),
            _rating(f"INF{category[:4].upper()}B", label="Recommended", score=70, category=category),
        )

    result = run_rating_list("can you tell me names of 4 gold funds", fetch=fetch)
    assert set(called) == set(GOLD_SCHEME_CATEGORIES)
    categories = [row["category"] for row in result["rankings"]]
    assert len(result["rankings"]) == 4
    assert "gold etf" in categories
    assert "fund of funds-domestic-gold" in categories
    assert all(row["rs_label"] in {"Best in category", "Recommended"} for row in result["rankings"])


def test_planner_gold_sector_screen_becomes_rating_list():
    plan = ExecutionPlan(
        routed_by="planner",
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"sector": "gold", "top_n": 4, "direction": "any"},
                wave=1,
            )
        ],
    )
    ensure_quality_fund_list("can you tell me names of 4 gold funds", plan)
    call = plan.tool_calls[0]
    assert call.arguments.get("rating_screen") is True
    assert call.arguments.get("sector") == ""
    assert call.arguments.get("top_n") == 4
    assert "gold etf" in (plan.presentation_notes or "")


def test_named_gold_etf_is_not_a_category_list():
    assert parse_rating_screen("what is the nav of Nippon India Gold ETF") is None
    assert parse_rating_screen("tell me absl gold etf") is None
    assert parse_rating_screen("tell me about my gold fund") is None
    plan = ExecutionPlan(
        routed_by="planner",
        funds=["Aditya Birla Sun Life Gold ETF"],
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"sections": ["snapshot", "rating"]}, wave=1)
        ],
    )
    ensure_quality_fund_list("tell me absl gold etf", plan)
    assert [call.tool for call in plan.tool_calls] == ["get_fund_data"]


def test_my_gold_fund_does_not_add_category_screen():
    plan = ExecutionPlan(
        routed_by="planner",
        data_need="investor_holding",
        portfolio_scope="investor",
        tool_calls=[
            ToolCall(
                tool="get_investor_portfolio",
                arguments={"modules": ["holdings"], "scheme_filter": "gold"},
                wave=1,
            )
        ],
    )
    ensure_quality_fund_list("tell me about my gold fund", plan)
    assert not any(c.tool == "screen_funds_by_exposure" for c in plan.tool_calls)


def test_category_rating_request_uses_admin_header(monkeypatch):
    seen: dict = {}

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"ratings": []}}

    def fake_get(url, headers, timeout):
        seen["url"] = url
        seen["headers"] = headers
        return _Response()

    monkeypatch.setattr("news_rag.fund_rating_screen.httpx.get", fake_get)
    monkeypatch.setattr(
        "news_rag.fund_rating_screen.rupeestop_admin_request_headers",
        lambda url: {"Accept": "application/json", "Authorization": "Bearer admin-test"},
    )
    from news_rag import fund_rating_screen as screen

    screen._cache.clear()
    fetch_category_ratings("others", "gold etf")
    assert "/api/v1/admin/rs-rating/by-category/others/" in seen["url"]
    assert "gold" in seen["url"]
    assert seen["headers"]["Authorization"] == "Bearer admin-test"
