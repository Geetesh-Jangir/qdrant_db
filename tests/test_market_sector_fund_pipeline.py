"""Tests for compound market + sector + directional mutual fund pipeline."""

from __future__ import annotations

from unittest.mock import patch
from news_rag.ask_plan import AskPlan, PlannedTool
from news_rag.plan_enrich import enrich_ask_plan
from news_rag.tools import enrich_rankings_with_nav, explicit_fund_count, select_funds_by_nav
from news_rag.ask_execution import ExecutionBundle
from news_rag.ask_composer import _finalize_compose, _build_ranked_fund_bullets


def _mock_nav_history(isin: str):
    if isin == "INF1":
        return {
            "success": True,
            "latest_nav": 150.0,
            "latest_date": "2026-03-30",
            "stats": {
                "1W": {"change_pct": 1.25},
                "1M": {"change_pct": 4.50},
            },
        }
    if isin == "INF2":
        return {
            "success": True,
            "latest_nav": 80.0,
            "latest_date": "2026-03-30",
            "stats": {
                "1W": {"change_pct": -2.10},
                "1M": {"change_pct": -6.30},
            },
        }
    return {"success": False}


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
def test_enrich_rankings_with_nav_positive(mock_nav):
    candidates = [
        {"isin": "INF2", "fund_name": "Fund Negative", "sector_weight_pct": 40.0, "matched_sectors": ["IT"]},
        {"isin": "INF1", "fund_name": "Fund Positive", "sector_weight_pct": 20.0, "matched_sectors": ["IT"]},
    ]
    res = enrich_rankings_with_nav(candidates, direction="positive", top_n=2)
    assert len(res) == 1
    assert res[0]["isin"] == "INF1"
    assert res[0]["return_1m_pct"] == 4.50
    assert res[0]["return_1w_pct"] == 1.25
    assert res[0]["nav_direction_match"] is True


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
def test_enrich_rankings_with_nav_negative(mock_nav):
    candidates = [
        {"isin": "INF1", "fund_name": "Fund Positive", "sector_weight_pct": 20.0, "matched_sectors": ["IT"]},
        {"isin": "INF2", "fund_name": "Fund Negative", "sector_weight_pct": 40.0, "matched_sectors": ["IT"]},
    ]
    res = enrich_rankings_with_nav(candidates, direction="negative", top_n=2)
    assert len(res) == 1
    assert res[0]["isin"] == "INF2"
    assert res[0]["return_1m_pct"] == -6.30
    assert res[0]["return_1w_pct"] == -2.10


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
def test_enrich_rankings_with_nav_any(mock_nav):
    candidates = [
        {"isin": "INF1", "fund_name": "Fund Positive", "sector_weight_pct": 20.0, "matched_sectors": ["IT"]},
        {"isin": "INF2", "fund_name": "Fund Negative", "sector_weight_pct": 40.0, "matched_sectors": ["IT"]},
    ]
    res = enrich_rankings_with_nav(candidates, direction="any", top_n=2, sort_by="performance")
    assert len(res) == 2
    assert res[0]["isin"] == "INF1"
    assert res[1]["isin"] == "INF2"


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
def test_enrich_rankings_performance_beats_exposure_weight(mock_nav):
    """Higher sector weight must not beat better 1M NAV when sort_by=performance."""
    candidates = [
        {"isin": "INF2", "fund_name": "Heavy loser", "sector_weight_pct": 80.0, "matched_sectors": ["Banks"]},
        {"isin": "INF1", "fund_name": "Lighter winner", "sector_weight_pct": 30.0, "matched_sectors": ["Banks"]},
    ]
    res = enrich_rankings_with_nav(candidates, direction="any", top_n=1, sort_by="performance")
    assert res[0]["isin"] == "INF1"


def test_plan_enrich_sets_affected_funds_when_question_asks_funds():
    plan = AskPlan(
        tools=[
            PlannedTool(tool="common_market_news"),
            PlannedTool(tool="sector_news"),
        ],
        affected_funds="none",
    )
    q = "tell me whats happening in the market right now and what are the sectors which are performing well and then which mutual funds are working well"
    enriched = enrich_ask_plan(q, plan)
    assert enriched.affected_funds == "none"
    assert {t.tool for t in enriched.tools} == {"common_market_news", "sector_news"}


