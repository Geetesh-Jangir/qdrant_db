"""Scoring math for the sector leaderboard. No model and no Qdrant."""

from ai_insight.common.clustering import Cluster
from ai_insight.common.display import sector_label

from ai_insight.sector_leaderboard.schema import SectorScore, StoryScore, llm_schema
from ai_insight.sector_leaderboard.score import (
    Ranking,
    prominence,
    rank,
    score_sector,
    score_stories,
    shown,
    story_weight,
    top_stories,
    pulse_viz_data,
    pulse_viz_items,
    summarize_sector_news,
    viz_items,
)


def _row(
    url,
    title,
    direction,
    relevance=4,
    impact=3,
    about=1.0,
    published="2026-11-16T04:00:00Z",
    text="Plain story text.",
):
    return {
        "article": {
            "url": url,
            "title": title,
            "source": "Mint",
            "published_at": published,
            "scraped_text": text,
            "alias_urls": [],
        },
        "entity": {
            "name": "Banks",
            "type": "sector",
            "relevance": relevance,
            "impact": impact,
            "direction": direction,
            "event_type": "results",
            "about_this_name": about,
        },
    }


def _cluster(cluster_id, rows):
    return Cluster(
        cluster_id=cluster_id,
        label=cluster_id,
        member_urls=[row["article"]["url"] for row in rows],
        representative_title=rows[0]["article"]["title"],
        representative_url=rows[0]["article"]["url"],
        weight=len(rows),
        avg_impact=0,
        direction_mix={},
        articles=rows,
    )


def test_story_weight_matches_the_hand_calculation():
    weight, sign, magnitude = story_weight(
        {"relevance": 4, "impact": 3, "about_this_name": 1.0, "direction": "positive"}
    )
    assert (weight, sign, magnitude) == (1.0, 1, 1.0)
    weight, sign, magnitude = story_weight(
        {"relevance": 3, "impact": 2, "about_this_name": 0.8, "direction": "negative"}
    )
    assert weight == -0.4
    assert sign == -1
    assert magnitude == 0.4
    for direction in ("neutral", "unclear", "mixed", ""):
        weight, sign, _magnitude = story_weight(
            {"relevance": 4, "impact": 3, "about_this_name": 1, "direction": direction}
        )
        assert weight == 0
        assert sign == 0


def test_sector_score_shrinks_by_story_count_plus_two():
    sector = score_sector(
        "Banks",
        [
            _cluster("s00_c0", [_row("https://a", "Mandate", "positive")]),
            _cluster(
                "s00_c1",
                [_row("https://b", "Caution", "negative", relevance=3, impact=2, about=0.8)],
            ),
        ],
    )
    assert sector.n_stories == 2
    assert sector.score == 0.6 / 4
    assert shown(sector.score) == 0.15


def test_one_perfect_story_loses_to_three_consistent_stories():
    lucky = score_sector("Banks", [_cluster("s00_c0", [_row("https://a", "One win", "positive")])])
    solid_row = lambda url, title: _row(url, title, "positive", impact=2, about=1.0)
    steady = score_sector(
        "Realty",
        [
            _cluster("s17_c0", [solid_row("https://b", "Orders one")]),
            _cluster("s17_c1", [solid_row("https://c", "Orders two")]),
            _cluster("s17_c2", [solid_row("https://d", "Orders three")]),
        ],
    )
    assert lucky.score == 1 / 3
    assert steady.score == 2 / 5
    assert steady.score > lucky.score


def test_a_single_story_cannot_win_even_when_its_score_is_highest():
    lucky = score_sector("Banks", [_cluster("s00_c0", [_row("https://a", "One win", "positive")])])
    quiet = score_sector(
        "Realty",
        [
            _cluster("s17_c0", [_row("https://b", "Small one", "positive", impact=2, about=0.8)]),
            _cluster("s17_c1", [_row("https://c", "Small two", "positive", impact=2, about=0.8)]),
        ],
    )
    ranking = rank([lucky, quiet])
    assert lucky.score > quiet.score
    assert ranking.best is quiet
    assert all(sector.n_stories >= 2 for sector in ranking.eligible)
    assert lucky not in ranking.eligible


