from news_rag.market_pulse import (
    MARKET_PULSE_TOP_CLUSTERS,
    market_pulse_representatives_from_clusters,
)


def test_one_rep_per_cluster_up_to_eight():
    clusters = [
        {
            "label": f"Theme {i}",
            "theme_key": f"t{i}",
            "article_count": 10 - i,
            "articles": [{"title": f"Headline {i}", "snippet": f"Body {i}", "max_impact": 3}],
        }
        for i in range(10)
    ]
    reps = market_pulse_representatives_from_clusters(clusters)
    assert len(reps) == MARKET_PULSE_TOP_CLUSTERS
    assert reps[0]["theme"] == "Theme 0"
    assert reps[0]["articles_in_theme"] == 10
