from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.investor_subject import (
    apply_investor_category_fund_to_plan,
    enforce_investor_holding_subject,
    ensure_catalog_tools_for_fund_news,
    ensure_my_category_fund_investor_plan,
    question_asks_whole_investor_portfolio,
    resolve_answer_subject,
    resolve_investor_holding_fund_name,
    resolve_investor_holding_from_holdings_rows,
)


def _memory_like_log():
    return {
        "holdings_in_chat": [
            {
                "name": "Kotak Contra Fund - Regular Plan - Growth",
                "isin": "INF174K01245",
                "category": "contra",
                "aum_inr": 12220.54,
                "xirr_pct": -10.71,
            },
        ],
        "list_cursor": {
            "rows": [
                {"name": "HSBC Value Fund - Regular Plan - Growth"},
                {"name": "Kotak Contra Fund - Regular Plan - Growth"},
            ],
        },
        "entity_stack": [{"name": "HSBC Value Fund - Regular Plan - Growth"}],
    }


def test_my_contra_fund_resolves_to_holding_not_screen():
    memory = _memory_like_log()
    name = resolve_investor_holding_fund_name("what news are affecting my contra fund", memory)
    assert name == "Kotak Contra Fund - Regular Plan - Growth"


def test_enforce_overwrites_wrong_catalog_fund():
    memory = _memory_like_log()
    plan = ExecutionPlan(
        funds=["HSBC Value Fund - Regular Plan - Growth"],
        subject_ref="memory_primary",
        tool_calls=[
            ToolCall(tool="search_financial_news", arguments={"scope": "all"}, wave=2),
        ],
    )
    enforce_investor_holding_subject(plan, memory, "what news are affecting my contra fund")
    assert plan.funds == ["Kotak Contra Fund - Regular Plan - Growth"]


def test_fund_news_adds_catalog_tools():
    plan = ExecutionPlan(
        funds=["Kotak Contra Fund - Regular Plan - Growth"],
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={"modules": ["holdings"]}, wave=1),
            ToolCall(tool="search_financial_news", arguments={"scope": "all"}, wave=2),
        ],
    )
    ensure_catalog_tools_for_fund_news(plan)
    tools = [c.tool for c in plan.tool_calls]
    assert tools.count("get_fund_data") >= 1
    assert tools.count("get_portfolio_data") >= 1


def test_deictic_risk_strips_planner_hallucination_uses_last_focus():
    from news_rag.insight.investor_subject import enforce_deictic_and_memory_primary_fund

    memory = {
        "frame": {
            "last_fund_focus": "Kotak Contra Fund - Regular Plan - Growth",
            "subjects": [],
        },
        "holdings_in_chat": [
            {"name": "Kotak Contra Fund - Regular Plan - Growth", "category": "contra"},
        ],
        "entity_stack": [],
    }
    plan = ExecutionPlan(
        funds=["Aditya Birla Sun Life Credit Risk Fund - Regular Plan - Growth"],
        subject_ref="memory_primary",
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["risk"]}, wave=1)],
    )
    enforce_deictic_and_memory_primary_fund(plan, memory, "do its risk analysis")
    assert plan.funds == ["Kotak Contra Fund - Regular Plan - Growth"]


def test_contra_nav_resolves_subject_from_wave1_holdings_not_first_row():
    holdings = [
        {
            "scheme_name": "Invesco India Large & Mid Cap Fund - Regular Plan - Growth",
            "scheme_category": "large & mid cap",
            "current_nav": 104.13,
        },
        {
            "scheme_name": "Kotak Contra Fund - Regular Plan - Growth",
            "scheme_category": "contra",
            "current_nav": 142.326,
        },
    ]
    plan = ExecutionPlan(funds=[])
    wave1 = [{"tool": "get_investor_portfolio", "ok": True, "data": {"holdings": holdings}}]
    apply_investor_category_fund_to_plan(
        plan,
        "whats the nav of my contra fund",
        {},
        wave1,
    )
    assert plan.funds == ["Kotak Contra Fund - Regular Plan - Growth"]
    subject = resolve_answer_subject(
        "whats the nav of my contra fund",
        plan,
        {},
        wave1_results=wave1,
    )
    assert subject == "Kotak Contra Fund - Regular Plan - Growth"
    assert (
        resolve_investor_holding_from_holdings_rows("whats the nav of my contra fund", holdings)
        == "Kotak Contra Fund - Regular Plan - Growth"
    )


