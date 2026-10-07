from news_rag.ask_composer import COMPOSER_SYSTEM, _finalize_compose, _strip_ungrounded_numbers
from news_rag.ask_execution import ExecutionBundle
from news_rag.name_resolution import ResolvedNames


def _bundle() -> ExecutionBundle:
    return ExecutionBundle(names=ResolvedNames())


def test_composer_prompt_is_not_a_fixed_bullet_template():
    assert "Four to six" not in COMPOSER_SYSTEM
    assert "at most three" not in COMPOSER_SYSTEM.lower()
    assert "one clean sentence" not in COMPOSER_SYSTEM.lower()
    assert "format_chosen" in COMPOSER_SYSTEM
    assert "Everyday words" in COMPOSER_SYSTEM
    assert "how that hits a sector" in COMPOSER_SYSTEM


def test_finalize_keeps_model_narrative_and_bullets():
    bullets = ["**Banks** — credit growth is the story."]
    headline, narrative, out = _finalize_compose(
        "Headline",
        "A connected account of the tape.",
        bullets,
        _bundle(),
        market_pulse_clusters=[{"label": "RBI Repo Rate", "articles": [{"snippet": "margins"}]}],
        evidence_text="credit",
    )
    assert headline == "Headline"
    assert narrative == "A connected account of the tape."
    assert out == bullets
    assert "Macro Backdrop" not in " ".join(out)


def test_finalize_drops_exact_duplicates_and_invented_percentages():
    headline, narrative, bullets = _finalize_compose(
        "Rates moved 9.9%",
        "Banks gained on the policy.",
        [
            "Banks gained on the policy.",
            "Banks rose 9.9% today.",
            "IT exports held up.",
            "IT exports held up.",
        ],
        _bundle(),
        evidence_text="no figures",
    )
    assert "9.9" not in headline
    assert narrative == "Banks gained on the policy."
    assert bullets == ["Banks rose today.", "IT exports held up."]
    assert _strip_ungrounded_numbers("Still down between **-1.2%** and **-0.4%**.", set()) == "Still down."
