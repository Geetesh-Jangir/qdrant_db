import news_rag.macro_news_cache as cache
from news_rag.macro_news_cache import TTL_SECONDS, get_macro_news


def _digest(label: str) -> dict:
    return {
        "windows": {
            "7": {
                "window_days": 7,
                "label": "7 days",
                "clusters": [{"label": label, "article_count": 4, "articles": []}],
            },
            "30": {
                "window_days": 30,
                "label": "1 month",
                "clusters": [{"label": label, "article_count": 9, "articles": []}],
            },
        }
    }


def test_macro_news_is_reused_for_two_hours_then_overwritten(tmp_path, monkeypatch):
    path = tmp_path / "macro_news_cache.json"
    monkeypatch.setattr(cache, "_MEMORY", {})
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return _digest(f"pass-{calls['n']}")

    first = get_macro_news(now=1_000.0, path=path, fetch=fetch)
    second = get_macro_news(now=1_000.0 + TTL_SECONDS - 1, path=path, fetch=fetch)
    third = get_macro_news(now=1_000.0 + TTL_SECONDS, path=path, fetch=fetch)

    assert calls["n"] == 2
    assert first["cache_hit"] is False
    assert second["cache_hit"] is True
    assert second["windows"]["7"]["clusters"][0]["label"] == "pass-1"
    assert third["cache_hit"] is False
    assert third["windows"]["30"]["clusters"][0]["label"] == "pass-2"
    assert set(third["windows"]) == {"7", "30"}


def test_failed_refresh_keeps_the_previous_cache(tmp_path, monkeypatch):
    path = tmp_path / "macro_news_cache.json"
    monkeypatch.setattr(cache, "_MEMORY", {})
    get_macro_news(now=1_000.0, path=path, fetch=lambda: _digest("kept"))

    def boom():
        raise RuntimeError("qdrant down")

    again = get_macro_news(now=1_000.0 + TTL_SECONDS + 5, path=path, fetch=boom)
    assert again["stale"] is True
    assert again["windows"]["7"]["clusters"][0]["label"] == "kept"


def test_cache_keeps_the_article_body_not_only_the_title():
    slim = cache._slim_clusters(
        [
            {
                "label": "Banks",
                "article_count": 4,
                "articles": [
                    {
                        "title": "RBI raises CRR",
                        "scraped_text": (
                            "The Reserve Bank raised the daily CRR maintenance to 99 percent "
                            "from 90 percent, tightening liquidity for banks."
                        ),
                    }
                ],
            }
        ]
    )
    text = slim[0]["articles"][0]["summary"]
    assert "99 percent" in text
    assert "tightening liquidity" in text


def test_title_only_cache_is_rebuilt(tmp_path, monkeypatch):
    path = tmp_path / "macro_news_cache.json"
    monkeypatch.setattr(cache, "_MEMORY", {})
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        if calls["n"] == 1:
            stored = _digest("old")
            headline = [{"title": "Only a headline", "summary": ""}]
            stored["windows"]["7"]["clusters"][0]["articles"] = headline
            stored["windows"]["30"]["clusters"][0]["articles"] = headline
            return stored
        stored = _digest("new")
        body = [{"title": "RBI liquidity", "summary": "The Reserve Bank tightened liquidity for banks."}]
        stored["windows"]["7"]["clusters"][0]["articles"] = body
        stored["windows"]["30"]["clusters"][0]["articles"] = body
        return stored

    get_macro_news(now=1_000.0, path=path, fetch=fetch)
    again = get_macro_news(now=1_001.0, path=path, fetch=fetch)
    assert calls["n"] == 2
    assert "tightened liquidity" in again["windows"]["7"]["clusters"][0]["articles"][0]["summary"]


def test_cache_searches_named_macro_parameters(monkeypatch):
    def fake_search(specs, window_days):
        names = [name for name, _query in specs]
        assert "Macro - Crude Oil" in names
        assert "Macro - RBI Repo Rate" in names
        assert window_days in (7, 30)
        return [
            {
                "label": "Macro - Crude Oil",
                "query": "Crude oil Brent prices India fuel",
                "article_count": 5,
                "articles": [{"title": "Oil", "scraped_text": "Brent crude rose on tighter supply."}],
            },
            {
                "label": "Macro - RBI Repo Rate",
                "query": "RBI repo rate monetary policy committee MPC",
                "article_count": 2,
                "articles": [{"title": "RBI", "scraped_text": "The repo rate was left unchanged."}],
            },
        ]

    monkeypatch.setattr(cache, "_search_macro_parameters", fake_search)
    built = cache.compute_macro_news()
    labels = [row["label"] for row in built["windows"]["7"]["clusters"]]
    assert labels == ["Macro - Crude Oil", "Macro - RBI Repo Rate"]
    assert "Banks" not in labels
    assert "Brent crude rose" in built["windows"]["7"]["clusters"][0]["articles"][0]["summary"]


def test_seven_day_question_uses_the_seven_day_cache():
    from news_rag.macro_news_cache import select_macro_for_question

    payload = {
        "windows": {
            "7": {"window_days": 7, "label": "7 days", "clusters": [{"label": "Macro - Crude Oil", "articles": [{"title": "Oil", "summary": "Brent rose."}]}]},
            "30": {"window_days": 30, "label": "1 month", "clusters": [{"label": "Macro - Gold", "articles": [{"title": "Gold", "summary": "Gold fell."}]}]},
        }
    }
    picked = select_macro_for_question(payload, "tell me about banking sector and its news?", window_days=7)
    assert picked["window_days"] == 7
    assert picked["clusters"][0]["label"] == "Macro - Crude Oil"


def test_banking_and_banks_are_one_search():
    from news_rag.insight.capabilities.executor import _news_search_targets

    targets = _news_search_targets(
        ["banking", "Banks"],
        scope="sector",
        top_n=8,
        window_days=7,
        direction=None,
    )
    assert len(targets) == 1
    assert targets[0].limit == 8


def test_question_gets_two_articles_from_each_leading_section():
    from news_rag.macro_news_cache import select_macro_for_question

    clusters = []
    for index in range(6):
        clusters.append(
            {
                "label": f"Macro {index}",
                "article_count": 10 - index,
                "articles": [
                    {"title": f"{index}-a", "summary": "first story"},
                    {"title": f"{index}-b", "summary": "second story"},
                    {"title": f"{index}-c", "summary": "third story"},
                ],
            }
        )
    payload = {"windows": {"7": {"window_days": 7, "label": "7 days", "clusters": clusters}, "30": {"window_days": 30, "label": "1 month", "clusters": []}}}
    picked = select_macro_for_question(payload, "what happened last week")
    titles = [art["title"] for cluster in picked["clusters"] for art in cluster["articles"]]
    assert picked["window_days"] == 7
    assert picked["article_total"] == 10
    assert titles == ["0-a", "0-b", "1-a", "1-b", "2-a", "2-b", "3-a", "3-b", "4-a", "4-b"]
    assert "0-c" not in titles
    assert "5-a" not in titles


def test_clusters_are_ordered_by_how_many_articles_are_in_the_db():
    slim = cache._slim_clusters(
        [
            {"label": "small", "article_count": 1, "score": 9, "articles": []},
            {"label": "large", "article_count": 6, "score": 1, "articles": []},
        ]
    )
    assert [row["label"] for row in slim] == ["large", "small"]
