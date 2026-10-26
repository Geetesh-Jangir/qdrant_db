"""Regression: stock quote import and driver exposure screening prerequisites."""

from news_rag.insight.slot_router import slot_route
from news_rag.insight.capabilities.executor import execute_wave


def test_stock_quote_capability_succeeds():
    plan = slot_route("tell me about hdfc bank?")
    assert plan and plan.stocks
    w1 = [c for c in plan.tool_calls if c.wave == 1]
    ctx = {
        "question": "tell me about hdfc bank?",
        "stock_name": plan.stocks[0],
        "window_days": plan.window_days,
    }
    results = execute_wave(w1, ctx)
    snap = next(r for r in results if r.get("tool") == "get_market_snapshot")
    assert snap.get("ok"), snap.get("error")
    data = snap.get("data") or {}
    assert "stock_quote" in data or data.get("stock_quote") is not None


def test_driver_exposure_screen_no_longer_needs_sector_picks_first():
    q = "Why is crude oil rising and how does it affect energy mutual funds in India?"
    plan = slot_route(q)
    w1 = [c for c in plan.tool_calls if c.wave == 1]
    ctx = {"question": q, "window_days": plan.window_days, "direction": "any", "top_n": 5}
    results = execute_wave(w1, ctx)
    screen = next(r for r in results if r.get("tool") == "screen_funds_by_exposure")
    assert screen.get("error") != "needs_sector_picks_first"
    assert screen.get("ok"), screen.get("error")


def test_crude_increase_compound_question_screens_negatively_affected_funds():
    q = (
        "why the crude price is increase day by day? and which sectors are affected? "
        "which funds are affected negatively by it?"
    )
    plan = slot_route(q)
    assert plan is not None
    tools = [c.tool for c in plan.tool_calls]
    assert "screen_funds_by_exposure" in tools
    w1 = [c for c in plan.tool_calls if c.wave == 1]
    ctx = {
        "question": q,
        "window_days": plan.window_days,
        "drivers": [d["id"] for d in (plan.drivers or [])],
        "top_n": 5,
    }
    results = execute_wave(w1, ctx)
    screen = next(r for r in results if r.get("tool") == "screen_funds_by_exposure")
    assert screen.get("error") != "no_sectors_for_driver"
    assert screen.get("ok"), screen.get("error")
    rankings = (screen.get("data") or {}).get("rankings") or []
    assert len(rankings) >= 1


def test_fund_manager_query_uses_rupeestop_api():
    q = "tell me about fund manager of hdfc large cap fund?"
    plan = slot_route(q)
    assert plan is not None
    assert plan.answer_mode.value == "DATA_ONLY"
    tc = next(c for c in plan.tool_calls if c.tool == "get_fund_data")
    assert tc.arguments.get("modules") == ["managers"]
    w1 = [c for c in plan.tool_calls if c.wave == 1]
    ctx = {"question": q, "window_days": plan.window_days, "fund_names": plan.funds}
    results = execute_wave(w1, ctx, fund_names=plan.funds)
    fund = next(r for r in results if r.get("tool") == "get_fund_data")
    assert fund.get("ok"), fund.get("error")
    mgr = (fund.get("data") or {}).get("managers") or {}
    current = mgr.get("current") or []
    assert current, "expected current manager from API"
    assert any("rahul" in str(m.get("name") or "").lower() for m in current)


def test_fof_fund_screen_returns_fof_schemes():
    from news_rag.tools import run_screen_funds, screen_hints_from_question

    q = "tell me any 3 fof funds which are performing positive in last 1 year?"
    assert screen_hints_from_question(q)["category"] == "Fund of Funds"
    r = run_screen_funds(question=q, direction="positive", top_n=3, return_window="1Y")
    rows = (r.get("data") or {}).get("rankings") or []
    assert len(rows) == 3
    for row in rows:
        blob = f"{row.get('fund_name') or ''}".lower()
        assert "fof" in blob or "fund of fund" in blob


