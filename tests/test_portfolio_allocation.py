from news_rag.fund_rating_screen import RatingScreenSpec, run_rating_list
from news_rag.insight.contracts import ExecutionPlan, ScopeKind
from news_rag.insight.plan_enforce import apply_planner_post_hooks
from news_rag.insight.portfolio_allocation import allocate


def test_balanced_equity_by_bucket():
    expected = {
        0.5: 0,
        2: 20,
        4: 40,
        6: 55,
        8: 70,
        12: 80,
    }
    for years, equity in expected.items():
        result = allocate(years, "balanced", False)
        assert result.equity_pct == equity
        assert result.equity_pct + result.debt_pct + result.gold_pct == 100


def test_equity_more_on_ten_years_stays_within_cap():
    result = allocate(10, "equity_more", False)
    assert result.equity_pct == 90
    assert result.mismatch


def test_equity_more_on_very_short_stays_at_zero():
    result = allocate(0.5, "equity_more", False)
    assert result.equity_pct == 0
    assert result.mismatch


def test_debt_more_on_ten_years_keeps_equity_floor():
    result = allocate(10, "debt_more", False)
    assert result.equity_pct >= 60


def test_gold_on_medium_long_is_five_and_sums_to_100():
    result = allocate(6, "balanced", True)
    assert result.gold_pct == 5
    assert result.equity_pct + result.debt_pct + result.gold_pct == 100
    assert any(row.category == "gold etf" for row in result.categories)


def test_gold_on_two_years_stays_zero():
    result = allocate(2, "balanced", True)
    assert result.gold_pct == 0
    assert result.mismatch
    assert not any(row.category == "gold etf" for row in result.categories)


def test_unspecified_preference_is_balanced():
    result = allocate(10, "unspecified", False)
    assert result.assumed_preference
    assert result.preference_used == "balanced"
    assert result.equity_pct == 80


def test_very_long_categories_are_equity_diverse_without_gold():
    result = allocate(12, "balanced", False)
    names = [row.category for row in result.categories]
    assert "large cap" in names and "mid cap" in names and "small cap" in names
    assert "corporate bond" in names
    assert "gold etf" not in names


def test_very_short_is_debt_only():
    result = allocate(0.4, "balanced", False)
    assert result.equity_pct == 0
    assert all(row.fund_type == "debt" for row in result.categories)


def test_one_rated_fund_per_category_does_not_fill_with_gold():
    def _row(isin: str, label: str, score: float, category: str) -> dict:
        return {
            "isin": isin,
            "fundName": isin,
            "schemeCategory": category,
            "finalScore": score,
            "label": label,
            "benchmark": "n/a",
            "asOnDate": "2026-10-31",
            "inputs": {},
            "pillars": {},
        }

    def fetch(fund_type: str, category: str) -> dict:
        if category == "gold etf":
            ratings = [
                _row(f"INFGOLD{i}", "Best in category", 90 - i, category) for i in range(5)
            ]
        elif category == "large cap":
            ratings = [_row("INFLARGE1", "Best in category", 80, category)]
        else:
            ratings = []
        return {"data": {"ratings": ratings}}

    spec = RatingScreenSpec(
        count=2,
        fund_type="equity",
        category="",
        locked=False,
        label="",
        min_score=None,
        highest_score=False,
        return_window="",
        return_direction="",
        compare_category=False,
        random_sample=False,
        amc="",
        suggestion="rated",
        walk_category_pairs=(("equity", "large cap"), ("others", "gold etf")),
        spread_categories=True,
        one_per_category=True,
    )
    result = run_rating_list("portfolio", spec=spec, fetch=fetch)
    names = [row["fund_name"] for row in result["rankings"]]
    assert len(result["rankings"]) == 2
    assert sum(1 for row in result["rankings"] if row["category"] == "gold etf") == 1

    no_gold = RatingScreenSpec(
        count=1,
        fund_type="equity",
        category="",
        locked=False,
        label="",
        min_score=None,
        highest_score=False,
        return_window="",
        return_direction="",
        compare_category=False,
        random_sample=False,
        amc="",
        suggestion="rated",
        walk_category_pairs=(("equity", "large cap"),),
        spread_categories=True,
        one_per_category=True,
    )
    only_equity = run_rating_list("portfolio", spec=no_gold, fetch=fetch)
    assert [row["category"] for row in only_equity["rankings"]] == ["large cap"]
    del names


def test_missing_horizon_asks_and_does_not_call_tools():
    plan = ExecutionPlan(routed_by="planner", data_need="portfolio_allocation", horizon_years=None)
    out = apply_planner_post_hooks("what should be the ideal portfolio", plan, None)
    assert out.scope_kind == ScopeKind.NEEDS_CLARIFICATION
    assert not out.tool_calls
    assert "years" in (out.direct_reply or "").lower()


def test_ten_year_unspecified_screen_matches_allocator_and_skips_gold():
    plan = ExecutionPlan(
        routed_by="planner",
        data_need="portfolio_allocation",
        horizon_years=10,
        asset_preference="unspecified",
        include_gold=False,
    )
    out = apply_planner_post_hooks("ideal portfolio for 10 years", plan, None)
    screen = next(call for call in out.tool_calls if call.tool == "screen_funds_by_exposure")
    expected = allocate(10, "unspecified", False)
    assert screen.arguments["top_n"] == len(expected.pairs())
    assert screen.arguments["top_n"] != 7 or len(expected.pairs()) == 7
    assert all(pair[1] != "gold etf" for pair in screen.arguments["allocation_pairs"])
    assert "illustrative allocation" in (out.presentation_notes or "").lower()
