"""Planner tasks keep catalog facts and bind a category peer without reading the question."""

from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.task_exec import apply_task_layer, parse_task_list, render_task_answer


def test_managers_fact_restores_fund_data_after_holdings_only_plan():
    plan = ExecutionPlan(
        intent="lookup",
        data_need="investor_holding",
        portfolio_scope="investor",
        portfolio_intent="list_holdings",
        asked_facts=["managers"],
        tool_calls=[ToolCall(tool="get_investor_portfolio", arguments={"modules": ["holdings"]})],
    )
    apply_task_layer(plan, memory={})
    fund_calls = [c for c in plan.tool_calls if c.tool == "get_fund_data"]
    assert fund_calls
    assert "managers" in (fund_calls[0].arguments.get("modules") or [])
    assert plan.holding_scope == "all_holdings"
    assert plan.portfolio_intent == "none"
    assert plan.tasks[0]["subjects"][0]["kind"] == "all_holdings"


def test_compare_reading_adds_large_cap_peer_screen():
    plan = ExecutionPlan(
        intent="compare",
        funds=["Kotak Contra Fund - Regular Plan - Growth"],
        planner_reading="Compare Kotak Contra Fund with a large cap fund",
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"})],
    )
    memory = {"holdings_in_chat": [
        {"name": "Kotak Contra Fund - Regular Plan - Growth", "category": "contra"},
        {"name": "Invesco India Large & Mid Cap Fund", "category": "large & mid cap"},
    ]}
    apply_task_layer(plan, memory=memory)
    screens = [c for c in plan.tool_calls if c.tool == "screen_funds_by_exposure"]
    assert screens
    assert "large cap" in str(screens[0].arguments.get("focus_question") or "").lower()
    kinds = [s["kind"] for s in plan.tasks[0]["bound"]]
    assert "category_peer" in kinds


def test_held_category_binds_to_the_holding_not_a_peer():
    plan = ExecutionPlan(
        intent="compare",
        funds=["Quant Small Cap Fund - Growth"],
        compare_sides=[
            {"source": "my_holding", "name": "", "category": "small cap"},
            {"source": "my_holding", "name": "", "category": "contra"},
        ],
        tool_calls=[ToolCall(tool="compare_funds", arguments={"mode": "both"})],
    )
    memory = {"holdings_in_chat": [
        {"name": "Quant Small Cap Fund - Growth", "category": "small cap"},
        {"name": "Kotak Contra Fund - Regular Plan - Growth", "category": "contra"},
    ]}
    apply_task_layer(plan, memory=memory)
    assert not any(c.tool == "screen_funds_by_exposure" for c in plan.tool_calls)
    names = [s["value"] for s in plan.tasks[0]["bound"]]
    assert "Kotak Contra Fund - Regular Plan - Growth" in names


def test_nav_of_all_holdings_does_not_add_a_catalog_call():
    plan = ExecutionPlan(
        intent="lookup",
        data_need="investor_holding",
        portfolio_scope="investor",
        asked_facts=["nav"],
        tool_calls=[ToolCall(tool="get_investor_portfolio", arguments={"modules": ["holdings"]})],
    )
    apply_task_layer(plan, memory={})
    assert not any(c.tool == "get_fund_data" for c in plan.tool_calls)


def test_render_manager_table_and_marks_a_gap():
    plan = ExecutionPlan(
        tasks=parse_task_list([{
            "subjects": [{"kind": "all_holdings", "value": ""}],
            "facts": ["manager", "manager_experience"],
            "operation": "lookup",
        }]),
    )
    pack = {
        "investor_portfolio": {"holdings": [
            {"scheme_name": "Kotak Contra Fund"},
            {"scheme_name": "Quant Small Cap Fund"},
        ]},
        "fund:kotak": {
            "fund_name": "Kotak Contra Fund",
            "managers": {"current": [{"name": "A. Shah", "managing_since": "2019", "total_experience_years": 14}]},
        },
    }
    text = render_task_answer(plan, pack)
    assert "A. Shah" in text
    assert "14 years" in text
    assert "n/a" in text


def test_multi_part_tasks_render_two_sections():
    plan = ExecutionPlan(tasks=parse_task_list([
        {"subjects": [{"kind": "holding_by_name", "value": "Kotak Contra Fund"}], "facts": ["nav"], "operation": "lookup"},
        {"subjects": [{"kind": "holding_by_name", "value": "Kotak Contra Fund"}], "facts": ["manager"], "operation": "lookup"},
    ]))
    pack = {
        "investor_portfolio": {"holdings": [{"scheme_name": "Kotak Contra Fund", "current_nav": 154.32}]},
        "fund:kotak": {"fund_name": "Kotak Contra Fund", "managers": {"current": [{"name": "A. Shah"}]}},
    }
    text = render_task_answer(plan, pack)
    assert "154.32" in text
    assert "A. Shah" in text