def test_build_ranked_fund_bullets():
    funds = [
        {
            "fund_name": "ICICI Prudential Technology Fund",
            "sector_weight_pct": 34.5,
            "matched_sectors": ["Information Technology"],
            "return_1m_pct": 5.2,
            "return_1w_pct": 1.1,
        }
    ]
    bullets = _build_ranked_fund_bullets(funds)
    assert len(bullets) == 1
    b = bullets[0]
    assert "**ICICI Prudential Technology Fund**" in b
    assert "**34.5%**" in b
    assert "**Information Technology**" in b
    assert "**+5.2%**" in b
    assert "**+1.1%**" in b


def test_finalize_compose_includes_ranked_funds_for_fund_query():
    from news_rag.name_resolution import ResolvedNames
    bundle = ExecutionBundle(names=ResolvedNames())
    bundle.tool_results["affected_funds_post"] = {
        "ok": True,
        "data": {
            "rankings": [
                {
                    "fund_name": "Nippon India Power & Infra Fund",
                    "sector_weight_pct": 28.0,
                    "matched_sectors": ["Power"],
                    "return_1m_pct": 3.8,
                    "return_1w_pct": 0.9,
                }
            ]
        },
    }
    initial_bullets = [
        "**Market Backdrop** — Indices under pressure from global cues.",
        "**Information Technology** — Strong exports boost realization.",
    ]
    q = "what is happening in market and what sectors and mutual funds are performing well"
    headline, narrative, bullets = _finalize_compose(
        "Headline",
        "Banks gained while IT lagged.",
        initial_bullets + ["Banks gained while IT lagged."],
        bundle,
        digests=[],
        market_pulse_clusters=[{"label": "Theme 1", "article_count": 2}],
        question=q,
        answer_parts=q,
        sentiment="positive",
        evidence_text="no fund figures here",
    )
    assert narrative == "Banks gained while IT lagged."
    assert headline == "Headline"
    assert any("Information Technology" in b for b in bullets)
    assert not any("Nippon India Power" in b for b in bullets)
    assert not any(b == "Banks gained while IT lagged." for b in bullets)


def test_enrich_does_not_rewrite_planner_sentiment():
    plan = AskPlan(
        tools=[PlannedTool(tool="common_market_news"), PlannedTool(tool="sector_news")],
        sentiment="any",
        affected_funds="after_news",
    )
    q = "what are the sectors performing well and which mutual funds are working well"
    enriched = enrich_ask_plan(q, plan)
    assert enriched.sentiment == "any"
    assert explicit_fund_count("which mutual funds are working well") is None
    assert explicit_fund_count("show me the top 4 banking mutual funds") == 4
    assert explicit_fund_count("give three funds in IT") == 3


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
def test_select_funds_positive_does_not_list_drawdowns(mock_nav):
    rows = [
        {
            "isin": "INF2",
            "fund_name": "Bank Fund Down",
            "sector_weight_pct": 60.0,
            "sector_purity": "dedicated_sectoral",
        }
    ]
    picked, all_drawdown, note = select_funds_by_nav(
        rows, direction="positive", top_n=5, count_explicit=False
    )
    assert picked == []
    assert all_drawdown is True
    assert "positive" in note.lower()


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
def test_select_funds_positive_skips_negative(mock_nav):
    rows = [
        {"isin": "INF2", "fund_name": "Down", "sector_purity": "dedicated_sectoral", "sector_weight_pct": 40},
        {"isin": "INF1", "fund_name": "Up", "sector_purity": "dedicated_sectoral", "sector_weight_pct": 20},
    ]
    picked, all_drawdown, _note = select_funds_by_nav(
        rows, direction="positive", top_n=5, count_explicit=False
    )
    assert all_drawdown is False
    assert [r["isin"] for r in picked] == ["INF1"]


