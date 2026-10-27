from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall
from news_rag.insight.evidence_pack import build_evidence_pack
from news_rag.insight.fund_display import (
    clean_news_insight,
    is_article_only_news,
    news_insight_articles,
    strip_publisher,
)


def test_news_about_hdfc_bank_is_not_a_market_pulse():
    from news_rag.insight.capabilities.executor import _news_search_targets, _news_subject

    question = "what is the news about hdfc bank in the market?"
    assert _news_subject(question) == "hdfc bank"
    assert _news_subject("what is the news about the market?") == ""
    targets = _news_search_targets(
        ["hdfc bank"],
        scope="market",
        top_n=8,
        window_days=7,
        direction=None,
    )
    assert len(targets) == 1
    assert "hdfc bank" in targets[0].query.lower()


def test_news_insight_drops_publisher_clips_and_unrelated_articles():
    title = strip_publisher(
        "HDFC Bank PAT ticks up 5% amid pressure - The Economic Times"
    )
    assert title == "HDFC Bank PAT ticks up 5% amid pressure"
    assert "BusinessLine" not in strip_publisher(
        "HDFC Bank shares near ₹728 ahead of Q2 results; Sell orders at 77% - BusinessLine"
    )

    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.NEWS_ONLY,
        tool_calls=[ToolCall(tool="search_financial_news", arguments={"scope": "market"}, wave=1)],
    )
    pack = build_evidence_pack(
        plan,
        [
            {
                "tool": "search_financial_news",
                "ok": True,
                "scope": "market",
                "data": {
                    "grouped": {
                        "market": {
                            "hdfc bank": [
                                {
                                    "title": "HDFC Bank PAT ticks up 5% amid pressure - The Economic Times",
                                    "summary": (
                                        "Net profit rose 4.7% to ₹19,510 crore. "
                                        "Net interest margin hit a record low of 3.16%, and treasury income plu..."
                                    ),
                                    "published_at": "2026-10-18T04:38:20Z",
                                },
                                {
                                    "title": "New indicator for New India - The Economic Times",
                                    "summary": "Economists waited for GDP. This story is not about the bank.",
                                    "published_at": "2026-09-28T00:00:00Z",
                                },
                            ]
                        }
                    }
                },
            }
        ],
        [],
        question="what is the news about hdfc bank in the market?",
    )
    assert is_article_only_news(plan, pack)
    rows = news_insight_articles("what is the news about hdfc bank in the market?", pack.news_grouped)
    assert len(rows) == 1
    assert "4.7%" in rows[0]["what_happened"]
    assert "plu" not in rows[0]["what_happened"]
    assert "..." not in rows[0]["what_happened"]
    assert "Economic Times" not in rows[0]["what_happened"]
    cleaned = clean_news_insight(
        "Profit rose while margins tightened.\n\n- Shares slipped - BusinessLine\n- A clipped line that ends..."
    )
    assert "BusinessLine" not in cleaned
    assert "..." not in cleaned


def test_news_plus_a_market_snapshot_stays_with_the_composer():
    plan = ExecutionPlan(
        intent="lookup",
        answer_mode=AnswerMode.NEWS_ONLY,
        tool_calls=[
            ToolCall(tool="get_market_snapshot", arguments={}, wave=1),
            ToolCall(tool="search_financial_news", arguments={"scope": "market"}, wave=1),
        ],
    )
    pack = build_evidence_pack(
        plan,
        [
            {"tool": "get_market_snapshot", "ok": True, "data": {"nifty": {"change_pct": -1.2}}},
            {
                "tool": "search_financial_news",
                "ok": True,
                "data": {
                    "grouped": {
                        "market": {
                            "Nifty": [{"title": "Nifty falls", "summary": "The index fell."}]
                        }
                    }
                },
            },
        ],
        [],
    )
    assert is_article_only_news(plan, pack) is False