def test_aum_without_a_named_fund_is_the_book_total():
    plan = ExecutionPlan(
        intent="lookup",
        asked_facts=["aum", "invested"],
        data_need="investor_summary",
        portfolio_scope="investor",
        tool_calls=[ToolCall(tool="get_investor_portfolio", arguments={"modules": ["summary"]})],
    )
    apply_task_layer(plan, memory={})
    assert plan.tasks[0].get("book_total") is True
    text = render_task_answer(plan, {"investor_portfolio": {
        "summary": {"aum_inr": 3973714, "invested_inr": 2551280},
        "holdings": [{"scheme_name": "Should Not Appear", "aum_inr": 1}],
    }})
    assert "3,973,714.00" in text
    assert "Should Not Appear" not in text


def test_compare_pair_screen_does_not_add_a_peer_screen():
    plan = ExecutionPlan(
        intent="compare",
        scheme_category="large cap",
        planner_reading="compare two large cap funds",
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"compare_pair": True, "focus_question": "large cap", "top_n": 2},
                wave=1,
            ),
            ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1),
        ],
    )
    apply_task_layer(plan, memory={})
    screens = [c for c in plan.tool_calls if c.tool == "screen_funds_by_exposure"]
    assert len(screens) == 1
    assert screens[0].arguments.get("compare_pair") is True


def test_random_compare_no_investor_portfolio_when_disabled(monkeypatch):
    monkeypatch.setattr(
        "news_rag.config.get_settings",
        lambda: type("S", (), {"portfolio_enabled": False})(),
    )
    memory = {
        "chat_turns": [
            {"user": "x", "assistant": "ITI Small Cap Fund - Regular Plan - Growth"},
        ],
    }
    plan = ExecutionPlan(
        intent="compare",
        asked_facts=["category", "expense", "returns", "risk"],
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"compare_pair": True, "random_sample": True},
                wave=1,
            ),
            ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1),
        ],
    )
    apply_task_layer(plan, memory=memory)
    assert not any(c.tool == "get_investor_portfolio" for c in plan.tool_calls)


def test_category_filter_does_not_bind_every_holding():
    plan = ExecutionPlan(
        intent="lookup",
        asked_facts=["aum"],
        portfolio_scope="investor",
        tool_calls=[ToolCall(
            tool="get_investor_portfolio",
            arguments={"modules": ["holdings"], "scheme_filter": "liquid"},
        )],
    )
    apply_task_layer(plan, memory={"holdings_in_chat": [
        {"name": "Nippon Liquid", "category": "liquid"},
        {"name": "HSBC Value", "category": "value"},
    ]})
    assert plan.tasks[0]["subjects"][0] == {"kind": "holding_by_category", "value": "liquid"}
    assert [row["value"] for row in plan.tasks[0]["bound"]] == ["Nippon Liquid"]


def test_unknown_fact_still_keeps_the_task():
    tasks = parse_task_list([{
        "subjects": [{"kind": "all_holdings", "value": ""}],
        "facts": ["not_a_real_fact"],
        "operation": "lookup",
    }])
    assert tasks
    assert tasks[0]["facts"][0]["name"] == "value"


def test_top_live_holdings_prefers_different_categories(monkeypatch):
    monkeypatch.setattr(
        "news_rag.portfolio.cache.peek_portfolio",
        lambda crn=None: {"holdings": [
            {"scheme_name": "Sold", "aum_inr": 0, "scheme_category": "liquid"},
            {"scheme_name": "Big", "aum_inr": 100, "scheme_category": "value"},
            {"scheme_name": "Same", "aum_inr": 90, "scheme_category": "value"},
            {"scheme_name": "Other", "aum_inr": 40, "scheme_category": "liquid"},
        ]},
    )
    from news_rag.insight.tool_runners import _top_live_holdings

    assert [row["scheme_name"] for row in _top_live_holdings(2)] == ["Big", "Other"]


def test_stock_reading_fetches_concentration():
    from news_rag.insight.portfolio_scope import _modules_for_investor_plan

    plan = ExecutionPlan(
        data_need="investor_hybrid",
        planner_reading="Which stocks the user holds most, and how much",
    )
    assert "concentration" in _modules_for_investor_plan(plan)
