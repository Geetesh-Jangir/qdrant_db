from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall, Wave2Policy
from news_rag.insight.evidence_pack import sector_focus_from_market
from news_rag.insight.fund_display import strip_news_roundup
from news_rag.insight.planner_policy import finalize_planner_plan
from news_rag.tools import asks_sector_overview


def test_banking_sector_question_is_an_overview_not_a_fund_list():
    q = "tell me about banking sector and its sector?"
    assert asks_sector_overview(q) is True
    assert asks_sector_overview("compare two random banking funds and also tell me their aum") is False


def test_sector_overview_keeps_market_and_news_and_drops_the_fund_screen():
    q = "tell me about banking sector and its sector?"
    plan = ExecutionPlan(
        routed_by="planner",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        intent="overview",
        tool_calls=[
            ToolCall(
                tool="get_market_snapshot",
                arguments={"modules": ["index_return", "sector_ranking"], "index": "nifty50"},
                wave=1,
            ),
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"sector": "Banking & Financial Services", "top_n": 5},
                wave=1,
            ),
            ToolCall(
                tool="search_financial_news",
                arguments={"scope": "sectors", "topics": ["banking"], "top_n": 8},
                wave=2,
            ),
        ],
        wave_2_policy=Wave2Policy(trigger="always", max_calls=1),
    )
    out = finalize_planner_plan(q, plan)
    assert out.tool_names == ["get_market_snapshot", "search_financial_news"]
    assert out.funds == []
    assert "sector_focus" in out.presentation_notes
    assert "examples" in out.presentation_notes


def test_sector_focus_states_the_gap_versus_the_index():
    market = {
        "index_return": {"return_pct": -1.85, "horizon": "1M"},
        "sector_ranking": {
            "horizon": "1M",
            "leaders": [{"sector": "Banks", "return_pct": -2.89}],
            "laggards": [],
        },
    }
    focus = sector_focus_from_market(market, "tell me about banking sector and its sector?")
    assert focus is not None
    assert focus["sector"] == "Banks"
    assert focus["gap_vs_index_pct"] == -1.04


def test_examples_heading_is_removed():
    prose = (
        "Banks fell 2.89% (1M).\n\n"
        "### How the sector is held (examples only)\n\n"
        "These are examples.\n\n"
        "### Summary\n\n"
        "Banks lagged the index."
    )
    cleaned = strip_news_roundup(prose)
    assert "examples" not in cleaned.lower()
    assert "Banks lagged the index." in cleaned