def test_plan_enrich_adds_sector_funds_for_banking_best_query():
    plan = AskPlan(
        tools=[
            PlannedTool(tool="macro_news_enhanced", semantic_query="RBI repo rate India"),
            PlannedTool(tool="sector_news", semantic_query="banking credit India"),
        ],
        affected_funds="none",
    )
    q = (
        "What are the latest updates on RBI monetary policy, how does it affect banking and financials, "
        "and which banking mutual funds have performed best over the last month?"
    )
    enriched = enrich_ask_plan(q, plan)
    assert [t.tool for t in enriched.tools] == ["macro_news_enhanced", "sector_news"]


def test_finalize_compose_does_not_duplicate_when_llm_wrote_fund_bullets():
    from news_rag.name_resolution import ResolvedNames
    bundle = ExecutionBundle(names=ResolvedNames())
    bundle.tool_results["affected_funds_post"] = {
        "ok": True,
        "data": {
            "rankings": [
                {
                    "fund_name": "Nippon India Power & Infra Fund",
                    "sector_weight_pct": 28.0,
                    "matched_sectors": ["Power"],
                    "return_1m_pct": 3.8,
                    "return_1w_pct": 0.9,
                }
            ]
        },
    }
    llm_bullets = [
        "**Market Backdrop** — Indices under pressure from global cues.",
        "**Information Technology** — Strong exports boost realization.",
        "**Top Fund: ICICI Prudential Technology Fund** — Holds **34.2%** in Information Technology with **+4.8%** return.",
    ]
    q = "what is happening in market and what sectors and mutual funds are performing well"
    _, narrative, bullets = _finalize_compose(
        "Headline",
        "The tape is mixed.",
        llm_bullets,
        bundle,
        digests=[],
        market_pulse_clusters=[{"label": "Theme 1", "article_count": 2}],
        question=q,
        answer_parts=q,
        sentiment="positive",
        evidence_text="34.2 4.8",
    )
    assert narrative == "The tape is mixed."
    assert any("ICICI Prudential Technology Fund" in b for b in bullets)
    assert not any("Nippon India Power" in b for b in bullets)


def _week_up_month_down(isin: str):
    if isin == "MIX":
        return {
            "success": True,
            "latest_nav": 40.0,
            "latest_date": "2026-03-30",
            "stats": {"1W": {"change_pct": 1.1}, "1M": {"change_pct": -2.4}},
        }
    return {"success": False}


@patch("news_rag.tools.get_fund_nav_history", side_effect=_week_up_month_down)
def test_positive_week_keeps_a_fund_that_is_down_on_the_month(mock_nav):
    rows = [{"isin": "MIX", "fund_name": "Week Up", "sector_weight_pct": 12.0}]
    week, _, _note = select_funds_by_nav(
        rows, direction="positive", top_n=3, count_explicit=True, return_window="1W"
    )
    month, all_drawdown, note = select_funds_by_nav(
        rows, direction="positive", top_n=3, count_explicit=True, return_window="1M"
    )
    assert [row["fund_name"] for row in week] == ["Week Up"]
    assert week[0]["return_1w_pct"] == 1.1
    assert month == []
    assert all_drawdown is True
    assert "positive" in note.lower()


@patch("news_rag.scoped_retrieve.retrieve_scoped_news")
@patch("news_rag.tools.rank_funds_by_sector_exposure")
@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
@patch(
    "news_rag.tools._catalog_candidates",
    return_value=[{"isin": "INF1", "fund_name": "Large One", "category": "Large Cap"}],
)
def test_large_cap_screen_does_not_call_news(mock_catalog, mock_nav, mock_rank, mock_news):
    from news_rag.tools import run_screen_funds

    result = run_screen_funds(category="Large Cap", direction="positive", return_window="1M", top_n=3)
    mock_news.assert_not_called()
    mock_rank.assert_not_called()
    assert result["ok"] is True
    assert result["data"]["rankings"][0]["fund_name"] == "Large One"


