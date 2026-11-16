"""Clustering stays put when the input is shuffled."""

import json
import os
import subprocess
import sys

from ai_insight.common.clustering import cluster_rows


def _row(url, title, published, name, impact, direction, text="body", aliases=None, relevance=3):
    return {
        "article": {
            "url": url,
            "title": title,
            "source": "Mint",
            "published_at": published,
            "scraped_text": text,
            "alias_urls": aliases or [],
        },
        "entity": {
            "name": name,
            "type": "sector",
            "relevance": relevance,
            "impact": impact,
            "direction": direction,
            "event_type": "regulatory",
            "about_this_name": 0.9,
        },
    }


def _sample():
    return [
        _row("https://a", "Banks raise lending rates", "2026-11-16T06:00:00Z", "Banks", 3, "negative", text="A" * 20),
        _row("https://b", "Crude supply shock widens", "2026-11-16T05:00:00Z", "Crude", 2, "positive", text="B" * 20),
        _row("https://c", "Cement plants lift prices", "2026-11-16T04:00:00Z", "Cement", 2, "positive", text="C" * 20),
    ]


def _signature(rows):
    clusters = cluster_rows(rows, cluster_by="title", top_clusters=8)
    return [
        (c.cluster_id, c.member_urls, c.label, c.weight, c.avg_impact, c.direction_mix, c.representative_title)
        for c in clusters
    ]


def test_same_clusters_after_shuffle():
    import random

    base = _signature(_sample())
    for seed in range(25):
        rows = list(_sample())
        random.Random(seed).shuffle(rows)
        assert _signature(rows) == base


def test_hash_seed_does_not_change_ids():
    code = (
        "import json\n"
        "from ai_insight.common.clustering import cluster_rows\n"
        f"rows = json.loads({json.dumps(json.dumps(_sample()))})\n"
        "clusters = cluster_rows(rows, cluster_by='title')\n"
        "print(json.dumps([(c.cluster_id, c.member_urls) for c in clusters]))\n"
    )
    outputs = []
    for seed in ("1", "2"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        done = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, check=False)
        assert done.returncode == 0, done.stderr
        outputs.append(done.stdout)
    assert outputs[0] == outputs[1]


def test_syndicated_copies_count_once():
    rows = [
        _row("https://a", "Banks raise lending rates", "2026-11-16T06:00:00Z", "Banks", 2, "negative", text="short", aliases=["https://b"]),
        _row("https://b", "Banks raise lending rates", "2026-11-16T06:05:00Z", "Banks", 3, "negative", text="the complete syndicated article"),
        _row("https://a", "Banks raise lending rates", "2026-11-16T06:00:00Z", "Other", 1, "positive", relevance=1),
    ]
    clusters = cluster_rows(rows, cluster_by="title")
    assert len(clusters) == 1
    assert clusters[0].weight == 1
    assert clusters[0].member_urls == ["https://a"]
    assert clusters[0].articles[0]["entity"]["name"] == "Banks"
    assert clusters[0].articles[0]["article"]["scraped_text"] == "the complete syndicated article"


def test_title_mode_does_not_merge_unrelated_stories_that_share_an_entity():
    rows = [
        _row("https://a", "Banks raise lending rates", "2026-11-16T06:00:00Z", "Banks", 3, "negative"),
        _row("https://b", "Crude supply shock widens", "2026-11-16T05:00:00Z", "Banks", 2, "positive"),
    ]
    by_title = cluster_rows(rows, cluster_by="title")
    by_entity = cluster_rows(rows, cluster_by="entity")
    assert len(by_title) == 2
    assert len(by_entity) == 1
    assert by_entity[0].weight == 2
    assert by_entity[0].direction_mix["negative"] == 1
    assert by_entity[0].direction_mix["positive"] == 1
