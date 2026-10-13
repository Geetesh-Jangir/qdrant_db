from news_rag.insight.grounding import strip_media_attribution


def test_strip_media_attribution_removes_outlet_cites():
    text = (
        "FIIs sold for eight weeks (Economic Times, 10 Oct). "
        "Crude eased (Economic Times, 9 Oct; Moneycontrol, 9 Oct)."
    )
    out = strip_media_attribution(text)
    assert "Economic Times" not in out
    assert "Moneycontrol" not in out
    assert "eight weeks" in out
