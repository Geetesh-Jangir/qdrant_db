from news_rag.fund_rating_screen import pick_compare_pair_in_category
from news_rag.insight.capabilities.catalog import validate_capability_args
from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.plan_enforce import apply_planner_post_hooks


def test_validate_capability_args_keeps_compare_pair():
    args = validate_capability_args(
        "screen_funds_by_exposure",
        {
            "rating_screen": True,
            "focus_question": "large cap",
            "top_n": 2,
            "compare_pair": True,
            "rating_fetch_n": 20,
        },
    )
    assert args.get("compare_pair") is True
    assert args.get("rating_fetch_n") == 20


def test_random_equity_compare_uses_same_category_screen(monkeypatch):
    monkeypatch.setattr(
        "news_rag.insight.category_plan.pick_random_scheme_category_for_compare",
        lambda _q: ("mid cap", "equity"),
    )
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        fund_pick="random_in_category",
        funds=[
            "Aditya Birla Sun Life CRISIL-IBX Financial Services 3 to 6 Months Debt Index Fund - Regular Plan - Growth",
        ],
        tool_calls=[
            ToolCall(tool="screen_funds_by_exposure", arguments={"rating_screen": True, "top_n": 2}, wave=1),
            ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1),
        ],
    )
    q = "compare any random two equity funds that needs to be in category"
    out = apply_planner_post_hooks(q, plan, None)
    assert out.funds == []
    assert len(out.tool_calls) == 1
    assert out.tool_calls[0].tool == "screen_funds_by_exposure"
    args = out.tool_calls[0].arguments
    assert args.get("compare_pair") is True
    assert args.get("focus_question") == "mid cap"
    assert out.scheme_category == "mid cap"


def test_named_hdfc_invesco_compare_keeps_compare_funds():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        funds=[],
        tool_calls=[
            ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1),
        ],
    )
    q = "compare hdfc large cap fund with invesco india large cap fund"
    out = apply_planner_post_hooks(q, plan, None)
    assert out.intent == "compare"
    assert len(out.tool_calls) == 1
    assert out.tool_calls[0].tool == "compare_funds"
    assert len(out.funds) >= 2
    joined = " ".join(out.funds).lower()
    assert "hdfc" in joined and "invesco" in joined


def test_unnamed_large_cap_compare_plan():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="compare",
        funds=["Edelweiss Large Cap Fund"],
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"top_n": 2, "focus_question": "large cap", "rating_screen": True},
                wave=1,
            ),
        ],
    )
    out = apply_planner_post_hooks("compare two large cap funds", plan, None)
    assert out.intent == "compare"
    assert out.funds == []
    assert len(out.tool_calls) == 1
    args = out.tool_calls[0].arguments
    assert args.get("compare_pair") is True
    assert args.get("focus_question") == "large cap"


def test_pick_compare_pair_walks_tiers():
    def fake_fetch(_fund_type: str, _category: str) -> dict:
        return {
            "data": {
                "ratings": [
                    {
                        "isin": "INFAAA11111",
                        "fundName": "Alpha Large Cap",
                        "finalScore": 90,
                        "label": "Best in category",
                        "schemeCategory": "large cap",
                    },
                    {
                        "isin": "INFBBB22222",
                        "fundName": "Beta Large Cap",
                        "finalScore": 75,
                        "label": "Recommended",
                        "schemeCategory": "large cap",
                    },
                ],
            },
        }

    result = pick_compare_pair_in_category(
        fund_type="equity",
        category="large cap",
        fetch=fake_fetch,
    )
    assert result.get("success") is True
    labels = [r.get("rs_label") for r in result.get("rankings") or []]
    assert len(labels) == 2
    assert labels[0] == "Best in category"
    assert labels[1] == "Recommended"


def test_resolve_rating_category_debt_gold_and_typo():
    from news_rag.fund_rating_categories import CATEGORIES, resolve_rating_category

    assert resolve_rating_category("compare two random debt funds") == ("debt", "")
    assert resolve_rating_category("detb") == ("debt", "")
    assert resolve_rating_category("gold etf") == ("others", "gold etf")
    assert resolve_rating_category("silver etf") == ("others", "silver etf")
    assert resolve_rating_category("silver etf fof") == ("others", "fund of funds-domestic-silver")
    assert resolve_rating_category("golt etf") == ("others", "gold etf")
    assert resolve_rating_category("gold fund") == ("others", "")
    debt_type, debt_cat = resolve_rating_category("liquid")
    assert debt_type == "debt"
    assert debt_cat in CATEGORIES["debt"]


