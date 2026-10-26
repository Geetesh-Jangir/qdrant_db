"""Guardrails and domain intake — entity-aware scope, not keyword length."""

from news_rag.guardrails import check_guardrails
from news_rag.domain_intake import scan_question_domain, question_in_finance_scope
from news_rag.insight.slot_router import slot_route


def test_hdfc_bank_passes_guardrails():
    q = "tell me about hdfc bank?"
    result = check_guardrails(q)
    assert result.outcome == "pass"
    scan = scan_question_domain(q)
    assert "hdfc bank" in [s.lower() for s in scan.stocks]


def test_hdfc_bank_short_happening_passes():
    q = "whats happening with the hdfc bank?"
    assert check_guardrails(q).outcome == "pass"
    in_scope, scan = question_in_finance_scope(q)
    assert in_scope
    assert scan.stocks


def test_slot_router_plans_stock_overview():
    plan = slot_route("tell me about hdfc bank?")
    assert plan is not None
    assert plan.scope_kind.value == "in_scope"
    assert plan.stocks
    tools = [c.tool for c in plan.tool_calls]
    assert "get_market_snapshot" in tools


def test_crude_why_not_misrouted_to_random_fund():
    q = "why the crude price is increase day by day?"
    plan = slot_route(q)
    assert plan is not None and plan.scope_kind.value == "in_scope"
    assert plan.funds == [] or "get_fund_data" not in [c.tool for c in plan.tool_calls]
    tools = [c.tool for c in plan.tool_calls]
    assert "get_market_snapshot" in tools
    assert "search_financial_news" in tools
    assert plan.answer_mode.value == "INSIGHT_FUSION"


def test_jio_ipo_news_passes_guardrails_and_routes():
    q = "tell me news about jio ipo?"
    assert check_guardrails(q).outcome == "pass"
    plan = slot_route(q)
    assert plan is not None and plan.scope_kind.value == "in_scope"
    assert plan.answer_mode.value == "NEWS_ONLY"
    assert any(c.tool == "search_financial_news" for c in plan.tool_calls)


def test_non_financial_still_refused():
    result = check_guardrails("write me a python poem about cats")
    assert result.outcome == "refuse_out_of_domain"


def test_fund_question_still_passes():
    assert check_guardrails("what is the nav of hdfc top 100 fund").outcome == "pass"
