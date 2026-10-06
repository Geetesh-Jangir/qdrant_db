from news_rag.ask_composer import _holding_bullet_from_snap, _inject_holdings_market_bullets


def test_holding_bullet_includes_news_snippet():
    snap = {
        "name": "HDFC Bank Limited",
        "weight_pct": 8.01,
        "price": {"return_1m": -1.03},
        "news": {
            "linked_articles": [
                {
                    "title": "HDFC Bank Q3",
                    "snippet": "HDFC Bank reported slower loan growth in the third quarter.",
                    "direction": "negative",
                    "max_impact": 3,
                }
            ]
        },
    }
    line = _holding_bullet_from_snap(snap)
    assert line
    assert "news we found" in line.lower()
    assert "loan growth" in line.lower()
    assert "fund" in line.lower()


def test_inject_replaces_ungrounded_amid_bullet():
    snaps = [
        {
            "name": "ICICI Bank Limited",
            "weight_pct": 7.0,
            "price": {"return_1m": -6.0},
            "news": {"linked_articles": [{"snippet": "ICICI faced FII selling pressure.", "title": "x"}]},
        }
    ]
    bullets = [
        "ICICI Bank accounts for 7% of the fund, declining -6% amid institutional developments."
    ]
    out = _inject_holdings_market_bullets(bullets, snaps)
    assert any("news we found" in b.lower() for b in out)
    assert not any("amid institutional" in b.lower() for b in out)
