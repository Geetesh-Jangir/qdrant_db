from news_rag.insight.contracts import ExecutionPlan, ToolCall
from news_rag.insight.plan_catalog_bind import enforce_planner_catalog_plan, planner_requested_catalog
from news_rag.insight.plan_enforce import apply_planner_post_hooks
from news_rag.insight.portfolio_scope import strip_spurious_catalog_for_investor_book


def _book():
    return {
        "frame": {"investor_subjects": []},
        "holdings_in_chat": [
            {"name": "Invesco India Large & Mid Cap Fund - Regular Plan - Growth", "isin": "INF205K01247"},
            {"name": "Quant Small Cap Fund - Growth", "isin": "INF966L01AA0"},
        ],
    }


def test_strip_keeps_planner_get_portfolio_data():
    plan = ExecutionPlan(
        data_need="investor_holding",
        portfolio_scope="investor",
        intent="rank",
        planner_portfolio_slice="sectors",
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={"modules": ["holdings"]}, wave=1),
            ToolCall(tool="get_portfolio_data", arguments={"sections": ["sectors"]}, wave=1),
        ],
    )
    kept = strip_spurious_catalog_for_investor_book(plan, _book(), "")
    tools = [c.tool for c in kept.tool_calls]
    assert "get_portfolio_data" in tools


def test_single_fund_nav_skips_catalog_get_fund_data():
    plan = ExecutionPlan(
        holding_scope="single",
        portfolio_scope="investor",
        portfolio_intent="nav_of_scheme",
        funds=["Quant Small Cap Fund - Growth"],
        asked_fields=["nav"],
        data_need="investor_holding",
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={"modules": ["holdings"]}, wave=1),
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"], "windows": ["1Y"]}, wave=1),
        ],
    )
    plan = enforce_planner_catalog_plan(plan, _book(), "What's the NAV of my quant fund?")
    assert not any(c.tool == "get_fund_data" for c in plan.tool_calls)


def test_all_holdings_binds_funds_and_get_fund_data():
    plan = ExecutionPlan(
        holding_scope="all_holdings",
        portfolio_scope="both",
        window_days=1,
        window_label="1 day",
        tool_calls=[ToolCall(tool="get_investor_portfolio", arguments={"modules": ["holdings"]}, wave=1)],
    )
    plan = enforce_planner_catalog_plan(plan, _book())
    assert len(plan.funds) == 2
    gfd = next(c for c in plan.tool_calls if c.tool == "get_fund_data")
    assert gfd.arguments["windows"] == ["1D"]


def test_planner_entities_funds_validated_against_memory():
    plan = ExecutionPlan(
        funds=["Invesco India Large & Mid Cap Fund - Regular Plan - Growth"],
        portfolio_scope="both",
        window_days=30,
        tool_calls=[],
    )
    plan = enforce_planner_catalog_plan(plan, _book())
    assert "get_fund_data" in [c.tool for c in plan.tool_calls]


def test_all_holdings_not_collapsed_by_single_entity():
    book = _book()
    plan = ExecutionPlan(
        holding_scope="all_holdings",
        funds=["Invesco India Large & Mid Cap Fund - Regular Plan - Growth"],
        portfolio_scope="both",
        window_days=30,
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1M"]},
                wave=1,
            )
        ],
    )
    plan = enforce_planner_catalog_plan(plan, book)
    assert len(plan.funds) == 2


def test_all_holdings_clears_hallucinated_fund_when_memory_empty():
    plan = ExecutionPlan(
        holding_scope="all_holdings",
        funds=["Angel One Nifty Total Market Index Fund - Regular Plan - Growth"],
        portfolio_scope="both",
        data_need="investor_holding",
        window_days=30,
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={"modules": ["holdings"]}, wave=1),
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1M"]},
                wave=1,
            ),
        ],
    )
    plan = enforce_planner_catalog_plan(plan, None)
    assert plan.funds == []
    assert "get_portfolio_data" not in [c.tool for c in plan.tool_calls]


def test_all_holdings_return_only_no_auto_portfolio_sectors():
    plan = ExecutionPlan(
        holding_scope="all_holdings",
        portfolio_scope="both",
        window_days=30,
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={"modules": ["holdings"]}, wave=1),
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1M"]},
                wave=1,
            ),
        ],
    )
    plan = enforce_planner_catalog_plan(plan, _book())
    assert "get_portfolio_data" not in [c.tool for c in plan.tool_calls]


