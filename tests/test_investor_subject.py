from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.investor_subject import (
    apply_investor_category_fund_to_plan,
    enforce_investor_holding_subject,
    ensure_catalog_tools_for_fund_news,
    ensure_my_category_fund_investor_plan,
    fix_unasked_scheme_opening_heading,
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


def test_my_quant_fund_resolves_by_amc_token():
    memory = {
        "holdings_in_chat": [
            {"name": "Quant Small Cap Fund - Growth", "isin": "INF966L01AA0", "category": "small cap"},
            {"name": "Kotak Contra Fund - Regular Plan - Growth", "category": "contra"},
        ],
    }
    name = resolve_investor_holding_fund_name("whats the current nav of my quant fund", memory)
    assert name == "Quant Small Cap Fund - Growth"


def test_deictic_allocations_use_last_fund_focus_not_planner_pick():
    from news_rag.insight.investor_subject import enforce_deictic_and_memory_primary_fund

    memory = {
        "frame": {
            "last_fund_focus": "Quant Small Cap Fund - Growth",
            "subjects": [],
        },
        "holdings_in_chat": [
            {"name": "Quant Small Cap Fund - Growth", "category": "small cap"},
            {"name": "Kotak Contra Fund - Regular Plan - Growth", "category": "contra"},
        ],
        "entity_stack": [{"name": "Kotak Contra Fund - Regular Plan - Growth", "turn": 5}],
    }
    plan = ExecutionPlan(
        funds=["Kotak Contra Fund - Regular Plan - Growth"],
        subject_ref="memory_primary",
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["risk"]}, wave=1),
            ToolCall(tool="get_portfolio_data", arguments={"sections": ["sectors"]}, wave=1),
        ],
    )
    enforce_deictic_and_memory_primary_fund(plan, memory, "can i see the allocations of this fund")
    assert plan.funds == ["Quant Small Cap Fund - Growth"]


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


def test_category_money_share_keeps_full_book_allocation():
    plan = ExecutionPlan(
        data_need="investor_holding",
        funds=["Axis Large Cap Fund - Regular Plan - Growth"],
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
            ToolCall(
                tool="get_investor_portfolio",
                arguments={"modules": ["holdings"], "scheme_filter": "large cap"},
                wave=1,
            ),
        ],
    )
    ensure_my_category_fund_investor_plan(
        plan,
        "how much of my money is investd in large cap category",
        {},
    )
    inv = next(c for c in plan.tool_calls if c.tool == "get_investor_portfolio")
    assert "scheme_filter" not in (inv.arguments or {})
    assert "allocation" in (inv.arguments or {}).get("modules", [])
    assert all(c.tool != "get_fund_data" for c in plan.tool_calls)


def test_minimum_redemption_uses_hdfc_in_memory_not_planner_hallucination():
    from news_rag.insight.plan_enforce import apply_planner_post_hooks

    memory = {
        "turn": 1,
        "frame": {
            "subject_kind": "single_fund",
            "last_fund_focus": "HDFC Large Cap Fund - Growth",
            "recent_fund_focus": ["HDFC Large Cap Fund - Growth"],
            "subjects": [
                {"id": "INF179K01BE2", "name": "HDFC Large Cap Fund - Growth", "role": "primary"},
            ],
            "shown_facts": ["get_fund_data:limits:-", "limits"],
        },
        "entity_stack": [
            {
                "ref": 1,
                "name": "HDFC Large Cap Fund - Growth",
                "facts": ["get_fund_data:limits:-", "limits"],
            },
        ],
    }
    plan = ExecutionPlan(
        routed_by="planner",
        intent="lookup",
        subject_ref="user_named",
        funds=["ICICI Prudential Equity Minimum Variance Fund - Regular Plan - Growth"],
        planner_reading="Minimum redemption period for ICICI Prudential Equity Minimum Variance Fund",
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["limits"]}, wave=1),
        ],
    )
    out = apply_planner_post_hooks("whats the minimum redemption period", plan, memory)
    assert out.funds == ["HDFC Large Cap Fund - Growth"]
    assert out.subject_ref == "memory_primary"


