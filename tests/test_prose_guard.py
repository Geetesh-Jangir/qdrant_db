from ai_insight.common.prose_guard import scrub_refusal_prose


def test_scrub_removes_refusal_sentences():
    body = (
        "Nifty rose 0.5%. The articles do not explain today's drop. "
        "Crude eased earlier this week, which may have helped sentiment."
    )
    out = scrub_refusal_prose(body)
    assert "do not explain" not in out.lower()
    assert "Crude eased" in out