def test_compare_of_two_screened_funds_returns_names_and_window_return():
    from news_rag.tools import run_compare_funds

    result = run_compare_funds(
        rows=[
            {"isin": "INFA", "fund_name": "Alpha", "return_1w_pct": 1.2, "latest_nav": 10},
            {"isin": "INFB", "fund_name": "Beta", "return_1w_pct": 0.4, "latest_nav": 12},
        ],
        compare_on="nav",
        return_window="1W",
        top_n=2,
    )
    funds = result["data"]["funds"]
    assert [row["fund_name"] for row in funds] == ["Alpha", "Beta"]
    assert [row["return_pct"] for row in funds] == [1.2, 0.4]
    assert funds[0]["return_window"] == "1W"
    assert "holdings" not in funds[0]


@patch("news_rag.tools.rank_funds_by_sector_exposure")
@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
@patch(
    "news_rag.tools._catalog_candidates",
    return_value=[{"isin": "INF1", "fund_name": "HDFC Large", "amc": "HDFC Mutual Fund"}],
)
def test_amc_only_screen_does_not_require_a_sector_ranking(mock_catalog, mock_nav, mock_rank):
    from news_rag.ask_agent import AGENT_SYSTEM
    from news_rag.tools import run_screen_funds, screen_hints_from_question

    hints = screen_hints_from_question("give me any name of the funds provided by HDFC")
    assert hints["amc"].lower() == "hdfc"
    assert hints["sector_name"] == ""
    assert "does not need a news search" in AGENT_SYSTEM
    result = run_screen_funds(amc="HDFC", direction="any", top_n=1, question="funds from HDFC")
    mock_rank.assert_not_called()
    assert result["data"]["rankings"][0]["fund_name"] == "HDFC Large"


def test_short_large_cap_name_question_is_not_refused():
    from news_rag.guardrails import check_guardrails

    result = check_guardrails("give me any two large cap funds name?")
    assert result.outcome == "pass"


def _dated_nav(isin: str):
    if isin == "STALE":
        return {
            "success": True,
            "latest_nav": 262.0,
            "latest_date": "2026-04-30",
            "stats": {"1W": {"change_pct": 1.0}, "1M": {"change_pct": 7.47}},
        }
    if isin == "FRESH":
        return {
            "success": True,
            "latest_nav": 168.0,
            "latest_date": "2026-10-06",
            "stats": {"1W": {"change_pct": 0.2}, "1M": {"change_pct": 0.14}},
        }
    return {"success": False}


@patch("news_rag.tools.get_fund_nav_history", side_effect=_dated_nav)
def test_stale_nav_is_dropped(mock_nav):
    rows = [
        {"isin": "STALE", "fund_name": "Quantum Nifty 50 ETF"},
        {"isin": "FRESH", "fund_name": "Taurus Large Cap"},
    ]
    picked, _draw, _note = select_funds_by_nav(
        rows, direction="positive", top_n=5, count_explicit=True, return_window="1M"
    )
    assert [row["fund_name"] for row in picked] == ["Taurus Large Cap"]


@patch("news_rag.tools.run_affected_funds")
@patch("news_rag.affected_sectors.pick_affected_sectors")
@patch(
    "news_rag.tools._articles_for_affected_question",
    return_value=[{"body": "Banks gain as a rate hike lifts margins. Real estate is hurt."}],
)
def test_crude_affected_question_ranks_banks_not_petroleum(mock_articles, mock_pick, mock_rank):
    from news_rag.tools import run_screen_funds

    mock_pick.return_value = [
        {"name": "Banks", "direction": "positive", "reason": "A rate hike lifts bank margins."}
    ]
    mock_rank.return_value = {
        "ok": True,
        "data": {
            "rankings": [
                {
                    "fund_name": "Bank Fund",
                    "isin": "INFB",
                    "return_1m_pct": 1.2,
                    "matched_sectors": ["Banks"],
                }
            ]
        },
    }
    result = run_screen_funds(
        category="Large Cap",
        direction="positive",
        top_n=2,
        question="which funds are positively affected by the crude price increase?",
    )
    assert mock_rank.call_args.kwargs["sector_names"] == ["Banks"]
    assert "Petroleum" not in mock_rank.call_args.kwargs["sector_names"]
    assert mock_rank.call_args.kwargs["allow_broad_fallback"] is False
    assert result["data"]["rankings"][0]["fund_name"] == "Bank Fund"


