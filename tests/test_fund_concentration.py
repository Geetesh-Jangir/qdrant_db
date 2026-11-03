from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
from news_rag.insight.evidence_pack import build_evidence_pack, render_fund_concentration_answer
from news_rag.insight.fund_concentration import ensure_fund_concentration_plan
from news_rag.insight.plan_enforce import apply_planner_post_hooks


def test_ensure_fund_concentration_adds_composition_and_top_n():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="lookup",
        data_need="fund_holdings_breakdown",
        subject_ref="memory_primary",
        funds=["HDFC Large Cap Fund - Growth"],
        planner_count=10,
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["risk", "snapshot"]}, wave=1),
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": ["holdings", "sectors"], "top_n": 5},
                wave=1,
            ),
        ],
    )
    out = ensure_fund_concentration_plan("show me the concentration in this fund", plan)
    gfd = next(c for c in out.tool_calls if c.tool == "get_fund_data")
    assert "composition" in gfd.arguments["modules"]
    port = next(c for c in out.tool_calls if c.tool == "get_portfolio_data")
    assert port.arguments["top_n"] >= 10
    assert out.requires_compose is False


def test_render_fund_concentration_from_portfolio_data():
    plan = ExecutionPlan(
        funds=["HDFC Large Cap Fund - Growth"],
        data_need="fund_holdings_breakdown",
        answer_mode=AnswerMode.DATA_ONLY,
    )
    wave1 = [
        {
            "tool": "get_portfolio_data",
            "ok": True,
            "fund": "HDFC Large Cap Fund - Growth",
            "data": {
                "fund_name": "HDFC Large Cap Fund - Growth",
                "holdings": [
                    {"name": "ICICI Bank Ltd.", "weight_pct": 9.79, "sector": "Banks"},
                    {"name": "HDFC Bank Ltd.", "weight_pct": 7.36, "sector": "Banks"},
                ],
                "sectors": [
                    {"sector": "Banks", "weight_pct": 30.08},
                    {"sector": "Telecom - Services", "weight_pct": 6.46},
                ],
            },
        },
        {
            "tool": "get_fund_data",
            "ok": True,
            "fund": "HDFC Large Cap Fund - Growth",
            "data": {
                "composition": {
                    "top_5_pct": 34.76,
                    "top_10_pct": 52.1,
                    "holding_count": 42,
                },
                "risk": {
                    "market_cap": [
                        {"label": "Large Cap", "percentage": 82.91},
                        {"label": "Mid Cap", "percentage": 14.6},
                    ]
                },
            },
        },
    ]
    pack = build_evidence_pack(plan, wave1, [], question="show me the concentration in this fund")
    text = render_fund_concentration_answer(
        pack, plan, "show me the concentration in this fund"
    )
    assert text
    assert "30.08" in text
    assert "ICICI Bank" in text
    assert "34.76" in text
    assert "42" in text
    assert "Returns" not in text


def test_apply_hooks_for_concentration_followup():
    memory = {
        "frame": {
            "last_fund_focus": "HDFC Large Cap Fund - Growth",
            "subjects": [{"name": "HDFC Large Cap Fund - Growth"}],
        },
    }
    plan = ExecutionPlan(
        routed_by="planner",
        intent="lookup",
        data_need="fund_holdings_breakdown",
        subject_ref="memory_primary",
        funds=["HDFC Large Cap Fund - Growth"],
        tool_calls=[
            ToolCall(tool="get_fund_data", arguments={"modules": ["risk", "snapshot"]}, wave=1),
            ToolCall(
                tool="get_portfolio_data",
                arguments={"sections": ["holdings", "sectors"], "top_n": 5},
                wave=1,
            ),
        ],
    )
    out = apply_planner_post_hooks("show me the concentration in this fund", plan, memory)
    gfd = next(c for c in out.tool_calls if c.tool == "get_fund_data")
    assert "composition" in gfd.arguments["modules"]
