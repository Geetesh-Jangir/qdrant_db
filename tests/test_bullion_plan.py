from news_rag.insight.brief import (
    question_is_bullion_metal_price_question,
    question_mentions_gold_etf_or_fund,
)
from news_rag.insight.bullion_plan import apply_bullion_metal_scope
from news_rag.insight.contracts import ExecutionPlan, ToolCall


def test_bullion_vs_gold_etf_detection():
    q = "tell me about gold is its price decreasing or increasing"
    assert question_is_bullion_metal_price_question(q)
    assert not question_mentions_gold_etf_or_fund(q)
    assert question_is_bullion_metal_price_question("is gold going up or down")
    assert not question_is_bullion_metal_price_question("how is nippon india gold etf performing")
    assert not question_is_bullion_metal_price_question("returns on my gold mutual fund")


def test_bullion_plan_clears_memory_gold_etf():
    plan = ExecutionPlan(
        funds=["Angel One Gold ETF"],
        subject_ref="memory_primary",
        tool_calls=[
            ToolCall(
                tool="get_fund_data",
                arguments={"modules": ["snapshot"], "windows": ["1M"]},
                wave=1,
            ),
            ToolCall(
                tool="get_market_snapshot",
                arguments={"modules": ["metals_spot"], "metal": "gold", "windows": ["1W", "1M"]},
                wave=1,
            ),
            ToolCall(
                tool="search_financial_news",
                arguments={"scope": "sectors", "topics": ["Gold"], "top_n": 8},
                wave=2,
            ),
        ],
    )
    out = apply_bullion_metal_scope(
        "tell me about gold is its price decreasing or increasing",
        plan,
    )
    assert out.funds == []
    assert out.subject_ref == "none"
    assert not any(c.tool == "get_fund_data" for c in out.tool_calls)
    assert any(
        c.tool == "get_market_snapshot" and "metals_spot" in (c.arguments or {}).get("modules", [])
        for c in out.tool_calls
    )