def test_positive_picker_prompt_asks_only_for_sectors_that_benefit():
    from news_rag.affected_sectors import build_picker_prompt

    prompt = build_picker_prompt(
        question="which funds are positively affected by the crude price increase?",
        direction="positive",
        articles=[{"body": "Banks gain."}],
        sector_names=["Banks", "Realty"],
    )
    assert "only sectors that benefit" in prompt.lower()


def test_picker_drops_a_sector_name_that_is_not_in_the_list():
    from news_rag.affected_sectors import accepted_sectors

    kept = accepted_sectors(
        [
            {"name": "Banks", "direction": "positive", "reason": "Margins rise."},
            {"name": "Not A Real Sector", "direction": "positive", "reason": "Invented."},
        ],
        ["Banks", "Realty"],
        direction="positive",
    )
    assert [row["name"] for row in kept] == ["Banks"]


def _weight_nav(isin: str):
    if isin == "HIGH":
        return {
            "success": True,
            "latest_nav": 10,
            "latest_date": "2026-10-06",
            "stats": {"1M": {"change_pct": -1.0}, "1W": {"change_pct": -0.2}},
        }
    if isin == "LOW":
        return {
            "success": True,
            "latest_nav": 12,
            "latest_date": "2026-10-06",
            "stats": {"1M": {"change_pct": 5.0}, "1W": {"change_pct": 1.0}},
        }
    return {"success": False}


@patch("news_rag.affected_sectors.pick_affected_sectors")
@patch("news_rag.tools.get_fund_nav_history", side_effect=_weight_nav)
@patch(
    "news_rag.tools._sector_candidates",
    return_value=[
        {"isin": "LOW", "fund_name": "Light Finance", "sector_weight_pct": 10, "sector_purity": "dedicated_sectoral"},
        {"isin": "HIGH", "fund_name": "Heavy Finance", "sector_weight_pct": 40, "sector_purity": "dedicated_sectoral"},
    ],
)
@patch("news_rag.tools._catalog_candidates")
def test_finance_exposure_keeps_sector_weight_order(mock_catalog, mock_sector, mock_nav, mock_pick):
    from news_rag.tools import run_screen_funds

    result = run_screen_funds(
        category="Large Cap",
        direction="positive",
        top_n=2,
        question="name any two funds that are heavily invested in finance sector?",
    )
    mock_catalog.assert_not_called()
    mock_pick.assert_not_called()
    names = [row["fund_name"] for row in result["data"]["rankings"]]
    assert names == ["Heavy Finance", "Light Finance"]
    assert result["data"]["rankings"][0]["sector_weight_pct"] == 40.0


@patch("news_rag.tools.get_fund_nav_history", side_effect=_mock_nav_history)
@patch("news_rag.tools._catalog_candidates", return_value=[{"isin": "INF1", "fund_name": "Mixed Fund"}])
@patch("news_rag.tools._sector_candidates", return_value=[])
def test_performing_well_does_not_force_large_cap(mock_sector, mock_catalog, mock_nav):
    from news_rag.tools import run_screen_funds

    run_screen_funds(
        category="Large Cap",
        direction="positive",
        top_n=3,
        question="what are the funds that are performing well?",
    )
    assert mock_catalog.called
    assert all(not (call.kwargs.get("category") or "") for call in mock_catalog.call_args_list)