def test_investor_summary_strips_catalog_fanout():
    plan = ExecutionPlan(
        holding_scope="all_holdings",
        data_need="investor_summary",
        portfolio_scope="both",
        window_days=30,
        tool_calls=[
            ToolCall(
                tool="get_investor_portfolio",
                arguments={"modules": ["allocation", "summary"]},
                wave=1,
            ),
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1M"]},
                wave=1,
            ),
        ],
    )
    plan = enforce_planner_catalog_plan(plan, _book(), "show me my portfolio allocation")
    tools = [c.tool for c in plan.tool_calls]
    assert "get_fund_data" not in tools
    assert "get_investor_portfolio" in tools


def test_concentration_strips_fund_snapshot_fanout():
    plan = ExecutionPlan(
        holding_scope="all_holdings",
        data_need="investor_hybrid",
        portfolio_scope="both",
        window_days=30,
        planner_reading="Concentration in the user's own mutual fund book",
        tool_calls=[
            ToolCall(
                tool="get_investor_portfolio",
                arguments={"modules": ["summary", "allocation", "concentration"]},
                wave=1,
            ),
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1M"]},
                wave=1,
            ),
        ],
    )
    plan = enforce_planner_catalog_plan(plan, _book(), "show me the concentration in my portfolio")
    assert [c.tool for c in plan.tool_calls] == ["get_investor_portfolio"]


def test_plan_needs_investor_before_catalog_when_no_memory():
    from news_rag.insight.plan_catalog_bind import plan_needs_investor_before_catalog

    plan = ExecutionPlan(
        holding_scope="all_holdings",
        portfolio_scope="both",
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={"modules": ["holdings"]}, wave=1),
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1M"]},
                wave=1,
            ),
        ],
    )
    assert plan_needs_investor_before_catalog(plan, None) is True
    assert plan_needs_investor_before_catalog(plan, _book()) is False


def test_sector_table_shows_zero_when_missing():
    from news_rag.insight.sector_exposure_tables import render_all_holdings_sector_table

    plan = ExecutionPlan(
        holding_scope="all_holdings",
        funds=["Fund A", "Fund B"],
        sectors=["banks"],
        planner_portfolio_slice="sectors",
    )
    results = [
        {
            "ok": True,
            "tool": "get_portfolio_data",
            "fund": "Fund A",
            "data": {"sectors": [{"sector": "Banks", "percentage": 12.5}]},
        },
        {"ok": True, "tool": "get_portfolio_data", "fund": "Fund B", "data": {"sectors": [{"sector": "IT", "percentage": 20}]}},
    ]
    table = render_all_holdings_sector_table(plan, results, None)
    assert "Fund A" in table
    assert "12.50%" in table
    assert "0%" in table


def test_my_all_funds_binds_every_holding_without_planner_scope():
    book = _book()
    book["holdings_in_chat"].append(
        {"name": "Kotak Contra Fund - Regular Plan - Growth", "isin": "INF174K01245"}
    )
    plan = ExecutionPlan(
        funds=["Invesco India Large & Mid Cap Fund - Regular Plan - Growth"],
        portfolio_scope="both",
        window_days=30,
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1M"]},
                wave=1,
            )
        ],
    )
    from news_rag.insight.plan_enforce import apply_planner_post_hooks

    plan = apply_planner_post_hooks(
        "what are the month returns of my all funds",
        plan,
        book,
    )
    assert plan.holding_scope == "all_holdings"
    assert len(plan.funds) == 3


def test_slots_from_plan_not_question():
    from news_rag.insight.fact_slots import slots_from_plan

    plan = ExecutionPlan(
        asked_facts=["returns"],
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1D"]},
                wave=1,
            )
        ],
    )
    assert "return:1D" in slots_from_plan(plan)


def test_compare_this_with_portfolio_large_cap_fetches_holding():
    plan = ExecutionPlan(
        intent="compare",
        subject_ref="memory_primary",
        funds=["Bandhan Large Cap Fund - Regular Plan - Growth"],
        compare_sides=[
            {"source": "chat_memory", "name": "Bandhan Large Cap Fund - Regular Plan - Growth"},
            {"source": "my_holding", "category": "large cap"},
        ],
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["snapshot"]}, wave=1),
            ToolCall(tool="compare_funds", arguments={"mode": "both"}, wave=1),
        ],
    )
    memory = {
        "frame": {
            "subjects": [{"name": "Bandhan Large Cap Fund - Regular Plan - Growth", "role": "primary"}],
            "last_fund_focus": "Bandhan Large Cap Fund - Regular Plan - Growth",
        }
    }
    plan = apply_planner_post_hooks(
        "compare this with the large cap that is in my portfolio",
        plan,
        memory,
    )
    tools = [c.tool for c in plan.tool_calls]
    assert tools[0] == "get_investor_portfolio"
    assert "compare_funds" in tools
    assert "get_fund_data" not in tools
    assert plan.tool_calls[0].arguments.get("scheme_filter") == "large cap"
    assert plan.funds == ["Bandhan Large Cap Fund - Regular Plan - Growth"]
