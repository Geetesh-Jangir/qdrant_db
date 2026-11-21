from news_rag.insight.prose_repair import repair_compose_placeholders


def test_strips_broken_compare_fragments() -> None:
    raw = "SBI was **ahead by percentage points**, with about ** crore** more AUM."
    out = repair_compose_placeholders(raw)
    assert "percentage points" not in out.lower() or "ahead on returns" in out
    assert "** crore**" not in out