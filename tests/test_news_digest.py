from news_rag.insight.news_digest import digest_articles


def test_digest_articles_uses_snippet_and_impact():
    arts = [
        {
            "title": "GST boosts auto sales",
            "direction": "positive",
            "max_impact": 4,
            "event_type": "policy",
            "scraped_text": "Passenger vehicle volumes rose after GST cuts in the festive quarter.",
        },
        {
            "title": "Costs rise",
            "direction": "negative",
            "max_impact": 3,
            "event_type": "margin_pressure",
            "scraped_text": "Input costs and freight weighed on automaker margins.",
        },
    ]
    insights, stats = digest_articles(arts)
    assert stats["positive"] == 1
    assert stats["negative"] == 1
    assert stats["avg_impact"] == 3.5
    assert any("Passenger vehicle" in x or "GST" in x for x in insights)
    assert any("score **4**" in x for x in insights)


def test_digest_strips_boilerplate_and_dedupes():
    arts = [
        {
            "title": "PV sales record",
            "url": "https://example.com/a",
            "direction": "positive",
            "max_impact": 2,
            "event_type": "operations",
            "scraped_text": (
                'Listen to this article in summarized format "We expect inventory build-up '
                "ahead of the festive season to support wholesale volumes."
            ),
        },
        {
            "title": "PV sales record",
            "url": "https://example.com/a",
            "direction": "positive",
            "max_impact": 2,
            "event_type": "operations",
            "scraped_text": "Duplicate body should be skipped.",
        },
    ]
    insights, stats = digest_articles(arts)
    assert stats["count"] == 2
    assert len(insights) == 1
    assert "Listen to this" not in insights[0]
    assert "inventory" in insights[0].lower() or "festive" in insights[0].lower()


def test_executive_sector_summary_mixed():
    from news_rag.insight.news_digest import executive_sector_summary

    stats = {"positive": 8, "negative": 8, "avg_impact": 2.0, "count": 16}
    insights = ["Positive (score **2**/5) — festive inventory supports volumes"]
    text = executive_sector_summary(stats, insights)
    assert "mixed" in text.lower()
    assert "8" in text
