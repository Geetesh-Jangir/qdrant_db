"""Specific questions stay prose. Trailing tables and recap sections stay off."""

from news_rag.insight.contracts import AnswerMode, ExecutionPlan
from news_rag.insight.display_table_policy import (
    fact_values_already_stated,
    question_wants_fact_table,
    resolve_display_table_policy,
)
from news_rag.insight.graph import _strip_unasked_closers, strip_meta_opening_heading


def test_specific_lookup_has_no_default_table():
    plan = ExecutionPlan(intent="lookup", answer_mode=AnswerMode.DATA_ONLY, window_days=30)
    policy = resolve_display_table_policy("who manages hdfc large cap", plan)
    assert not policy.include


def test_fact_table_skipped_when_prose_has_the_figure():
    table = "| Fact | Value |\n| --- | --- |\n| Expense ratio | 2.21% |\n| 1M return | 4.59 |"
    prose = "The only figure is the expense ratio of 2.21%."
    assert fact_values_already_stated(prose, table)
    assert not fact_values_already_stated("No numbers here.", table)


def test_fact_table_only_for_compare_or_an_explicit_list():
    compare = ExecutionPlan(intent="compare")
    assert question_wants_fact_table("compare these two funds", compare)
    lookup = ExecutionPlan(intent="lookup")
    assert not question_wants_fact_table("what is the expense ratio", lookup)


def test_strip_meta_opening_heading_keeps_summary_prose():
    raw = "### The short answer\nCrude fell **16%** last week.\n\n### What drove it\n- Iran talks"
    out = strip_meta_opening_heading(raw)
    assert not out.startswith("#")
    assert out.startswith("Crude fell")
    assert "### What drove it" in out


def test_next_steps_and_summary_are_removed():
    text = "Bandhan returned **4.59%**.\n\n### What you can do next\n- Ask again.\n\n### Summary\nThat is all."
    cleaned = _strip_unasked_closers(text, keep_summary=False)
    assert "Ask again" not in cleaned
    assert "Summary" not in cleaned
    assert "4.59%" in cleaned
    kept = _strip_unasked_closers(text, keep_summary=True)
    assert "### Summary" in kept
    assert "Ask again" not in kept
