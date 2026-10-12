from types import SimpleNamespace

from news_rag.article_pool import collect_bundle_articles, sources_from_articles


def test_collect_bundle_articles_from_tool_results():
    bundle = SimpleNamespace(
        articles_by_focus={},
        articles_by_layer={},
        tool_results={
            "market_pulse": {
                "ok": True,
                "data": {
                    "articles": [{"title": "RBI holds rates", "url": "https://example.com/a"}],
                },
            }
        },
    )
    arts = collect_bundle_articles(bundle)
    assert len(arts) == 1
    src = sources_from_articles(arts)
    assert src[0]["url"] == "https://example.com/a"