def test_short_category_moves_to_another_with_two_funds():
    from news_rag.fund_rating_screen import pick_compare_pair_with_fallback

    def fetch(fund_type, category):
        if category == "overnight":
            return {"data": {"ratings": [{"isin": "INFON111111", "fundName": "Only One", "label": "Recommended", "finalScore": 70}]}}
        if category == "liquid":
            return {
                "data": {
                    "ratings": [
                        {"isin": "INFLQ222222", "fundName": "Liquid A", "label": "Best in category", "finalScore": 80},
                        {"isin": "INFLQ333333", "fundName": "Liquid B", "label": "Recommended", "finalScore": 75},
                    ]
                }
            }
        return {"data": {"ratings": []}}

    result = pick_compare_pair_with_fallback(
        fund_type="debt",
        category="overnight",
        count=2,
        fetch=fetch,
    )
    isins = [row.get("isin") for row in result.get("rankings") or []]
    assert result.get("success") is True
    assert isins == ["INFLQ222222", "INFLQ333333"]
    assert "overnight" in str(result.get("ranking_note") or "")
    assert "liquid" in str(result.get("ranking_note") or "")


def test_debt_type_picks_a_debt_scheme_category(monkeypatch):
    from news_rag.fund_rating_categories import CATEGORIES
    from news_rag.insight.category_plan import pick_random_scheme_category_for_compare

    monkeypatch.setattr("random.choice", lambda pool: pool[0])
    category, fund_type = pick_random_scheme_category_for_compare("compare two random debt funds")
    assert fund_type == "debt"
    assert category == CATEGORIES["debt"][0]


def test_finalize_rewrites_debt_type_to_a_scheme_category(monkeypatch):
    from news_rag.fund_rating_categories import CATEGORIES
    from news_rag.insight.category_plan import finalize_unnamed_catalog_compare

    monkeypatch.setattr("random.choice", lambda pool: pool[0])
    plan = ExecutionPlan(
        intent="compare",
        fund_pick="random_in_category",
        planner_count=2,
        scheme_categories=["debt"],
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"focus_question": "debt", "compare_pair": True, "top_n": 2},
                wave=1,
            ),
        ],
    )
    out = finalize_unnamed_catalog_compare(plan)
    screens = [c for c in out.tool_calls if c.tool == "screen_funds_by_exposure"]
    assert screens[0].arguments["focus_question"] == CATEGORIES["debt"][0]


def test_finalize_uses_planner_count_and_one_category(monkeypatch):
    from news_rag.insight.category_plan import finalize_unnamed_catalog_compare

    monkeypatch.setattr(
        "news_rag.insight.category_plan.pick_random_scheme_category_for_compare",
        lambda _q: ("flexi cap", "equity"),
    )
    plan = ExecutionPlan(
        intent="compare",
        fund_pick="random_in_category",
        planner_count=5,
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"focus_question": "equity", "compare_pair": True, "top_n": 2},
                wave=1,
            ),
        ],
    )
    out = finalize_unnamed_catalog_compare(plan)
    screens = [c for c in out.tool_calls if c.tool == "screen_funds_by_exposure"]
    assert len(screens) == 1
    assert screens[0].arguments["focus_question"] == "flexi cap"
    assert screens[0].arguments["top_n"] == 5
    assert any(c.tool == "compare_funds" for c in out.tool_calls)


def test_finalize_splits_count_across_planner_categories():
    from news_rag.insight.category_plan import finalize_unnamed_catalog_compare

    plan = ExecutionPlan(
        intent="compare",
        fund_pick="compare_categories",
        planner_count=5,
        scheme_categories=["small cap", "large cap"],
    )
    out = finalize_unnamed_catalog_compare(plan)
    screens = [c for c in out.tool_calls if c.tool == "screen_funds_by_exposure"]
    by_cat = {c.arguments["focus_question"]: c.arguments["top_n"] for c in screens}
    assert by_cat == {"small cap": 3, "large cap": 2}
    assert any(c.tool == "compare_funds" for c in out.tool_calls)
