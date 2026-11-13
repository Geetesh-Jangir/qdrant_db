"""Fund types and scheme categories for the category RS-rating URL.

The list is the one published for that API. Sector and theme slugs are not guessed.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass

# API fund-type slugs. "solution oriented" and "other" in the published list
# are solution_oriented and others on the by-category URL.
# unknown / other stay listed but are never a random pick.
CATEGORIES: dict[str, tuple[str, ...]] = {
    "equity": (
        "large cap",
        "large & mid cap",
        "flexi cap",
        "focused",
        "multi cap",
        "mid cap",
        "small cap",
        "value",
        "elss",
        "dividend yield",
        "sectoral-banking and finance",
        "sectoral-fmcg",
        "sectoral-infrastructure",
        "sectoral-pharma and healthcare",
        "sectoral-technology",
        "thematic-transportation",
        "thematic-business-cycle",
        "thematic-consumption",
        "thematic-energy",
        "thematic-esg",
        "thematic-innovation",
        "thematic-international",
        "thematic-manufacturing",
        "thematic-mnc",
        "thematic-multi-sector",
        "thematic-psu",
        "thematic-quantitative",
        "thematic-active-momentum",
        "thematic-others",
        "unknown",
    ),
    "debt": (
        "overnight",
        "liquid",
        "ultra short duration",
        "low duration",
        "money market",
        "short duration",
        "medium duration",
        "medium to long duration",
        "long duration",
        "dynamic bond",
        "corporate bond",
        "credit risk",
        "banking and psu",
        "floater",
        "gilt",
        "gilt with 10 year constant duration",
        "fmp",
    ),
    "hybrid": (
        "aggressive hybrid",
        "balanced hybrid",
        "conservative hybrid",
        "equity savings",
        "arbitrage",
        "dynamic asset allocation",
        "dynamic asset allocation or balanced advantage",
        "multi asset allocation",
    ),
    "solution_oriented": (
        "childrens",
        "retirement",
    ),
    "others": (
        "index",
        "etfs",
        "gold etf",
        "silver etf",
        "fund of funds-domestic-gold",
        "fund of funds-domestic-silver",
        "fund of funds-domestic-gold and silver",
        "fund of funds-domestic-equity",
        "fund of funds-domestic-debt",
        "fund of funds-domestic-hybrid",
        "fund of funds-income plus arbitrage",
        "fund of funds-overseas",
        "other",
    ),
}

_NOT_A_PICK = frozenset({"unknown", "other"})

# Bullion products on the category rating URL. Generic "etfs" and "index" are not metal funds.
GOLD_SCHEME_CATEGORIES: tuple[str, ...] = (
    "gold etf",
    "fund of funds-domestic-gold",
    "fund of funds-domestic-gold and silver",
)
SILVER_SCHEME_CATEGORIES: tuple[str, ...] = (
    "silver etf",
    "fund of funds-domestic-silver",
    "fund of funds-domestic-gold and silver",
)

# Subset used when the user asks for random equity compares (same-category pair).
RANDOM_EQUITY_COMPARE_CATEGORIES: tuple[str, ...] = (
    "large cap",
    "mid cap",
    "small cap",
    "flexi cap",
    "multi cap",
    "large & mid cap",
)

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
            if phrase not in _NOT_A_PICK
        ),
        key=lambda item: len(item[0]),
        reverse=True,
    )
) + (
    ("short term", "debt", "short duration"),
    ("gold fof", "others", "fund of funds-domestic-gold"),
    ("gold fund of funds", "others", "fund of funds-domestic-gold"),
    ("gold fund of fund", "others", "fund of funds-domestic-gold"),
    ("silver fof", "others", "fund of funds-domestic-silver"),
    ("silver fund of funds", "others", "fund of funds-domestic-silver"),
    ("silver fund of fund", "others", "fund of funds-domestic-silver"),
    ("balanced advantage", "hybrid", "dynamic asset allocation"),
    ("business cycle", "equity", ""),
    ("contra", "equity", ""),
    ("momentum", "equity", ""),
    ("infrastructure", "equity", ""),
    ("defence", "equity", ""),
    ("defense", "equity", ""),
    ("manufacturing", "equity", ""),
    ("retirement", "solution_oriented", "retirement"),
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


def fund_type_for_category(category: str) -> str:
    for phrase, fund_type, cat in _CATEGORY_ALIASES:
        if cat == category:
            return fund_type
    return ""


def match_all_fund_types(question: str) -> list[str]:
    """Every fund type token named in the question (order of appearance)."""
    text = _spaced_category_words(question or "")
    low = text.lower()
    hits: list[tuple[int, str, int]] = []
    for phrase, fund_type in _TYPE_WORDS:
        for match in re.finditer(rf"\b{re.escape(phrase)}\b", low):
            hits.append((match.start(), fund_type, len(phrase)))
    hits.sort(key=lambda item: (item[0], -item[2]))
    out: list[str] = []
    seen: set[str] = set()
    for _pos, fund_type, _length in hits:
        if fund_type in seen:
            continue
        seen.add(fund_type)
        out.append(fund_type)
    return out


def rating_scope_pairs(question: str) -> tuple[tuple[str, str], ...]:
    """Union of named scheme categories and every category under each named fund type."""
    q = _spaced_category_words(question or "")
    types = match_all_fund_types(q)
    cats = match_all_scheme_categories(q)
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(ft: str, category: str) -> None:
        if not ft or not category:
            return
        key = (ft, category)
        if key in seen:
            return
        seen.add(key)
        pairs.append(key)

    for category in cats:
        ft = fund_type_for_category(category) or "equity"
        add(ft, category)
    for ft in types:
        for category in categories_for(ft):
            add(ft, category)
    return tuple(pairs)


def match_all_scheme_categories(question: str) -> list[str]:
    """Every distinct named scheme category mentioned (order of appearance)."""
    text = _spaced_category_words(question or "")
    low = text.lower()
    hits: list[tuple[int, str, int]] = []
    for phrase, _fund_type, category in _CATEGORY_ALIASES:
        if not category or not _phrase_in(phrase, low):
            continue
        pos = low.find(phrase)
        if pos < 0 and " & " in phrase:
            pos = low.find(phrase.replace(" & ", " and "))
        hits.append((max(pos, 0), category, len(phrase)))
    hits.sort(key=lambda item: (item[0], -item[2]))
    out: list[str] = []
    seen: set[str] = set()
    for _pos, category, _length in hits:
        if category in seen:
            continue
        seen.add(category)
        out.append(category)
    return out


def categories_for(fund_type: str) -> tuple[str, ...]:
    return CATEGORIES.get(fund_type or "equity", ())


def _rating_tokens(text: str) -> list[str]:
    """Lowercase words. Hyphens and punctuation become spaces. No regex."""
    cleaned = (text or "").lower().replace("&", " and ").replace("/", " ")
    for compact, phrase in (
        ("largecap", "large cap"),
        ("midcap", "mid cap"),
        ("smallcap", "small cap"),
        ("flexicap", "flexi cap"),
        ("multicap", "multi cap"),
    ):
        cleaned = cleaned.replace(compact, phrase)
    for ch in "-_.,:;!?()[]\"'":
        cleaned = cleaned.replace(ch, " ")
    out: list[str] = []
    for word in cleaned.split():
        if word == "fof":
            out.extend(("fund", "of", "funds"))
        else:
            out.append(word)
    return out


def _close(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, left, right).ratio()


def _token_close(query: list[str], phrase_tokens: list[str]) -> int:
    used: set[int] = set()
    matched = 0
    for phrase_token in phrase_tokens:
        hit = None
        for index, query_token in enumerate(query):
            if index in used:
                continue
            if query_token == phrase_token or _close(query_token, phrase_token) >= 0.72:
                hit = index
                break
        if hit is None:
            continue
        used.add(hit)
        matched += 1
    return matched


def _phrase_score(query: list[str], phrase: str) -> float:
    phrase_tokens = [tok for tok in _rating_tokens(phrase) if tok not in {"a", "the", "and", "or"}]
    if not query or not phrase_tokens:
        return 0.0
    matched = _token_close(query, phrase_tokens)
    if matched == len(phrase_tokens):
        return 3.0 + len(phrase_tokens) / 10
    if matched >= 2 and matched / len(phrase_tokens) >= 0.66:
        return 2.6 + matched / 10
    return matched / len(phrase_tokens)


def _metal_flags(tokens: list[str]) -> tuple[bool, bool, bool, bool]:
    blob = set(tokens)
    has_fof = "fof" in blob or ("fund" in blob and "funds" in blob and "of" in blob)
    return "gold" in blob, "silver" in blob, "etf" in blob or "etfs" in blob, has_fof


def _metal_category(tokens: list[str]) -> str:
    gold, silver, etf, fof = _metal_flags(tokens)
    if gold and silver:
        return "fund of funds-domestic-gold and silver"
    if silver and fof:
        return "fund of funds-domestic-silver"
    if gold and fof:
        return "fund of funds-domestic-gold"
    if silver and etf:
        return "silver etf"
    if gold and etf:
        return "gold etf"
    return ""


def _type_hit(tokens: list[str]) -> str:
    best_type = ""
    best = 0.0
    for phrase, fund_type in _TYPE_WORDS:
        for token in tokens:
            score = _close(token, phrase.replace(" ", "")) if " " not in phrase else 0.0
            if " " in phrase and set(_rating_tokens(phrase)) <= set(tokens):
                score = 1.0
            if score > best:
                best = score
                best_type = fund_type
    if best >= 0.72:
        return best_type
    return ""


def resolve_rating_category(text: str) -> tuple[str, str]:
    """Map free text to (fund_type, scheme category). Empty category means type only.

    A weak score is ("", "") so the caller does not fall through to equity.
    """
    tokens = [tok for tok in _rating_tokens(text) if tok not in {"a", "the", "fund", "funds", "random", "compare", "two", "any"}]
    if not tokens:
        return "", ""
    raw = _rating_tokens(text)
    metal = _metal_category(raw)
    if metal:
        return "others", metal
    best_type = ""
    best_cat = ""
    best_score = 0.0
    for fund_type, phrases in CATEGORIES.items():
        for phrase in phrases:
            if phrase in _NOT_A_PICK:
                continue
            score = _phrase_score(tokens, phrase)
            if score > best_score:
                best_score = score
                best_type = fund_type
                best_cat = phrase
    if best_score >= 2.5:
        return best_type, best_cat
    gold, silver, _etf, _fof = _metal_flags(raw)
    if gold or silver:
        return "others", ""
    typed = _type_hit(raw)
    if typed:
        return typed, ""
    return "", ""


def pickable_categories(fund_type: str) -> tuple[str, ...]:
    return tuple(name for name in categories_for(fund_type) if name not in _NOT_A_PICK)


def metal_scheme_categories(*metals: str) -> tuple[str, ...]:
    """Published gold/silver scheme categories, ETF before fund-of-funds."""
    chosen: list[str] = []
    pools = {"gold": GOLD_SCHEME_CATEGORIES, "silver": SILVER_SCHEME_CATEGORIES}
    for metal in metals:
        for category in pools.get(metal, ()):
            if category not in chosen:
                chosen.append(category)
    return tuple(chosen)


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