def test_portfolio_health_check_does_not_crash_fund_name_match():
    from news_rag.insight.plan_enforce import apply_planner_post_hooks

    memory = {
        "holdings_in_chat": [
            {"name": "Invesco India Large & Mid Cap Fund - Regular Plan - Growth", "category": "large & mid cap"},
        ],
    }
    plan = ExecutionPlan(intent="overview", data_need="investor_hybrid", portfolio_scope="investor", window_days=365)
    out = apply_planner_post_hooks("give me a portfolio health check", plan, memory)
    assert out is plan


def test_user_explicitly_named_scheme_requires_amc_or_two_tokens():
    from news_rag.insight.investor_subject import user_explicitly_named_scheme

    assert not user_explicitly_named_scheme(
        "whats the minimum redemption period",
        "ICICI Prudential Equity Minimum Variance Fund - Regular Plan - Growth",
    )
    assert user_explicitly_named_scheme(
        "exit load on icici prudential minimum variance",
        "ICICI Prudential Equity Minimum Variance Fund - Regular Plan - Growth",
    )


def test_assets_in_portfolio_question_is_not_mirae_asset_fund():
    from news_rag.insight.investor_subject import user_explicitly_named_scheme

    q = (
        "for a ideal portfolio show should it look like and what categories "
        "and assets it should hold"
    )
    assert not user_explicitly_named_scheme(
        q,
        "Mirae Asset Nifty EV and New Age Automotive ETF",
    )


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


def test_fix_opening_heading_for_unasked_scheme_on_portfolio_overview():
    plan = ExecutionPlan(
        funds=[
            "Invesco India Large & Mid Cap Fund - Regular Plan - Growth",
            "Quant Small Cap Fund - Growth",
        ],
        intent="overview",
        holding_scope="all_holdings",
        portfolio_scope="both",
        data_need="investor_hybrid",
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={}, wave=1),
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
        ],
    )
    raw = (
        "## Invesco India Large & Mid Cap Fund - Regular Plan - Growth\n"
        "Your portfolio is worth **₹69,803**."
    )
    out = fix_unasked_scheme_opening_heading(raw, "Tell me about my portfolio", plan, {})
    assert out.startswith("## Your portfolio")
    assert "Invesco" not in out.splitlines()[0]


def test_portfolio_overview_with_holdings_catalog_fanout_is_whole_book():
    plan = ExecutionPlan(
        funds=[
            "Invesco India Large & Mid Cap Fund - Regular Plan - Growth",
            "Quant Small Cap Fund - Growth",
        ],
        intent="overview",
        holding_scope="all_holdings",
        portfolio_scope="both",
        data_need="investor_hybrid",
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={}, wave=1),
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
        ],
    )
    question = "Tell me about my portfolio"
    assert question_asks_whole_investor_portfolio(question, plan)
    assert resolve_answer_subject(question, plan, {}) == ""


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


def test_rs_rating_all_my_funds_is_not_whole_portfolio_overview():
    plan = ExecutionPlan(
        funds=["Fund A - Growth", "Fund B - Growth"],
        holding_scope="all_holdings",
        asked_facts=["rs_rating"],
        portfolio_scope="both",
        data_need="investor_holding",
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={}, wave=1),
            ToolCall(tool="get_fund_data", arguments={"modules": ["rating"]}, wave=1),
        ],
    )
    question = "show me the rs rating of all my funds"
    assert question_asks_whole_investor_portfolio(question, plan) is False


def test_deictic_one_month_uses_get_fund_data_not_investor_pnl():
    from news_rag.insight.plan_enforce import apply_planner_post_hooks

    memory = {
        "frame": {
            "last_fund_focus": "Quant Small Cap Fund - Growth",
            "subject_kind": "investor_portfolio",
            "subjects": [],
        },
        "holdings_in_chat": [
            {"name": "Quant Small Cap Fund - Growth", "isin": "INF966L01AA0", "category": "small cap"},
            {"name": "Invesco India Large & Mid Cap Fund - Regular Plan - Growth", "category": "large & mid cap"},
        ],
    }
    plan = ExecutionPlan(
        data_need="investor_pnl",
        subject_ref="memory_primary",
        window_days=30,
        window_label="last 1 month",
        tool_calls=[],
    )
    plan = apply_planner_post_hooks("whats the last one month changes in this fund", plan, memory)
    tools = [c.tool for c in plan.tool_calls]
    assert plan.funds == ["Quant Small Cap Fund - Growth"]
    assert "get_fund_data" in tools
    assert "get_investor_portfolio" not in tools
    gfd = next(c for c in plan.tool_calls if c.tool == "get_fund_data")
    assert gfd.arguments.get("windows") == ["1M"]
    assert "snapshot" in (gfd.arguments.get("modules") or [])


