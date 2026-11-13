"""Sector weights and holdings taken from the top-holdings payload."""

from news_rag.insight.book_news_map import (
    book_wide_sectors,
    news_calls_for_book,
    resolve_book_sector,
    sector_holdings,
)
from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
from news_rag.insight.planner_policy import align_planned_news_execution
from news_rag.insight.portfolio_intents import apply_portfolio_intent

RAW = {
    "sector_allocation": [
        {"sector": "Banks", "percentage": 12.26},
        {"sector": "Commercial Paper", "percentage": 9},
        {"sector": "Cash and Cash Equivalents", "percentage": 3.46},
        {"sector": "Finance", "percentage": 4.68},
    ],
    "top_holdings": [
        {"instrument_name": "Cash and Cash Equivalents", "percentage": 3.46, "fund_count": 14, "industry": "Cash and Cash Equivalents"},
        {"instrument_name": "HDFC Bank Ltd.£", "percentage": 3.35, "fund_count": 7, "industry": "Banks"},
        {"instrument_name": "ICICI Bank Ltd.", "percentage": 2.43, "fund_count": 4, "industry": "Banks"},
        {"instrument_name": "The Federal Bank Limited", "percentage": 1.15, "fund_count": 4, "industry": "Banks"},
        {"instrument_name": "Bajaj Finance Ltd.", "percentage": 1.05, "fund_count": 3, "industry": "Finance"},
        {"instrument_name": "Karur Vysya Bank Limited", "percentage": 1, "fund_count": 3, "industry": "Banks"},
        {"instrument_name": "State Bank of India", "percentage": 0.94, "fund_count": 4, "industry": "Banks"},
        {"instrument_name": "Axis Bank Ltd.", "percentage": 0.8, "fund_count": 3, "industry": "Banks"},
        {"instrument_name": "Kotak Mahindra Bank Ltd.", "percentage": 0.5, "fund_count": 2, "industry": "Banks"},
    ],
}


def test_banks_weight_and_top_holdings():
    resolved = resolve_book_sector("banking", RAW["sector_allocation"])
    assert resolved is None or resolved["sector"] == "Banks"
    exact = resolve_book_sector("Banks", RAW["sector_allocation"])
    assert exact == {"sector": "Banks", "weight_pct": 12.26}
    names = [row["name"] for row in sector_holdings(RAW, "Banks")]
    assert names[0] == "HDFC Bank Ltd"
    assert "hdfc bank" in names[0].lower() or sector_holdings(RAW, "Banks")[0]["news_name"] == "hdfc bank"
    assert len(names) == 7
    assert names[1].startswith("ICICI Bank")


def test_unknown_sector_is_empty_and_cash_is_not_a_news_sector():
    assert resolve_book_sector("underwater mining", RAW["sector_allocation"]) is None
    assert sector_holdings(RAW, "underwater mining") == []
    labels = [row["sector"] for row in book_wide_sectors(RAW)]
    assert labels[0] == "Banks"
    assert "Cash and Cash Equivalents" not in labels
    assert "Commercial Paper" not in labels


def test_sector_news_plan_stays_fusion():
    plan = ExecutionPlan(
        routed_by="planner",
        intent="overview",
        answer_mode=AnswerMode.INSIGHT_FUSION,
        portfolio_intent="sector_exposure",
        portfolio_scope="investor",
        portfolio_news_mode="sector",
        news_sector="Banks",
        window_days=7,
        tool_calls=[
            ToolCall(tool="get_investor_portfolio", arguments={"modules": ["concentration"]}, wave=1),
            ToolCall(
                tool="search_financial_news",
                arguments={"scope": "sector", "topics": ["Banks"], "top_n": 8, "window_days": 7},
                wave=2,
            ),
        ],
    )
    plan = apply_portfolio_intent(plan, "banking sector news that could affect my portfolio")
    plan = align_planned_news_execution(plan)
    assert plan.answer_mode == AnswerMode.INSIGHT_FUSION
    assert any(call.tool == "search_financial_news" for call in plan.tool_calls)
    topics = [call.arguments["topics"] for call in news_calls_for_book(plan, RAW)]
    assert ["Banks"] in topics
    assert ["hdfc bank"] in topics
