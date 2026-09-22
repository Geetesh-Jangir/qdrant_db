"""Decide whether a headline belongs to a holding or a sector."""

from __future__ import annotations

from news_pipeline.textutil import contains_phrase


def matches_entity(title: str, snippet: str, entity: dict) -> bool:
    text = f"{title or ''} {snippet or ''}"
    if entity["type"] == "sector":
        return any(contains_phrase(text, keyword) for keyword in entity["keywords"])
    return _holding_mentioned(text, entity)


def _holding_mentioned(text: str, entity: dict) -> bool:
    aliases: list[str] = entity["aliases"]
    negatives: list[str] = entity["negative_aliases"]
    matched_aliases = [alias for alias in aliases if contains_phrase(text, alias)]
    if not matched_aliases:
        return False

    matched_negatives = [name for name in negatives if contains_phrase(text, name)]
    if not matched_negatives:
        return True

    # "SBI" inside "SBI Life" is the lookalike. The longer name wins.
    for alias in matched_aliases:
        blocked = False
        for negative in matched_negatives:
            if len(negative) > len(alias) and contains_phrase(negative, alias):
                blocked = True
                break
        if not blocked:
            return True
    return False
