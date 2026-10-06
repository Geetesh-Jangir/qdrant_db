from news_rag.article_pool import collect_bundle_articles, sources_from_articles
from news_rag.ask_execution import ExecutionBundle
from news_rag.name_resolution import ResolvedNames


def test_collect_bundle_articles_from_market_pulse_tool_result():
    bundle = ExecutionBundle(names=ResolvedNames())
    bundle.tool_results["market_pulse:0"] = {
        "ok": True,
        "data": {
            "clusters": [
                {
                    "theme_key": "nifty",
                    "articles": [
                        {
                            "title": "Nifty falls on RBI fears",
                            "url": "https://example.com/a",
                            "max_impact": 4,
                            "published_at": "2026-10-01",
                        }
                    ],
                }
            ],
            "articles": [],
        },
    }
    arts = collect_bundle_articles(bundle)
    assert len(arts) == 1
    sources = sources_from_articles(arts)
    assert len(sources) == 1
    assert sources[0]["url"] == "https://example.com/a"


def test_sources_title_only_without_url():
    arts = [{"title": "Headline only piece", "max_impact": 2}]
    sources = sources_from_articles(arts)
    assert len(sources) == 1
    assert sources[0]["url"] is None
    assert sources[0]["title"] == "Headline only piece"
