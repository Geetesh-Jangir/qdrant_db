from news_rag.ask_composer import (
    _build_news_backed_pulse_bullets,
    _dedupe_pulse_bullets,
    _is_generic_market_fluff,
)


def test_generic_fluff_detected():
    assert _is_generic_market_fluff(
        "Investors are keeping a close eye on Nifty to see how the overall market is moving."
    )


def test_news_backed_bullets_use_headline():
    clusters = [
        {
            "label": "RBI policy",
            "article_count": 3,
            "sectors": ["Banking"],
            "articles": [
                {
                    "title": "RBI holds repo rate at 6.5%",
                    "snippet": "The central bank kept rates unchanged citing inflation risks.",
                    "direction": "negative",
                    "max_impact": 4,
                    "published_at": "2026-10-04",
                }
            ],
        }
    ]
    bullets = _build_news_backed_pulse_bullets(clusters, None)
    assert bullets
    assert "Banking" in bullets[0]
    assert "related articles" not in bullets[0].lower()
    assert "mood:" not in bullets[0].lower()
    assert "inflation" in bullets[0].lower()


def test_banks_cluster_uses_sector_display_name():
    clusters = [
        {
            "label": "RBI Repo Rate",
            "article_count": 12,
            "sectors": ["Banks"],
            "articles": [
                {
                    "title": "PSBs see rate repricing",
                    "snippet": "Net interest margins of most banks are already under pressure.",
                    "direction": "unclear",
                    "max_impact": 2,
                }
            ],
        }
    ]
    bullets = _build_news_backed_pulse_bullets(clusters, None)
    assert bullets
    joined = " ".join(bullets)
    assert "Banking & Financial Services" in joined
    assert "related articles" not in joined.lower()
    assert "RBI Repo Rate" not in joined


def test_pulse_dedupe_keeps_multiple_themes():
    a = (
        "**Bond Yields** (11 related articles) — **Yields rise** (2026-10-01). "
        "First sentence. **Impact:** 4/5 · **Mood:** pressuring stocks."
    )
    b = (
        "**FII flows** (5 related articles) — **FIIs sell** (2026-10-02). "
        "Second theme sentence. **Impact:** 3/5 · **Mood:** mixed/neutral."
    )
    out = _dedupe_pulse_bullets([a, b])
    assert len(out) == 2
    assert "Yields rise" in out[0]
    assert "FIIs sell" in out[1]
