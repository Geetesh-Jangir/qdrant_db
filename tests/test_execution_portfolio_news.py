from __future__ import annotations

from unittest.mock import patch

from news_rag.execution import execute_sub_query, build_fund_context
from news_rag.macro_plans import try_fund_insights_plan
from news_rag.query_plan import DataNeed, SubQuery


def test_q3_executes_fund_portfolio_news() -> None:
    plan = try_fund_insights_plan(
        "I have invested in the HDFC large cap fund, what insights do you have for me for this fund?"
    )
    assert plan is not None
    q = "I have invested in the HDFC large cap fund, what insights do you have for me for this fund?"
    ctx = build_fund_context(plan, q)
    sq3 = plan.sub_queries[2]
    fake_article = {
        "url": "https://example.com/a",
        "title": "ICICI Bank sees loan growth",
        "snippet": "ICICI Bank Limited reported steady loan growth in the quarter.",
        "_news_layer": "holding",
        "_news_source_label": "ICICI Bank Ltd.",
    }
    with patch("news_rag.execution.run_fund_portfolio_news") as mock_news:
        mock_news.return_value = {
            "ok": True,
            "data": {"articles": [fake_article]},
            "error": "",
            "elapsed_ms": 1.0,
        }
        run = execute_sub_query(sq3, ctx, q)
    assert "fund_portfolio_news" in run.tool_results
    assert mock_news.called
    arts = (run.tool_results["fund_portfolio_news"].get("data") or {}).get("articles") or []
    assert len(arts) == 1
