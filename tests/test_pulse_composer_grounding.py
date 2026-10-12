from news_rag.insight.grounding import cores_in_text, finalize_text_fields, strip_ungrounded_numbers


def test_strip_ungrounded_percent():
    evidence = "return 5.2 exposure 18"
    allowed = cores_in_text(evidence)
    text = "The fund returned 9.9% while exposure is 18%."
    cleaned = strip_ungrounded_numbers(text, allowed)
    assert "9.9" not in cleaned
    assert "18" in cleaned or "18%" in cleaned


def test_finalize_compose_drops_invented_numbers():
    evidence = "benchmark_return_pct=2.0"
    headline, narrative, bullets, closing = finalize_text_fields(
        "Up 99%",
        "Benchmark moved 2.0%.",
        ["Fund fell 50%."],
        "Closing 77%.",
        evidence,
    )
    assert "99" not in headline
    assert "2.0" in narrative or "2" in narrative
    assert "50" not in "".join(bullets)
    assert "77" not in closing
