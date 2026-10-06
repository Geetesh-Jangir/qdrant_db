from news_rag.scoped_retrieve import _topic_match


def test_topic_match_long_semantic_query_uses_token_overlap():
    article = {
        "title": "Nifty falls 1% as RBI holds rates steady",
        "snippet": "Indian equity benchmarks declined amid global risk-off sentiment.",
        "sector_names": ["Financials"],
    }
    semantic = "Nifty 50 Sensex India equity markets today drivers"
    assert _topic_match(article, [semantic])


def test_topic_match_empty_topics_passes():
    assert _topic_match({"title": "Anything"}, [])