def test_missing_side_is_left_empty():
    positive = score_sector(
        "Banks",
        [
            _cluster("s00_c0", [_row("https://a", "One", "positive")]),
            _cluster("s00_c1", [_row("https://b", "Two", "positive")]),
        ],
    )
    other = score_sector(
        "Realty",
        [
            _cluster("s17_c0", [_row("https://c", "Three", "positive", impact=2)]),
            _cluster("s17_c1", [_row("https://d", "Four", "positive", impact=2)]),
        ],
    )
    ranking = rank([positive, other])
    assert ranking.best is positive
    assert ranking.worst is None

    negative = score_sector(
        "Banks",
        [
            _cluster("s00_c0", [_row("https://a", "One", "negative")]),
            _cluster("s00_c1", [_row("https://b", "Two", "negative")]),
        ],
    )
    other_neg = score_sector(
        "Realty",
        [
            _cluster("s17_c0", [_row("https://c", "Three", "negative", impact=2)]),
            _cluster("s17_c1", [_row("https://d", "Four", "negative", impact=2)]),
        ],
    )
    ranking = rank([negative, other_neg])
    assert ranking.best is None
    assert ranking.worst is negative


def test_representative_is_the_strongest_article_and_ties_break_earlier():
    mixed = _cluster(
        "s00_c0",
        [
            _row("https://early", "Early", "positive", impact=2, published="2026-11-16T01:00:00Z"),
            _row("https://late", "Late", "negative", published="2026-11-16T09:00:00Z"),
        ],
    )
    story = score_stories([mixed])[0]
    assert story.title == "Late"
    assert story.weight == -1.0
    assert story.magnitude == 1.0
    assert story.sign == -1

    tied = _cluster(
        "s00_c1",
        [
            _row("https://b", "Second", "positive", published="2026-11-16T05:00:00Z"),
            _row("https://a", "First", "negative", published="2026-11-16T01:00:00Z"),
        ],
    )
    story = score_stories([tied])[0]
    assert story.title == "First"
    assert story.sign == -1


def test_top_stories_follow_absolute_weight():
    sector = score_sector(
        "Banks",
        [
            _cluster("s00_c0", [_row("https://a", "Mild", "positive", impact=2, about=0.8)]),
            _cluster("s00_c1", [_row("https://b", "Sharp", "negative")]),
        ],
    )
    assert [story.title for story in top_stories(sector, 2)] == ["Sharp", "Mild"]


def test_summarize_sector_news_splits_direction_and_headlines():
    stories = [
        StoryScore(
            cluster_id="s00_c0",
            title="Rates cut",
            url="https://a",
            source="Mint",
            published_at="2026-11-13T06:00:00Z",
            text="Rates cut",
            weight=0.5,
            magnitude=0.5,
            sign=1,
            direction="positive",
        ),
        StoryScore(
            cluster_id="s00_c1",
            title="Loan stress rises",
            url="https://b",
            source="Mint",
            published_at="2026-11-13T07:00:00Z",
            text="Stress",
            weight=-0.4,
            magnitude=0.4,
            sign=-1,
            direction="negative",
        ),
    ]
    sector = SectorScore(name="Banks", display="Banks", score=0.05, n_stories=2, stories=stories)
    digest = summarize_sector_news(sector, headline_limit=2)
    assert digest["boosting"] == 1
    assert digest["weighing"] == 1
    assert len(digest["headlines"]["boosting"]) == 1
    assert digest["headlines"]["boosting"][0]["title"] == "Rates cut"


