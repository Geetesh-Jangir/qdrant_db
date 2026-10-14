from types import SimpleNamespace

from news_rag.insight.article_quality import filter_quality_articles, relevance_terms
from news_rag.insight.brief import QuestionBrief


def test_quality_filter_prefers_relevant_readable_articles():
    brief = QuestionBrief(goal="Why is the fund down?", funds=["Example Banking Fund"])
    evidence = SimpleNamespace(
        items=[
            SimpleNamespace(
                facet="fund_composition",
                data={
                    "holdings": [{"name": "HDFC Bank Ltd", "percentage": 8.0}],
                    "sectors": [{"sector": "Banks", "percentage": 22.0}],
                },
            )
        ],
        articles=[],
    )
    terms = relevance_terms(brief, evidence)
    assert "hdfc" in terms or "bank" in terms

    articles = [
        {"title": "Short fluff", "max_impact": 4, "snippet": "stars"},
        {
            "title": "Bank credit growth led by industry loans",
            "max_impact": 3,
            "body": (
                "Bank credit growth accelerated to 19.3 per cent year-on-year with industry loans rising. "
                "Lenders including HDFC Bank reported stronger loan books."
            ),
        },
    ]
    out = filter_quality_articles(
        articles, brief=brief, evidence=evidence, limit=5, char_limit=2000
    )
    titles = [a["title"] for a in out]
    assert titles and "credit" in titles[0].lower()