def test_my_contra_nav_plan_uses_holdings_not_summary():
    plan = ExecutionPlan(
        data_need="investor_summary",
        tool_calls=[
            ToolCall(
                tool="get_investor_portfolio",
                arguments={"modules": ["summary"], "include_meta": True},
                wave=1,
            ),
        ],
    )
    ensure_my_category_fund_investor_plan(
        plan,
        "what is the nav of my contra fund and whats the full form of the nav",
        {},
    )
    assert plan.data_need == "investor_holding"
    assert plan.requires_compose is True
    inv = next(c for c in plan.tool_calls if c.tool == "get_investor_portfolio")
    assert "holdings" in (inv.arguments or {}).get("modules", [])
    assert (inv.arguments or {}).get("scheme_filter") == "contra"
    assert (inv.arguments or {}).get("holdings_fields") == "standard"


def test_deictic_uses_recent_fund_focus_not_planner_hallucination():
    from news_rag.insight.investor_subject import (
        enforce_deictic_and_memory_primary_fund,
        reconcile_deictic_planner_fund,
    )

    memory = {
        "frame": {
            "last_fund_focus": "Kotak Contra Fund - Regular Plan - Growth",
            "recent_fund_focus": ["Kotak Contra Fund - Regular Plan - Growth"],
            "subjects": [],
        },
        "holdings_in_chat": [
            {"name": "Kotak Contra Fund - Regular Plan - Growth", "category": "contra"},
        ],
    }
    plan = ExecutionPlan(
        funds=["Aditya Birla Sun Life Credit Risk Fund - Regular Plan - Growth"],
        subject_ref="user_named",
        planner_reading="Risk analysis of Aditya Birla Sun Life Credit Risk Fund - Regular Plan - Growth",
        tool_calls=[ToolCall(tool="get_fund_data", arguments={"modules": ["risk"]}, wave=1)],
    )
    reconcile_deictic_planner_fund(plan, memory, "do its risk analysis")
    enforce_deictic_and_memory_primary_fund(plan, memory, "do its risk analysis")
    assert plan.funds == ["Kotak Contra Fund - Regular Plan - Growth"]
    assert plan.subject_ref == "memory_primary"
    assert "Kotak Contra" in (plan.planner_reading or "")


def test_memory_primary_rejects_fund_not_in_session():
    from news_rag.insight.plan_enforce import resolve_planner_subject_refs

    memory = {
        "frame": {
            "last_fund_focus": "Kotak Contra Fund - Regular Plan - Growth",
            "subjects": [],
        },
        "holdings_in_chat": [
            {"name": "Kotak Contra Fund - Regular Plan - Growth", "category": "contra"},
        ],
    }
    plan = ExecutionPlan(
        funds=["Aditya Birla Sun Life Credit Risk Fund - Regular Plan - Growth"],
        subject_ref="memory_primary",
    )
    resolve_planner_subject_refs(plan, memory, "do its risk analysis")
    assert plan.funds == ["Kotak Contra Fund - Regular Plan - Growth"]


def test_whole_portfolio_question_has_no_answer_subject():
    holdings = [
        {
            "scheme_name": "Invesco India Large & Mid Cap Fund - Regular Plan - Growth",
            "scheme_category": "large & mid cap",
            "aum_inr": 26511.498,
        },
        {
            "scheme_name": "Kotak Contra Fund - Regular Plan - Growth",
            "scheme_category": "contra",
            "aum_inr": 12220.5373,
        },
    ]
    plan = ExecutionPlan(
        funds=[],
        intent="overview",
        portfolio_scope="investor",
        data_need="investor_summary",
    )
    wave1 = [{"tool": "get_investor_portfolio", "ok": True, "data": {"holdings": holdings}}]
    question = "can you tell me about my portfolio"
    assert question_asks_whole_investor_portfolio(question, plan)
    assert resolve_answer_subject(question, plan, {}, investor_holdings=holdings, wave1_results=wave1) == ""