def test_bhel_resolves_to_the_archive_company_and_compare_keeps_holders():
    from news_rag.ask_agent import _rows_for_compare
    from news_rag.ask_execution import ExecutionBundle
    from news_rag.ask_plan import PlannedTool
    from news_rag.name_resolution import ResolvedNames
    from news_rag.stock_fund_ranking import _match_aggregated
    from news_rag.tools import screen_hints_from_question

    matched = _match_aggregated("BHEL")
    assert matched is not None
    assert matched[0] == "Bharat Heavy Electricals Limited"
    hints = screen_hints_from_question("compare any two funds that holds bhel stocks?")
    assert hints["stock_name"].lower() == "bhel"
    bundle = ExecutionBundle(names=ResolvedNames())
    bundle.tool_results["screen_funds_0"] = {
        "ok": True,
        "data": {
            "stock_name": "Bharat Heavy Electricals Limited",
            "rankings": [
                {"fund_name": "Holder A", "isin": "INFA", "weight_pct": 2.1, "holding_name": matched[0]},
                {"fund_name": "Holder B", "isin": "INFB", "weight_pct": 1.4, "holding_name": matched[0]},
                {"fund_name": "No Holding", "isin": "INFC", "return_1m_pct": 3.0},
            ],
        },
    }
    rows = _rows_for_compare(bundle, PlannedTool(tool="compare_funds", stock_name="BHEL", top_n=2))
    assert [row["fund_name"] for row in rows] == ["Holder A", "Holder B"]


def _bank_nav(isin: str):
    if isin == "DOWN":
        return {
            "success": True,
            "latest_nav": 10,
            "latest_date": "2026-10-06",
            "stats": {"1M": {"change_pct": -2.0}, "1W": {"change_pct": -0.4}},
        }
    if isin == "UP":
        return {
            "success": True,
            "latest_nav": 12,
            "latest_date": "2026-10-06",
            "stats": {"1M": {"change_pct": 1.5}, "1W": {"change_pct": 0.3}},
        }
    return {"success": False}


@patch("news_rag.tools.get_fund_nav_history", side_effect=_bank_nav)
@patch(
    "news_rag.tools._sector_candidates",
    return_value=[
        {
            "isin": "DOWN",
            "fund_name": "Dedicated Bank",
            "sector_weight_pct": 80,
            "sector_purity": "dedicated_sectoral",
        },
        {
            "isin": "UP",
            "fund_name": "Heavy Bank Mix",
            "sector_weight_pct": 35,
            "sector_purity": "diversified_equity",
        },
    ],
)
def test_banking_heavy_and_positive_month_keeps_the_fund_that_is_up(mock_sector, mock_nav):
    from news_rag.tools import run_screen_funds

    result = run_screen_funds(
        direction="positive",
        top_n=1,
        question="name any 1 funds that are heavily invested in banking sector and that are performing positive in last one month",
    )
    names = [row["fund_name"] for row in result["data"]["rankings"]]
    assert names == ["Heavy Bank Mix"]
    assert result["data"]["return_window"] == "1M"


@patch("news_rag.tools.get_fund_nav_history", side_effect=_bank_nav)
@patch("news_rag.stock_fund_ranking.funds_holding_stock")
@patch("news_rag.affected_sectors.pick_affected_companies", return_value=["Reliance Industries Limited"])
@patch("news_rag.tools.run_affected_funds")
@patch(
    "news_rag.affected_sectors.pick_affected_sectors",
    return_value=[{"name": "Banks", "direction": "positive", "reason": "Rates help banks."}],
)
@patch("news_rag.tools._articles_for_affected_question", return_value=[{"body": "Reliance refines crude."}])
def test_crude_with_no_sector_funds_uses_a_company_from_the_articles(
    mock_articles, mock_sectors, mock_rank, mock_companies, mock_holders, mock_nav
):
    from news_rag.tools import run_screen_funds

    mock_rank.return_value = {"ok": True, "data": {"rankings": []}}
    mock_holders.return_value = {
        "stock_name": "Reliance Industries Limited",
        "funds": [{"isin": "UP", "fund_name": "Energy Holder", "weight_pct": 4.2, "holding_name": "Reliance Industries Limited"}],
        "note": "",
    }
    result = run_screen_funds(
        top_n=1,
        question="name one fund that is affected by crude news?",
    )
    assert result["data"]["rankings"][0]["fund_name"] == "Energy Holder"
    mock_companies.assert_called()
