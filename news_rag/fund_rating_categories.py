"""Fund types and scheme categories for the category RS-rating URL.

The list is the one published for that API. Sector and theme slugs are not guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# fund type -> scheme categories, in the order a type-only question walks them
CATEGORIES: dict[str, tuple[str, ...]] = {
    "equity": (
        "large cap",
        "mid cap",
        "small cap",
        "flexi cap",
        "multi cap",
        "large & mid cap",
        "focused",
        "value",
        "elss",
        "dividend yield",
    ),
    "debt": (
        "liquid",
        "overnight",
        "ultra short duration",
        "low duration",
        "money market",
        "short duration",
        "corporate bond",
        "banking and psu",
        "gilt",
    ),
    "hybrid": (
        "aggressive hybrid",
        "conservative hybrid",
        "balanced hybrid",
        "dynamic asset allocation",
        "multi asset allocation",
        "arbitrage",
        "equity savings",
    ),
    "solution_oriented": (
        "funds-debt retirement",
        "childrens",
    ),
    "others": (
        "index",
        "etfs",
        "gold etf",
        "silver etf",
        "fund of funds-hybrid",
        "fund of funds-domestic-equity",
        "fund of funds-domestic-gold",
    ),
}

_TYPE_LABELS = {
    "equity": "Equity",
    "debt": "Debt",
    "hybrid": "Hybrid",
    "solution_oriented": "Solution oriented",
    "others": "Others",
}

# Longer phrases first so "large & mid cap" wins over "mid cap".
_CATEGORY_ALIASES: tuple[tuple[str, str, str], ...] = tuple(
    sorted(
        (
            (phrase, fund_type, phrase)
            for fund_type, phrases in CATEGORIES.items()
            for phrase in phrases
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
) + (
    ("gold fof", "others", "fund of funds-domestic-gold"),
    ("gold fund of funds", "others", "fund of funds-domestic-gold"),
    ("retirement", "solution_oriented", "funds-debt retirement"),
    ("children", "solution_oriented", "childrens"),
    ("childrens", "solution_oriented", "childrens"),
    ("solution oriented", "solution_oriented", ""),
    ("solution-oriented", "solution_oriented", ""),
)

_TYPE_WORDS = (
    ("solution oriented", "solution_oriented"),
    ("solution-oriented", "solution_oriented"),
    ("equity", "equity"),
    ("debt", "debt"),
    ("hybrid", "hybrid"),
    ("others", "others"),
    ("other", "others"),
)


def _spaced_category_words(text: str) -> str:
    """Join words users often type as one, such as largecap or large and mid cap."""
    spaced = text or ""
    for compact, phrase in (
        ("largecap", "large cap"),
        ("midcap", "mid cap"),
        ("smallcap", "small cap"),
        ("flexicap", "flexi cap"),
        ("multicap", "multi cap"),
    ):
        spaced = re.sub(rf"\b{compact}\b", phrase, spaced, flags=re.I)
    spaced = re.sub(
        r"\blarge\s+cap\s+(?:and|&)\s+mid(?:\s+cap)?\b",
        "large & mid cap",
        spaced,
        flags=re.I,
    )
    spaced = re.sub(
        r"\blarge\s+(?:and|&)\s+mid(?:\s+cap)?\b",
        "large & mid cap",
        spaced,
        flags=re.I,
    )
    spaced = re.sub(r"\blarge\s+mid(?:\s+cap)?\b", "large & mid cap", spaced, flags=re.I)
    return spaced

_TAXONOMY_RE = re.compile(
    r"\b(?:what|which|list|show|tell)\b.{0,48}\b(?:"
    r"fund[\s_-]*types?|types?\s+of\s+funds?|scheme[\s_-]*categor|"
    r"fund[\s_-]*categor|different\s+(?:categor|types)|"
    r"categor(?:y|ies)\b.{0,24}\b(?:under|in|of|come)"
    r")\b",
    re.I,
)


@dataclass
class CategoryMatch:
    fund_type: str
    category: str
    locked: bool


def _phrase_in(phrase: str, low: str) -> bool:
    forms = {phrase}
    if " & " in phrase:
        forms.add(phrase.replace(" & ", " and "))
    if " and " in phrase:
        forms.add(phrase.replace(" and ", " & "))
    return any(re.search(rf"\b{re.escape(form)}\b", low) for form in forms)


def match_scheme_category(question: str) -> CategoryMatch | None:
    """A named scheme category locks the search. A fund type alone does not."""
    text = _spaced_category_words(question or "")
    low = text.lower()
    for phrase, fund_type, category in _CATEGORY_ALIASES:
        if phrase and _phrase_in(phrase, low):
            if category:
                return CategoryMatch(fund_type, category, True)
            return CategoryMatch(fund_type, "", False)
    for phrase, fund_type in _TYPE_WORDS:
        if re.search(rf"\b{re.escape(phrase)}\b", low):
            return CategoryMatch(fund_type, "", False)
    return None


def categories_for(fund_type: str) -> tuple[str, ...]:
    return CATEGORIES.get(fund_type or "equity", ())


def asks_taxonomy(question: str) -> bool:
    q = question or ""
    if re.search(r"\b(?:best in category|good choice|underperformer|recommended)\b", q, re.I):
        return False
    return bool(_TAXONOMY_RE.search(q))


def taxonomy_reply(question: str) -> str:
    """The published types and categories. No rating call."""
    match = match_scheme_category(question or "")
    if match and (match.category or match.fund_type) and _names_a_type(question, match):
        fund_type = match.fund_type
        names = ", ".join(CATEGORIES.get(fund_type, ()))
        title = _TYPE_LABELS.get(fund_type, fund_type)
        return f"{title} categories: {names}."
    lines = ["Fund types: equity, debt, hybrid, solution oriented, and others."]
    for fund_type, phrases in CATEGORIES.items():
        title = _TYPE_LABELS.get(fund_type, fund_type)
        lines.append(f"{title}: {', '.join(phrases)}.")
    return "\n".join(lines)


def explanation_brief() -> str:
    """Official names the composer may use when explaining a type or a category."""
    listed = taxonomy_reply("")
    return (
        f"{listed}\n"
        "A large cap fund invests mainly in large companies. "
        "A mid cap fund invests mainly in mid-size companies, and a small cap fund in smaller companies. "
        "A flexi cap fund invests across company sizes, and the manager can change that mix. "
        "A multi cap fund also invests across large, mid, and small companies. "
        "Explain only what the user asked. Use these category names. "
        "Do not invent a category, a return, or a score."
    )


def _names_a_type(question: str, match: CategoryMatch) -> bool:
    low = (question or "").lower()
    if re.search(r"\b(?:under|in|of|come)\b", low) and match.fund_type:
        return True
    if match.category:
        return False
    return bool(re.search(r"\b(?:equity|debt|hybrid|solution|others)\b", low))