def test_pulse_viz_prefers_week_index_moves():
    ranking = Ranking(
        sectors=[],
        eligible=[
            SectorScore(name="Banks", display="Banks", score=0.04, n_stories=3, stories=[]),
            SectorScore(name="It - Software", display="It - Software", score=-0.01, n_stories=2, stories=[]),
        ],
        best=SectorScore(name="Banks", display="Banks", score=0.04, n_stories=3, stories=[]),
        worst=SectorScore(name="It - Software", display="It - Software", score=-0.01, n_stories=2, stories=[]),
    )
    items = pulse_viz_items(
        ranking,
        {
            "best_index": {"display": "Nifty Bank", "week_change_pct": 1.2, "sectors": ["Banks"]},
            "worst_index": {"display": "Nifty IT", "week_change_pct": -0.5, "sectors": ["It - Software"]},
        },
    )
    assert [item["week_change_pct"] for item in items] == [1.2, -0.5]
    assert items[0]["stories"] == 3


def test_pulse_viz_data_includes_driver_board():
    ranking = Ranking(
        sectors=[],
        eligible=[
            SectorScore(name="Banks", display="Banks", score=0.04, n_stories=1, stories=[]),
        ],
        best=SectorScore(
            name="Banks",
            display="Banks",
            score=0.04,
            n_stories=1,
            stories=[
                StoryScore(
                    cluster_id="s00_c0",
                    title="A",
                    url="https://a",
                    source="Mint",
                    published_at="z",
                    text="t",
                    weight=0.3,
                    magnitude=0.3,
                    sign=1,
                    direction="positive",
                )
            ],
        ),
        worst=None,
    )
    payload = pulse_viz_data(ranking, {"best_index": {"display": "Nifty Bank", "week_change_pct": 1.0, "sectors": ["Banks"]}}, best_theme="rates eased")
    assert payload["drivers"]["best"]["theme"] == "rates eased"
    assert payload["drivers"]["best"]["boosting"] == 1


def test_viz_keeps_three_each_side_and_rounds_scores():
    sectors = [
        SectorScore(name=f"P{index}", display=f"P{index}", score=score, n_stories=2, stories=[])
        for index, score in enumerate((0.5, 0.4, 0.3, 0.1))
    ]
    sectors.extend(
        SectorScore(name=f"N{index}", display=f"N{index}", score=score, n_stories=2, stories=[])
        for index, score in enumerate((-0.2, -0.55, -0.4, -0.1))
    )
    items = viz_items(sectors)
    assert [item["tone"] for item in items] == ["positive"] * 3 + ["negative"] * 3
    assert [item["score"] for item in items[:3]] == [0.5, 0.4, 0.3]
    assert [item["score"] for item in items[3:]] == [-0.55, -0.4, -0.2]
    assert all(item["stories"] == 2 for item in items)


def test_prominence_needs_five_saved_days_and_uses_the_top_decile():
    assert prominence([0.9], [0.1, 0.2, 0.3, 0.4], history_days=4) == "normal"
    history = [0.1, 0.1, 0.1, 0.2, 0.4]
    assert prominence([0.4], history, history_days=5) == "high"
    assert prominence([0.2], history, history_days=5) == "normal"
    assert prominence([], history, history_days=5) == "normal"


def test_display_names_stay_cosmetic():
    sector = score_sector("It - Software", [])
    assert sector.name == "It - Software"
    assert sector.display == sector_label("It - Software") == "It - Software"


def test_llm_schema_requires_only_the_sides_that_exist():
    schema = llm_schema(["s00_c0", "s00_c1"], [], {"best"})
    assert schema["additionalProperties"] is False
    assert "worst_theme" not in schema["properties"]
    assert schema["required"] == ["cited_cluster_ids", "best_theme"]
    assert schema["properties"]["cited_cluster_ids"]["items"]["enum"] == ["s00_c0", "s00_c1"]
    both = llm_schema(["s00_c0"], ["s17_c0"], {"best", "worst"})
    assert both["properties"]["cited_cluster_ids"]["items"]["enum"] == ["s00_c0", "s17_c0"]


def test_story_text_is_trimmed_on_a_word():
    long_text = "alpha " * 200
    story = score_stories([_cluster("s00_c0", [_row("https://a", "Long", "positive", text=long_text)])])[0]
    assert isinstance(story, StoryScore)
    assert len(story.text) <= 600
    assert story.text.endswith("alpha")