def test_deictic_return_without_memory_focus_does_not_title_largest_holding():
    holdings = [
        {"name": "Invesco India Large & Mid Cap Fund - Regular Plan - Growth", "category": "large & mid cap"},
        {"name": "Quant Small Cap Fund - Growth", "category": "small cap"},
    ]
    plan = ExecutionPlan(funds=[], subject_ref="memory_primary")
    subject = resolve_answer_subject(
        "whats the last one month changes in this fund",
        plan,
        {"frame": {"last_fund_focus": ""}, "holdings_in_chat": holdings},
        investor_holdings=[{"scheme_name": row["name"]} for row in holdings],
    )
    assert subject == ""


def test_memory_primary_yields_explicit_hdfc_when_user_names_it_not_list_cursor():
    from news_rag.insight.plan_enforce import apply_planner_post_hooks

    memory = {
        "frame": {
            "last_fund_focus": "Nippon India ETF Nifty 50 Shariah BeES",
            "subjects": [{"name": "Nippon India ETF Nifty 50 Shariah BeES"}],
        },
        "entity_stack": [
            {"name": "Nippon India ETF Nifty 50 Shariah BeES"},
            {"name": "HDFC Large Cap Fund - Growth"},
        ],
        "category_funds_in_chat": [{"category": "large cap", "fund_names": ["HDFC Large Cap Fund - Growth"]}],
        "list_cursor": {"rows": [{"n": 1, "name": "Nippon India ETF Nifty 50 Shariah BeES"}]},
    }
    question = (
        "if we see the hdfc large cap performance of 1 year against its category avg "
        "then its not performing good, so is it a bad fund and should i sell it"
    )
    plan = ExecutionPlan(
        funds=[],
        subject_ref="memory_primary",
        routed_by="planner",
        data_need="category_performance",
        planner_reading="1 year return of HDFC Large Cap versus its category average",
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={
                    "modules": ["snapshot", "vs_benchmark", "rating"],
                    "windows": ["1Y"],
                    "include_category": True,
                },
                wave=1,
            )
        ],
    )
    plan = apply_planner_post_hooks(question, plan, memory)
    assert plan.funds == ["HDFC Large Cap Fund - Growth"]


def test_is_it_a_bad_fund_is_not_deictic_fund_pronoun():
    from news_rag.insight.investor_subject import question_refers_deictic_fund

    q = "is it a bad fund and should i sell it"
    assert not question_refers_deictic_fund(q)
    assert question_refers_deictic_fund("do its risk analysis")


def test_it_sector_fund_list_does_not_bind_prior_chat_fund():
    from news_rag.insight.investor_subject import (
        enforce_catalog_fund_list_scope,
        ensure_deictic_fund_period_return_plan,
        question_asks_catalog_fund_list,
    )

    q = "can you tell me some IT focused funds and their one month returns"
    memory = {
        "frame": {"last_fund_focus": "Kotak Services Fund - Regular Plan - Growth"},
        "entity_stack": [{"name": "Kotak Services Fund - Regular Plan - Growth"}],
    }
    plan = ExecutionPlan(
        intent="rank",
        funds=["Kotak Services Fund - Regular Plan - Growth"],
        subject_ref="memory_primary",
        window_days=30,
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1M"], "window_days": 30},
                wave=1,
            ),
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"sector": "Technology", "top_n": 5, "return_window": "1M"},
                wave=1,
            ),
        ],
    )
    assert question_asks_catalog_fund_list(q, plan)
    plan = ensure_deictic_fund_period_return_plan(plan, memory, q)
    plan = enforce_catalog_fund_list_scope(plan, memory, q)
    assert plan.funds == []
    assert plan.subject_ref == "none"
    assert all(c.tool != "get_fund_data" for c in plan.tool_calls)
    assert resolve_answer_subject(q, plan, memory) == ""