def test_defence_fund_screen_uses_defense_category():
    from news_rag.tools import run_screen_funds, screen_hints_from_question

    q = "tell me any 2 defence funds which are performing positive in last 1 year?"
    assert screen_hints_from_question(q)["category"] == "Defense & Aerospace"
    r = run_screen_funds(question=q, direction="positive", top_n=2, return_window="1Y")
    rows = (r.get("data") or {}).get("rankings") or []
    assert len(rows) >= 1
    for row in rows:
        name = (row.get("fund_name") or "").lower()
        cat = (row.get("category") or "").lower()
        assert "defen" in name or "defen" in cat


def test_hdfc_equity_screen_uses_equity_scheme_type():
    from news_rag.tools import run_screen_funds

    q = "tell me any 2 hdfc equity funds which are performing positive in last 1 year?"
    r = run_screen_funds(question=q, direction="positive", top_n=2, return_window="1Y")
    rows = (r.get("data") or {}).get("rankings") or []
    assert len(rows) == 2
    for row in rows:
        assert str(row.get("scheme_type") or "").lower() == "equity"
        assert "HDFC" in str(row.get("fund_name") or "")


def test_funds_invested_in_hdfc_bank_not_hdfc_amc_catalog():
    from news_rag.tools import screen_hints_from_question, run_screen_funds

    q = "2 equity funds which are invested in hdfc bank"
    hints = screen_hints_from_question(q)
    assert hints["stock_name"].lower().startswith("hdfc")
    assert not hints["amc"]
    r = run_screen_funds(question=q, direction="any", top_n=2)
    rows = (r.get("data") or {}).get("rankings") or []
    assert len(rows) >= 1
    assert all(str(row.get("scheme_type") or "").lower() == "equity" for row in rows)


def test_infer_return_window_two_years_from_question():
    from news_rag.tools import infer_return_window, return_window_days

    q = "tell me any 5 random funds which are performing positive in last 2 years?"
    assert infer_return_window(q) == "2Y"
    assert return_window_days("2Y") == 730


def test_slot_route_two_year_fund_screen_plan():
    q = "tell me any 5 random funds which are performing positive in last 2 years?"
    plan = slot_route(q)
    assert plan is not None
    assert plan.window_days == 730
    tc = next(c for c in plan.tool_calls if c.tool == "screen_funds_by_exposure")
    assert tc.arguments.get("return_window") == "2Y"


def test_random_five_positive_1y_funds_screen():
    q = "name any 5 random funds which are working positive in last one year?"
    from news_rag.insight.brief import random_fund_count

    assert random_fund_count(q) == 5
    plan = slot_route(q)
    assert plan is not None
    assert plan.answer_mode.value == "DATA_ONLY"
    w1 = [c for c in plan.tool_calls if c.wave == 1]
    ctx = {"question": q, "window_days": plan.window_days}
    results = execute_wave(w1, ctx)
    screen = next(r for r in results if r.get("tool") == "screen_funds_by_exposure")
    assert screen.get("ok"), screen.get("error")
    rankings = (screen.get("data") or {}).get("rankings") or []
    assert len(rankings) == 5
    for row in rankings:
        assert float(row.get("return_1y_pct") or 0) > 0


def test_rbi_repo_increase_screens_negatively_affected_funds():
    q = (
        "why the rbi repo rate has increased? and which sectors are affected? "
        "which funds are affected negatively by it?"
    )
    plan = slot_route(q)
    assert plan is not None
    w1 = [c for c in plan.tool_calls if c.wave == 1]
    ctx = {
        "question": q,
        "window_days": plan.window_days,
        "drivers": [d["id"] for d in (plan.drivers or [])],
    }
    results = execute_wave(w1, ctx)
    screen = next(r for r in results if r.get("tool") == "screen_funds_by_exposure")
    assert screen.get("error") != "no_sectors_for_driver"
    assert screen.get("ok"), screen.get("error")
    assert len((screen.get("data") or {}).get("rankings") or []) >= 1
