"""Per-entity gate. Top-level max_relevance must not keep a weak sector row."""

from types import SimpleNamespace

import pytest

from ai_insight.common.qdrant_access import GateConfig, fetch_entity_rows, passes_gate
from ai_insight.common.freshness import is_stale, newest_scraped_at
from datetime import datetime, timedelta, timezone


def _point(payload):
    return SimpleNamespace(payload=payload)


def _article():
    body = "Reliance reported a jump in retail profit. " * 40
    return {
        "url": "https://example.com/story",
        "title": "Reliance profit and a passing mention of banks",
        "source": "Mint",
        "published_at": "2026-11-16T04:00:00Z",
        "scraped_text": body,
        "alias_urls": ["https://example.com/alias"],
        "max_relevance": 4,
        "max_impact": 3,
        "direction": "positive",
        "entities": [
            {
                "name": "Reliance",
                "type": "holding",
                "relevance": 4,
                "impact": 3,
                "direction": "positive",
                "event_type": "results",
                "about_this_name": 0.95,
                "affects_sector": 0.2,
                "affects_stock": 0.9,
                "affects_macro": 0.1,
            },
            {
                "name": "Banks",
                "type": "sector",
                "relevance": 1,
                "impact": 1,
                "direction": "negative",
                "event_type": "macro",
                "about_this_name": 0.9,
                "affects_sector": 0.4,
            },
        ],
    }


class FakeQdrant:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []
        self._index = 0

    def scroll(self, **kwargs):
        self.calls.append(kwargs)
        batch, offset = self.pages[self._index]
        self._index += 1
        return batch, offset


def test_low_relevance_sector_is_rejected_when_article_max_relevance_is_high():
    client = FakeQdrant([([_point(_article())], None)])
    window = ("2026-11-13T10:00:00Z", "2026-11-16T12:00:00Z")
    sector = fetch_entity_rows("sector", window, names=["Banks"], client=client)
    assert sector.rows == []
    assert sector.diagnostics.dropped["low_relevance"] == 1
    assert sector.diagnostics.entities_scanned == 2

    client = FakeQdrant([([_point(_article())], None)])
    holding = fetch_entity_rows("holding", window, names=["Reliance"], client=client)
    assert len(holding.rows) == 1
    assert holding.rows[0]["entity"]["name"] == "Reliance"
    assert holding.rows[0]["article"]["scraped_text"] == _article()["scraped_text"]
    assert "max_relevance" not in client.calls[0]["with_payload"]
    assert "max_relevance" not in str(client.calls[0]["scroll_filter"])
    assert "max_impact" not in str(client.calls[0]["scroll_filter"])


def test_scroll_walks_every_page():
    def entity(url):
        payload = _article()
        payload["url"] = url
        payload["entities"] = [
            {
                "name": "Banks",
                "type": "sector",
                "relevance": 3,
                "impact": 2,
                "direction": "positive",
                "event_type": "regulatory",
                "about_this_name": 0.8,
                "affects_sector": 0.9,
            }
        ]
        return payload

    client = FakeQdrant(
        [
            ([_point(entity("https://a"))], "p2"),
            ([_point(entity("https://b"))], "p3"),
            ([_point(entity("https://c"))], None),
        ]
    )
    result = fetch_entity_rows(
        "sector",
        ("2026-11-13T10:00:00Z", "2026-11-16T12:00:00Z"),
        names=["Banks"],
        client=client,
    )
    assert result.diagnostics.pages == 3
    assert result.diagnostics.articles_scanned == 3
    assert result.diagnostics.entities_passed == 3
    assert [row["article"]["url"] for row in result.rows] == ["https://a", "https://b", "https://c"]


@pytest.mark.parametrize(
    ("entity", "kept", "reason"),
    [
        ({"relevance": 2, "impact": 2, "about_this_name": 0.8, "event_type": "results", "direction": "positive"}, False, "low_relevance"),
        ({"relevance": 3, "impact": 2, "about_this_name": 0.8, "event_type": "results", "direction": "positive"}, True, None),
        ({"relevance": 3, "impact": 1, "about_this_name": 0.8, "event_type": "results", "direction": "positive"}, False, "low_impact"),
        ({"relevance": 3, "impact": 2, "about_this_name": 0.69, "event_type": "results", "direction": "positive"}, False, "low_about"),
        ({"relevance": 3, "impact": 2, "about_this_name": 0.7, "event_type": "results", "direction": "positive"}, True, None),
        ({"relevance": 4, "impact": 3, "about_this_name": 0.9, "event_type": "price_recap", "direction": "positive"}, False, "price_recap"),
        ({"relevance": 4, "impact": 2, "about_this_name": 0.9, "event_type": "opinion", "direction": "negative"}, False, "opinion_low_impact"),
        ({"relevance": 4, "impact": 3, "about_this_name": 0.9, "event_type": "opinion", "direction": "negative"}, True, None),
    ],
)
def test_gate_boundaries(entity, kept, reason):
    ok, why = passes_gate(entity, GateConfig())
    assert ok is kept
    assert why == reason


def test_neutral_direction_is_kept_with_zero_sign():
    payload = _article()
    payload["entities"] = [
        {
            "name": "Banks",
            "type": "sector",
            "relevance": 3,
            "impact": 2,
            "direction": "neutral",
            "event_type": "macro",
            "about_this_name": 0.8,
            "affects_sector": 0.5,
        }
    ]
    result = fetch_entity_rows(
        "sector",
        ("2026-11-13T10:00:00Z", "2026-11-16T12:00:00Z"),
        names=["Banks"],
        client=FakeQdrant([([_point(payload)], None)]),
    )
    assert result.rows[0]["entity"]["signed_score"] == 0


def test_holding_without_names_raises():
    with pytest.raises(ValueError):
        fetch_entity_rows("holding", ("2026-11-13T10:00:00Z", "2026-11-16T12:00:00Z"), client=FakeQdrant([]))


def test_freshness_stale_when_missing_or_old():
    window = ("2026-11-13T10:00:00Z", "2026-11-16T12:00:00Z")
    empty = FakeQdrant([([], None)])
    assert newest_scraped_at(window, client=empty) is None
    assert is_stale(window, max_hours=6, client=FakeQdrant([([], None)]), now=datetime(2026, 11, 16, 12, tzinfo=timezone.utc)) is True

    recent = (datetime(2026, 11, 16, 12, tzinfo=timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    old = (datetime(2026, 11, 16, 12, tzinfo=timezone.utc) - timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fresh = FakeQdrant([([_point({"scraped_at": recent})], None)])
    stale = FakeQdrant([([_point({"scraped_at": old})], None)])
    clock = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    assert is_stale(window, max_hours=6, client=fresh, now=clock) is False
    assert is_stale(window, max_hours=6, client=stale, now=clock) is True
