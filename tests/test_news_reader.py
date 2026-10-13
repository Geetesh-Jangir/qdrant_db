"""News reader: claim grounding, sector mapping, fallback (no network)."""

from types import SimpleNamespace

from news_rag.insight import news_reader
from news_rag.insight.brief import QuestionBrief
from news_rag.insight.news_reader import (
    NewsRead,
    SectorCall,
    _clean_claims,
    _clean_sector_calls,
    _heuristic_read,
    read_news,
    select_articles,
)

ARTS = [
    {
        "title": "Car sales jump in August",
        "url": "https://x.test/a",
        "source": "economictimes.indiatimes.com",
        "published_at": "2026-09-16T07:00:00Z",
        "direction": "positive",
        "max_impact": "3",
        "snippet": "Passenger vehicle sales rose 36.5% to 439,309 units in August, the highest ever for the month.",
    },
    {
        "title": "Tata Motors flags commodity costs",
        "url": "https://x.test/b",
        "source": "reuters.com",
        "published_at": "2026-09-25T07:00:00Z",
        "direction": "negative",
        "max_impact": "4",
        "snippet": "Tata Motors expects commodity inflation to hit passenger vehicle margins by 3% of revenue.",
    },
]


def _brief() -> QuestionBrief:
    return QuestionBrief(
        goal="auto",
        subjects=[{"role": "sector", "canonical": "Automobiles"}],
        sector_keys=["Automobiles"],
    )


def test_claim_with_number_not_in_article_is_dropped():
    raw = [
        {"text": "Sales rose 36.5% in August.", "sentiment": "positive", "article": 1},
        {"text": "Sales rose 52% in August.", "sentiment": "positive", "article": 1},  # 52 is invented
        {"text": "Margins under pressure.", "sentiment": "negative", "article": 9},  # no such article
    ]
    claims, dropped = _clean_claims(raw, ARTS)
    assert [c.text for c in claims] == ["Sales rose 36.5% in August."]
    assert dropped == 2
    assert claims[0].url == "https://x.test/a"


def test_duplicate_claims_collapse():
    raw = [
        {"text": "Sales rose 36.5% in August.", "sentiment": "positive", "article": 1},
        {"text": "Sales rose 36.5% in August.", "sentiment": "positive", "article": 1},
    ]
    claims, _ = _clean_claims(raw, ARTS)
    assert len(claims) == 1


def test_sector_reasons_are_polished():
    allowed = ["Banks", "Steel"]
    calls = _clean_sector_calls(
        [{"name": "Banks", "reason": "Livemint Updated 10 Oct 2026 IST — RBI hike weighs on lenders."}],
        allowed,
    )
    assert calls
    assert "livemint" not in calls[0].reason.lower()
    assert "ist" not in calls[0].reason.lower()


def test_sector_names_are_mapped_to_allowed_list():
    allowed = ["Automobiles", "Auto Components", "Banks"]
    calls = _clean_sector_calls(
        [{"name": "automobiles", "reason": "demand"}, {"name": "Spaceships"}, "Banks"], allowed
    )
    assert [c.name for c in calls] == ["Automobiles", "Banks"]


def test_direction_for_matches_loosely():
    read = NewsRead(
        sectors_positive=[SectorCall("Automobiles", "demand")],
        sectors_negative=[SectorCall("Auto Components", "costs")],
    )
    assert read.direction_for(["Automobiles"]) == "positive"
    assert read.direction_for(["Auto Components"]) == "negative"
    assert read.direction_for(["Banks"]) == "unknown"
    assert read.reason_for(["Automobiles"]) == "demand"


def test_select_articles_dedupes_titles_and_ranks_by_impact():
    dup = {**ARTS[0], "url": "https://x.test/dup"}
    picked = select_articles([ARTS[0], dup, ARTS[1]])
    assert len(picked) == 2
    assert picked[0]["title"].startswith("Tata Motors")  # impact 4 first


def test_heuristic_read_uses_article_text_and_tags():
    read = _heuristic_read(_brief(), ARTS)
    assert read.mode == "heuristic"
    assert read.claims and all(c.url for c in read.claims)
    assert read.tone in ("mixed", "positive", "negative")
    assert read.sectors_positive or read.sectors_negative


def test_read_news_falls_back_when_llm_fails(monkeypatch):
    monkeypatch.setattr(news_reader, "llm_api_key_configured", lambda *_a, **_k: True)

    def boom(**_k):
        raise RuntimeError("llm down")

    monkeypatch.setattr(news_reader, "call_json_llm", boom)
    read = read_news("how is auto doing", _brief(), ARTS)
    assert read.mode == "heuristic"
    assert read.claims


def test_read_news_uses_llm_result(monkeypatch):
    monkeypatch.setattr(news_reader, "llm_api_key_configured", lambda *_a, **_k: True)
    monkeypatch.setattr(news_reader, "_allowed_sector_names", lambda: ["Automobiles", "Banks"])
    parsed = {
        "tone": "mixed",
        "tone_reason": "Demand is strong but costs bite.",
        "claims": [{"text": "Sales rose 36.5% in August.", "sentiment": "positive", "article": 2}],
        "sectors_positive": [{"name": "Automobiles", "reason": "record sales"}],
        "sectors_negative": [],
        "themes": ["demand", "costs"],
    }
    monkeypatch.setattr(news_reader, "call_json_llm", lambda **_k: SimpleNamespace(parsed=parsed, truncated=False))
    # article 2 after ranking is the Car-sales article (impact 3 < Tata 4)
    read = read_news("how is auto doing", _brief(), ARTS)
    assert read.mode == "llm"
    assert read.tone == "mixed"
    assert read.claims[0].article == 2
    assert read.positive_names() == ["Automobiles"]


def test_no_articles_gives_empty_read():
    assert read_news("q", _brief(), []).mode == "none"
