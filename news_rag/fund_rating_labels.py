"""RupeeStop RS label tiers — used for screens and alternate-fund picks."""

from __future__ import annotations

# Highest quality first; alternate picks walk down this list.
RS_LABEL_TIER: tuple[str, ...] = (
    "Best in category",
    "Recommended",
    "Good Choice",
    "Average",
    "Underperformer",
)

# Default ceiling when picking "any" / random funds without naming a lower tier.
PREFERRED_PICK_MAX_TIER = "Good Choice"

_PHRASE_TO_LABEL: tuple[tuple[str, str], ...] = (
    ("best in category", "Best in category"),
    ("underperformer", "Underperformer"),
    ("good choice", "Good Choice"),
    ("recommended", "Recommended"),
    ("average", "Average"),
)


def normalize_rs_label(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    low = text.lower()
    for phrase, canonical in _PHRASE_TO_LABEL:
        if phrase in low or low == phrase:
            return canonical
    for label in RS_LABEL_TIER:
        if label.lower() == low:
            return label
    return text


def label_tiers_from(start_label: str | None) -> list[str]:
    """Labels to try in order: start tier, then each lower tier."""
    start = normalize_rs_label(start_label or "")
    if not start or start not in RS_LABEL_TIER:
        return list(RS_LABEL_TIER)
    idx = RS_LABEL_TIER.index(start)
    return list(RS_LABEL_TIER[idx:])


def label_tiers_up_to(max_tier: str, *, start: str | None = None) -> list[str]:
    """Tiers from start through max_tier inclusive (quality order)."""
    tiers = label_tiers_from(start or "Best in category")
    cap = normalize_rs_label(max_tier) or PREFERRED_PICK_MAX_TIER
    if cap in tiers:
        return tiers[: tiers.index(cap) + 1]
    return tiers


def tier_rank(label: str) -> int:
    canonical = normalize_rs_label(label)
    if canonical in RS_LABEL_TIER:
        return RS_LABEL_TIER.index(canonical)
    return len(RS_LABEL_TIER)

def is_lower_tier_than(picked: str, anchor: str) -> bool:
    if not anchor:
        return False
    return tier_rank(picked) > tier_rank(anchor)


def is_higher_rated_than(picked: str, picked_score: float | None, anchor_label: str, anchor_score: float | None) -> bool:
    """True when picked is a strictly better RS label tier, or same tier with higher score."""
    anchor = normalize_rs_label(anchor_label or "")
    pick_label = normalize_rs_label(picked or "")
    if anchor and pick_label:
        pr, ar = tier_rank(pick_label), tier_rank(anchor)
        if pr < ar:
            return True
        if pr > ar:
            return False
    if anchor_score is not None and picked_score is not None:
        return float(picked_score) > float(anchor_score)
    return False
