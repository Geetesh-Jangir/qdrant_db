"""Category RS-rating lists. Regular and growth stay fixed.

A named category is one URL. A fund type walks that type's categories only
when a label, score, or return filter is still short. AMC-only lists stay on
the markdown catalog.
"""

from __future__ import annotations

import logging
import random
import re
import threading
import time
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Any, Callable
from urllib.parse import quote

import httpx

from news_rag.rupeestop_auth import rupeestop_admin_request_headers
from news_rag.fund_rating_categories import (
    asks_taxonomy,
    categories_for,
    match_all_fund_types,
    match_all_scheme_categories,
    match_scheme_category,
    metal_scheme_categories,
    rating_scope_pairs,
)
from news_rag.tools import explicit_fund_count

logger = logging.getLogger(__name__)

_RATING_URL = (
    "https://backend.rupeestop.com/api/v1/admin/rs-rating/by-category/"
    "{fund_type}/{category}/regular/growth"
)
_CACHE_TTL_SEC = 3600
_HTTP_TIMEOUT = 12.0
_SHORTLIST = 10
_POSITIVE_CAP = 40

_cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
_cache_lock = threading.Lock()

_LABELS = (
    ("best in category", "Best in category"),
    ("underperformer", "Underperformer"),
    ("good choice", "Good Choice"),
    ("recommended", "Recommended"),
    ("average", "Average"),
)

_RETURN_RE = re.compile(
    r"\b(?:returns?|performance|performed|performing|gave|giving|yield)\b|"
    r"\b(?:1|3|5)\s*[- ]?(?:y|yr|year)s?\b|\b(?:one|three|five)\s+years?\b",
    re.I,
)
_POSITIVE_RE = re.compile(r"\b(?:positive|gained|gain|up|rose|risen|in the green)\b", re.I)
_HIGHEST_RE = re.compile(r"\b(?:highest|best|top|maximum|max)\b", re.I)
_LOWEST_RE = re.compile(r"\b(?:lowest|worst|minimum|min|bottom)\b", re.I)
_SCORE_RE = re.compile(
    r"\b(?:rs[\s_-]*rating|final[\s_-]*score|rupeestop[\s_-]*score|score|rat(?:ing|ed))\b",
    re.I,
)
_ABOVE_RE = re.compile(
    r"\b(?:above|over|greater than|more than|at least|>=)\s*(\d{1,3}(?:\.\d+)?)\b",
    re.I,
)
_LIST_RE = re.compile(r"\b(?:funds?|fudns?)\b", re.I)
_RANK_WORD_RE = re.compile(r"\b(?:highest|best|top|lowest|worst|random)\b", re.I)
_BUY_RE = re.compile(r"\bshould\s+i\s+(?:buy|sell|hold|invest)\b", re.I)
_SUGGEST_RE = re.compile(
    r"\b(?:recommend(?:ed|ation)?|suggest(?:ion|ed)?)\b|\bgood\s+funds?\b|\brandom\s+funds?\b",
    re.I,
)
_PERFORM_RE = re.compile(
    r"\b(?:perform(?:ing|ed|s)?|doing)\b.{0,40}\b(?:well|poorly|badly|worse|worst|better)\b|"
    r"\b(?:well|poorly|badly)\b.{0,24}\bperform",
    re.I,
)
_POOR_RE = re.compile(r"\b(?:poorly|badly|worse|worst)\b", re.I)
_POSITIVE_RETURN_RE = re.compile(
    r"\bpositive\s+returns?\b|\bshowing\s+(?:a\s+)?positive\b|\bperforming\s+positive\b|\bpositive\b",
    re.I,
)


def _looks_like_fund_list(question: str) -> bool:
    """A list of funds, including one fund asked for as the best or the highest."""
    if explicit_fund_count(question) is not None:
        return True
    if re.search(r"\b(?:funds?|fudns?)\b", question or "", re.I):
        return True
    if _LIST_RE.search(question or "") and _RANK_WORD_RE.search(question or ""):
        return True
    return False


@dataclass
class RatingScreenSpec:
    count: int
    fund_type: str
    category: str
    locked: bool
    label: str
    min_score: float | None
    highest_score: bool
    return_window: str
    return_direction: str
    compare_category: bool
    random_sample: bool
    amc: str
    suggestion: str = ""
    label_fallback: str = ""
    walk_categories: tuple[str, ...] = ()
    walk_category_pairs: tuple[tuple[str, str], ...] = ()
    spread_categories: bool = False
    one_per_category: bool = False
    mix_note: str = ""

    @property
    def walks(self) -> bool:
        if self.locked:
            return False
        return bool(self.label or self.min_score is not None or self.return_direction or self.highest_score)


def _return_direction(question: str, label: str, window: str) -> str:
    """Rank by a return only when the user asked for the highest or the lowest.

    "Best in category" is a label. It is not a request to sort by 1Y return.
    """
    if not window:
        return ""
    text = question or ""
    if label:
        text = re.sub(re.escape(label), " ", text, flags=re.I)
    if _POSITIVE_RE.search(text):
        return "positive"
    if _LOWEST_RE.search(text):
        return "lowest"
    if _HIGHEST_RE.search(text):
        return "highest"
    return ""


def _amc_token(question: str) -> str:
    from news_rag.tools import screen_hints_from_question

    return str(screen_hints_from_question(question).get("amc") or "").strip()


def _amc_outside_label(question: str, label: str) -> str:
    """A rating label such as Good Choice is not the Choice AMC."""
    amc = _amc_token(question)
    if not amc or not label:
        return amc
    if amc.lower() not in label.lower():
        return amc
    without_label = re.sub(re.escape(label), " ", question or "", flags=re.I)
    if re.search(rf"\b{re.escape(amc)}\b", without_label, re.I):
        return amc
    return ""


def _return_window(question: str) -> str:
    from news_rag.tools import explicit_return_window

    return explicit_return_window(question)


def _label_in(question: str) -> str:
    low = (question or "").lower()
    for phrase, label in _LABELS:
        if phrase in low:
            return label
    return ""


_ASKS_NAME_FUND_RE = re.compile(
    r"\b(?:"
    r"name\s+(?:of\s+)?(?:a|an|one|any)|"
    r"name\s+me\s+(?:a|an|one|any)|"
    r"tell\s+me\s+(?:the\s+)?name\s+of|"
    r"(?:give|tell)\s+me\s+(?:a|an|one|any)"
    r")\b",
    re.I,
)


def _fund_type_in_name_clause(question: str) -> str:
    """Fund type the user asked us to name (ignore 'debt vs equity' education clauses)."""
    q = question or ""
    for pattern in (
        r"\b(?:name|give|tell|show)\s+(?:me\s+)?(?:any\s+)?(?:\d+\s+)?(?:random(?:ly)?\s+)?"
        r"(debt|equity|hybrid|solution(?:\s+oriented)?|others)\s+funds?\b",
        r"\brandom(?:ly)?\s+(debt|equity|hybrid)\s+funds?\b",
        r"\b(?:any\s+)?(?:\d+\s+)?(?:random(?:ly)?\s+)?(debt|equity|hybrid)\s+funds?\b",
    ):
        m = re.search(pattern, q, re.I)
        if not m:
            continue
        token = m.group(1).lower().strip()
        if token.startswith("solution"):
            return "solution_oriented"
        return token
    return ""


def fund_type_name_spec(question: str) -> RatingScreenSpec | None:
    """Name one fund when the user names only a fund type (e.g. debt fund) — random scheme category."""
    q = question or ""
    if _BUY_RE.search(q):
        return None
    from news_rag.insight.concept_asks import asks_wants_named_example

    if not (_ASKS_NAME_FUND_RE.search(q) or asks_wants_named_example(q)):
        return None
    if _label_in(q) or _SCORE_RE.search(q):
        return None
    fund_type = _fund_type_in_name_clause(q)
    if not fund_type:
        types_named = match_all_fund_types(q)
        if len(types_named) == 1:
            fund_type = types_named[0]
        else:
            match = match_scheme_category(q)
            if not match or not match.fund_type:
                return None
            if match.locked and match.category:
                return None
            fund_type = match.fund_type
    if not re.search(r"\b(?:equity|debt|hybrid|solution|others)\b", q, re.I):
        return None
    if not categories_for(fund_type):
        return None
    count = explicit_fund_count(q) or 1
    match = match_scheme_category(q)
    locked = bool(match and match.locked and match.category)
    from news_rag.tools import question_wants_performance_ranking

    if question_wants_performance_ranking(q):
        window = _return_window(q) or "3Y"
        wants_positive = bool(_POSITIVE_RETURN_RE.search(q))
        if wants_positive:
            direction = "positive"
        elif _POOR_RE.search(q):
            direction = "lowest"
        else:
            direction = "highest"
        return RatingScreenSpec(
            count=count,
            fund_type=fund_type,
            category=match.category if locked else "",
            locked=locked,
            label="",
            min_score=None,
            highest_score=False,
            return_window=window,
            return_direction=direction,
            compare_category=False,
            random_sample=False,
            amc="",
            suggestion="period",
            label_fallback="Recommended",
            spread_categories=count > 1 and not locked,
        )
    return RatingScreenSpec(
        count=count,
        fund_type=fund_type,
        category=match.category if locked else "",
        locked=locked,
        label="Best in category",
        min_score=None,
        highest_score=False,
        return_window="",
        return_direction="",
        compare_category=False,
        random_sample=False,
        amc="",
        suggestion="rated",
        label_fallback="Recommended",
        spread_categories=count > 1 and not locked,
    )


def _category_fund_name_spec(question: str) -> RatingScreenSpec | None:
    """Name one fund in a named category via the RS-rating category API (not NAV random screen)."""
    q = question or ""
    if _BUY_RE.search(q):
        return None
    if not _ASKS_NAME_FUND_RE.search(q):
        return None
    if _label_in(q) or _SCORE_RE.search(q):
        return None
    if _RETURN_RE.search(q) and _return_window(q) and (_PERFORM_RE.search(q) or _POOR_RE.search(q)):
        return None
    from news_rag.insight.concept_asks import asks_concept_with_catalog_example

    if asks_concept_with_catalog_example(q):
        return None
    match = match_scheme_category(q)
    if not (match and match.locked and match.category):
        return None
    count = explicit_fund_count(q) or 1
    return RatingScreenSpec(
        count=count,
        fund_type=match.fund_type or "equity",
        category=match.category,
        locked=True,
        label="Best in category",
        min_score=None,
        highest_score=False,
        return_window="",
        return_direction="",
        compare_category=False,
        random_sample=False,
        amc="",
        suggestion="rated",
        label_fallback="Recommended",
    )


def _suggestion_spec(question: str) -> RatingScreenSpec | None:
    """A good, recommended, or random fund, or a fund that did well or poorly over a period."""
    q = question or ""
    if re.search(r"\bwhy\b", q, re.I):
        return None
    if _BUY_RE.search(q) or not _LIST_RE.search(q):
        return None
    window = _return_window(q)
    wants_positive = bool(_POSITIVE_RETURN_RE.search(q))
    wants_period = bool(_PERFORM_RE.search(q) or wants_positive or _POOR_RE.search(q))
    if wants_period:
        window = window or "3Y"
        match = match_scheme_category(q)
        named = bool(match and match.locked and match.category)
        count = explicit_fund_count(q) or 5
        if wants_positive:
            direction = "positive"
        elif _POOR_RE.search(q):
            direction = "lowest"
        else:
            direction = "highest"
        return RatingScreenSpec(
            count=count,
            fund_type=(match.fund_type if match and match.fund_type else "equity"),
            category=match.category if named else "",
            locked=named,
            label="",
            min_score=None,
            highest_score=False,
            return_window=window,
            return_direction=direction,
            compare_category=False,
            random_sample=False,
            amc="",
            suggestion="period",
            label_fallback="Recommended",
            spread_categories=count > 1 and not named,
        )
    if explicit_fund_count(q) and window:
        return None
    if not _SUGGEST_RE.search(q):
        return None
    match = match_scheme_category(q)
    named_label = _label_in(q)
    count = explicit_fund_count(q) or 1
    locked = bool(match and match.locked and match.category)
    random_sample = bool(re.search(r"\brandom\b", q, re.I))
    spec = RatingScreenSpec(
        count=count,
        fund_type=(match.fund_type if match and match.fund_type else "equity"),
        category=match.category if locked else "",
        locked=locked,
        label=named_label or "Best in category",
        min_score=None,
        highest_score=not locked,
        return_window="",
        return_direction="",
        compare_category=False,
        random_sample=random_sample,
        amc="",
        suggestion="rated",
        label_fallback="" if named_label else "Recommended",
    )
    if random_sample and not named_label:
        spec = replace(spec, label="", label_fallback="")
    return spec


_METAL_WORD_RE = re.compile(r"\b(gold|silver)\b", re.I)


def _question_names_amc_scheme(question: str) -> bool:
    """True when the catalog's AMC aliases appear in the question (ABSL, PPFAS, a new house, and so on)."""
    from news_rag.fund_search import _amc_hints_from_tokens

    tokens = re.findall(r"\b[a-z0-9]+\b", (question or "").lower())
    return bool(_amc_hints_from_tokens(tokens))


def _metal_fund_categories(question: str) -> tuple[str, ...]:
    """Gold/silver scheme categories for an unnamed fund list. Empty for a spot-price or one named scheme."""
    q = question or ""
    if not _METAL_WORD_RE.search(q):
        return ()
    if not re.search(r"\b(?:funds?|etfs?|fo[fF]s?|schemes?|fund of funds?)\b", q, re.I):
        return ()
    product = re.search(
        r"\b(?:gold|silver)\s+(?:etfs?|funds?|fo[fF]s?|schemes?|fund of funds?)\b|"
        r"\b(?:etfs?|funds?|fo[fF]s?|schemes?|fund of funds?)\b(?:\s+\w+){0,3}\s+(?:gold|silver)\b",
        q,
        re.I,
    )
    from news_rag.insight.brief import question_is_bullion_metal_price_question

    if not product and question_is_bullion_metal_price_question(q):
        return ()
    if re.search(r"\bwhat(?:'s| is| are)\b", q, re.I) and not re.search(
        r"\b(?:names?|list|show|which|random|\d+)\b", q, re.I
    ):
        return ()
    list_ask = bool(
        explicit_fund_count(q)
        or re.search(
            r"\b(?:random|names? of|list|show|which|suggest|recommend|best|top|any|some)\b",
            q,
            re.I,
        )
        or re.search(r"\b(?:gold|silver)\s+(?:funds?|etfs?|fo[fF]s?|schemes?)\b", q, re.I)
    )
    if not list_ask:
        return ()
    from news_rag.insight.memory.fund_context import (
        question_picks_one_shown_fund,
        question_refers_to_shown_list,
    )

    if question_picks_one_shown_fund(q) or question_refers_to_shown_list(q):
        return ()
    if _question_names_amc_scheme(q) and not re.search(r"\b(?:random|names? of|list of)\b", q, re.I):
        if not explicit_fund_count(q) or explicit_fund_count(q) == 1:
            return ()
    metals: list[str] = []
    if re.search(r"\bgold\b", q, re.I):
        metals.append("gold")
    if re.search(r"\bsilver\b", q, re.I):
        metals.append("silver")
    etf_only = bool(re.search(r"\betfs?\b", q, re.I)) and not re.search(
        r"\bfunds?\b|\bfof\b|fund of fund", q, re.I
    )
    fof_only = bool(re.search(r"\bfof\b|fund of fund", q, re.I)) and not re.search(
        r"\betfs?\b|\bfunds?\b", q, re.I
    )
    chosen = metal_scheme_categories(*metals)
    if etf_only:
        chosen = tuple(name for name in chosen if name.endswith("etf"))
    elif fof_only:
        chosen = tuple(name for name in chosen if "fund of funds" in name)
        if len(metals) == 1 and not re.search(r"\bgold and silver\b|\bsilver and gold\b", q, re.I):
            metal = metals[0]
            chosen = tuple(name for name in chosen if name.endswith(metal) or name == f"fund of funds-domestic-{metal}")
    return chosen


_BALANCED_PORTFOLIO_PAIRS: tuple[tuple[str, str], ...] = (
    ("equity", "large cap"),
    ("equity", "mid cap"),
    ("equity", "small cap"),
    ("equity", "flexi cap"),
    ("debt", "corporate bond"),
    ("hybrid", "conservative hybrid"),
    ("others", "gold etf"),
)

_LONG_HORIZON_RE = re.compile(
    r"\b(?:more\s+than|over|above|at\s+least)\s+(?:\d+|ten)\s+years?\b|"
    r"\b(?:10|ten)\+?\s*years?\s*(?:horizon|investment|term)?\b|"
    r"\bthinking?\s+for\s+(?:more\s+than\s+)?(?:10|ten)\s+years?\b",
    re.I,
)
_FUND_NAMES_ASK_RE = re.compile(
    r"\b(?:fund\s+names?|name\s+(?:me\s+)?(?:some\s+)?funds?|tell\s+me\s+some\s+fund|"
    r"some\s+funds?\b|suggest\s+(?:some\s+)?funds?)\b",
    re.I,
)
_IDEAL_PORTFOLIO_SHAPE_RE = re.compile(
    r"\bideal\s+portfolio\b|\bportfolio\s+should\s+(?:look|hold)\b|\bwhat\s+categories\b",
    re.I,
)


def _recent_portfolio_shape_chat(memory: dict[str, Any] | None) -> bool:
    if not isinstance(memory, dict):
        return False
    parts: list[str] = []
    for row in memory.get("chat_turns") or memory.get("turns") or []:
        if not isinstance(row, dict):
            continue
        parts.append(str(row.get("user") or ""))
    blob = " ".join(parts).lower()
    return bool(
        re.search(
            r"\bideal\s+portfolio\b|\bcategories\s+and\s+assets\b|\bportfolio\s+should\s+hold\b",
            blob,
            re.I,
        )
    )


def asks_ideal_portfolio_shape(question: str) -> bool:
    q = question or ""
    if not _IDEAL_PORTFOLIO_SHAPE_RE.search(q):
        return False
    return bool(re.search(r"\bcategor(?:y|ies)\b|\basset", q, re.I))


def asks_balanced_long_horizon_fund_menu(question: str, memory: dict[str, Any] | None = None) -> bool:
    q = question or ""
    has_horizon = bool(_LONG_HORIZON_RE.search(q))
    if not has_horizon and re.search(r"\bfor\s+it\b", q, re.I):
        has_horizon = _recent_portfolio_shape_chat(memory)
    if not has_horizon:
        return False
    if not (_FUND_NAMES_ASK_RE.search(q) or re.search(r"\bsome\s+funds?\b", q, re.I)):
        return False
    if match_scheme_category(q) and match_scheme_category(q).locked:
        return False
    if len(match_all_scheme_categories(q)) == 1:
        return False
    return True


def _make_balanced_portfolio_spec(*, mix_note: str, return_window: str = "5Y") -> RatingScreenSpec:
    pairs = _BALANCED_PORTFOLIO_PAIRS
    return RatingScreenSpec(
        count=len(pairs),
        fund_type="equity",
        category="",
        locked=False,
        label="Best in category",
        min_score=None,
        highest_score=False,
        return_window=return_window,
        return_direction="",
        compare_category=False,
        random_sample=False,
        amc="",
        suggestion="rated",
        label_fallback="Recommended",
        walk_category_pairs=pairs,
        spread_categories=True,
        mix_note=mix_note,
    )


def balanced_portfolio_examples_spec(
    question: str,
    memory: dict[str, Any] | None = None,
) -> RatingScreenSpec | None:
    """One top-rated fund per sleeve for diversification (long horizon or ideal portfolio shape)."""
    q = question or ""
    if asks_ideal_portfolio_shape(q):
        note = (
            "Ideal diversified portfolio: one RupeeStop top pick per sleeve — "
            "equity across cap sizes, debt and conservative hybrid for stability, gold as a hedge."
        )
        return _make_balanced_portfolio_spec(mix_note=note, return_window="")
    if asks_balanced_long_horizon_fund_menu(q, memory):
        note = (
            "10+ year horizon: balanced mix — equity (large/mid/small/flexi), "
            "debt and conservative hybrid for stability, gold ETF for diversification."
        )
        return _make_balanced_portfolio_spec(mix_note=note, return_window="5Y")
    return None


def _allocation_mix_spec(question: str) -> RatingScreenSpec | None:
    """One rated fund per equity/debt/gold sleeve when the user gives a percentage mix."""
    q = question or ""
    weights: dict[str, int] = {}
    for match in re.finditer(r"(\d{1,3})\s*%\s*(equity|debt|gold)\b", q, re.I):
        weights[match.group(2).lower()] = int(match.group(1))
    for match in re.finditer(r"\b(equity|debt|gold)\s*(?:at\s*)?(\d{1,3})\s*%", q, re.I):
        weights[match.group(1).lower()] = int(match.group(2))
    if len(weights) < 2:
        return None
    if not any(name in weights for name in ("equity", "debt", "gold")):
        return None
    pairs: list[tuple[str, str]] = []
    equity_cats = categories_for("equity")
    if "equity" in weights and equity_cats:
        pairs.append(("equity", equity_cats[0]))
    debt_cats = categories_for("debt")
    if "debt" in weights and debt_cats:
        pairs.append(("debt", debt_cats[0]))
    gold_cats = metal_scheme_categories("gold")
    if "gold" in weights and gold_cats:
        pairs.append(("others", gold_cats[0]))
    if len(pairs) < 2:
        return None
    mix_note = "User mix: " + ", ".join(
        f"{weights[name]}% {name}" for name in ("equity", "debt", "gold") if name in weights
    )
    return RatingScreenSpec(
        count=len(pairs),
        fund_type=pairs[0][0],
        category="",
        locked=False,
        label="Best in category",
        min_score=None,
        highest_score=False,
        return_window="",
        return_direction="",
        compare_category=False,
        random_sample=False,
        amc="",
        suggestion="rated",
        label_fallback="Recommended",
        walk_category_pairs=tuple(pairs),
        spread_categories=True,
        mix_note=mix_note,
    )


def _metal_fund_spec(question: str) -> RatingScreenSpec | None:
    categories = _metal_fund_categories(question)
    if not categories:
        return None
    q = question or ""
    count = explicit_fund_count(q) or 3
    random_sample = bool(re.search(r"\brandom\b", q, re.I))
    return RatingScreenSpec(
        count=count,
        fund_type="others",
        category=categories[0],
        locked=False,
        label="",
        min_score=None,
        highest_score=False,
        return_window="",
        return_direction="",
        compare_category=False,
        random_sample=random_sample,
        amc="",
        suggestion="rated",
        label_fallback="",
        walk_categories=categories,
        spread_categories=True,
    )


def parse_rating_screen(question: str) -> RatingScreenSpec | None:
    """A category rating list, or None when the catalog should answer."""
    q = question or ""
    if asks_taxonomy(q):
        return None
    mix = _allocation_mix_spec(q)
    if mix is not None:
        return mix
    metal = _metal_fund_spec(q)
    if metal is not None:
        return metal
    suggested = _suggestion_spec(q)
    if suggested is not None:
        return suggested
    named_in_category = _category_fund_name_spec(q)
    if named_in_category is not None:
        return named_in_category
    by_type = fund_type_name_spec(q)
    if by_type is not None:
        return by_type
    if re.search(r"\bwhy\b", q, re.I):
        return None
    if not _looks_like_fund_list(q):
        return None
    from news_rag.tools import asks_funds_with_sector_exposure

    if asks_funds_with_sector_exposure(q) and not _label_in(q) and not _SCORE_RE.search(q):
        return None

    match = match_scheme_category(q)
    label = _label_in(q)
    window = _return_window(q) if _RETURN_RE.search(q) else ""
    direction = _return_direction(q, label, window)
    above = _ABOVE_RE.search(q)
    min_score = float(above.group(1)) if above and _SCORE_RE.search(q) else None
    highest_score = bool(_SCORE_RE.search(q) and _HIGHEST_RE.search(q) and not window)
    amc = _amc_outside_label(q, label)
    types_named = match_all_fund_types(q)
    cats_named = match_all_scheme_categories(q)
    multi_scope = False
    if re.search(r"\bor\b", q, re.I):
        multi_scope = (
            len(types_named) > 1
            or len(cats_named) > 1
            or (bool(types_named) and bool(cats_named))
        )
    fund_type = match.fund_type if match else ""
    category = match.category if match else ""
    locked = bool(match and match.locked)
    if multi_scope:
        locked = False
        category = ""
        fund_type = types_named[0] if types_named else (fund_type or "equity")
    has_rating_filter = bool(label or min_score is not None or highest_score or window)
    if not explicit_fund_count(q) and not re.search(r"\brandom\b", q, re.I) and not has_rating_filter:
        return None
    if amc and not has_rating_filter:
        return None
    if not fund_type and not has_rating_filter:
        return None
    if not fund_type:
        fund_type = "equity"
    count = explicit_fund_count(q)
    if count is None and re.search(r"\ba\s+fund\b", q, re.I) and not re.search(r"\bfunds\b", q, re.I):
        count = 1
    if count is None:
        count = 1 if (highest_score or direction in {"highest", "lowest"}) else 5
    walk_cats = ()
    walk_pairs: tuple[tuple[str, str], ...] = ()
    spread = False
    if multi_scope:
        scope_pairs = rating_scope_pairs(q)
        spread = bool(scope_pairs)
        walk_pairs = scope_pairs
        walk_cats = tuple(dict.fromkeys(cat for _ft, cat in scope_pairs))
    elif (
        not locked
        and count > 1
        and not category
        and not label
        and not window
        and not highest_score
        and min_score is None
    ):
        spread = True
    return RatingScreenSpec(
        count=count,
        fund_type=fund_type,
        category=category,
        locked=locked,
        label=label,
        min_score=min_score,
        highest_score=highest_score,
        return_window=window,
        return_direction=direction,
        compare_category=bool(re.search(r"\bcategory\s+averages?\b|\bcompare\b", q, re.I)),
        random_sample=bool(re.search(r"\brandom\b", q, re.I)),
        amc=amc,
        walk_categories=walk_cats,
        walk_category_pairs=walk_pairs,
        spread_categories=spread,
    )


def asks_rating_list(question: str) -> bool:
    spec = parse_rating_screen(question)
    return spec is not None and spec.suggestion != "period"


def _public_row(raw: dict[str, Any], *, fund_type: str, category: str) -> dict[str, Any] | None:
    isin = str(raw.get("isin") or "").strip().upper()
    if not isin:
        return None
    inputs = raw.get("inputs") if isinstance(raw.get("inputs"), dict) else {}
    try:
        score = round(float(raw.get("finalScore")), 2)
    except (TypeError, ValueError):
        score = None
    name = _catalog_name(isin) or str(raw.get("fundName") or isin).strip()
    row = {
        "isin": isin,
        "fund_name": name,
        "final_score": score,
        "rs_label": str(raw.get("label") or "").strip(),
        "category": str(raw.get("schemeCategory") or category).strip(),
        "fund_type": str(raw.get("fundType") or fund_type).strip(),
        "benchmark": str(raw.get("benchmark") or "").strip(),
        "as_on": str(raw.get("asOnDate") or "").strip(),
    }
    for field, key in (("1Y", "trailing1Y"), ("3Y", "trailing3Y"), ("5Y", "trailing5Y")):
        try:
            row[f"_trail_{field}"] = float(inputs.get(key))
        except (TypeError, ValueError):
            row[f"_trail_{field}"] = None
    for field, key in (("1y", "categoryAvg1Y"), ("3y", "categoryAvg3Y"), ("5y", "categoryAvg5Y")):
        try:
            row[f"category_avg_{field}_pct"] = round(float(inputs.get(key)), 2)
        except (TypeError, ValueError):
            pass
    from news_rag.fund_risk import _public_pillars

    pillars = _public_pillars(raw.get("pillars"))
    if pillars:
        row["pillars"] = pillars
    return row


def _catalog_name(isin: str) -> str:
    try:
        from news_rag.fund_search import get_fund_index

        entry = get_fund_index().catalog_entry(isin) or {}
    except Exception:
        return ""
    return str(entry.get("fund_name") or "").strip()


def _amc_matches(isin: str, amc: str) -> bool:
    if not amc:
        return True
    try:
        from news_rag.fund_search import get_fund_index

        entry = get_fund_index().catalog_entry(isin) or {}
    except Exception:
        return False
    name = f"{entry.get('amc') or ''} {entry.get('fund_name') or ''}".lower()
    return amc.lower() in name


def fund_naming_clause(question: str) -> str:
    """The phrase that asked for fund names, not a later debt-vs-equity education clause."""
    m = re.search(
        r"(?:\btell\s+me\b|\bshow\s+me\b|\bname\b|\bgive\s+me\b).{0,80}?"
        r"(?:\d+\s+)?(?:debt|equity|hybrid)\s+funds?\b",
        question or "",
        re.I,
    )
    return m.group(0).strip() if m else ""


def rating_screen_question(user_question: str, focus_question: str) -> str:
    """Prefer the fund-naming clause when planner focus picked the wrong type."""
    user = (user_question or "").strip()
    focus = (focus_question or "").strip()
    clause = fund_naming_clause(user)
    if clause:
        return clause
    if not focus:
        return user
    user_types = match_all_fund_types(user)
    focus_types = match_all_fund_types(focus)
    if user_types and focus_types and user_types != focus_types:
        return user
    if explicit_fund_count(user) and user_types and not match_scheme_category(focus):
        return user
    return focus or user


def fetch_category_ratings(fund_type: str, category: str) -> dict[str, Any]:
    """One category. A failed call returns an empty payload so the walk can continue."""
    if not str(category or "").strip():
        return {"_error": "missing_category", "data": {"ratings": []}}
    key = (fund_type, category)
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < _CACHE_TTL_SEC:
            return deepcopy(hit[1])
    url = _RATING_URL.format(fund_type=quote(fund_type, safe=""), category=quote(category, safe=""))
    payload: dict[str, Any] = {}
    for attempt in range(2):
        try:
            from news_rag.rupeestop_auth import refresh_rupeestop_bearer_force

            headers = rupeestop_admin_request_headers(url)
            response = httpx.get(url, headers=headers, timeout=_HTTP_TIMEOUT)
            if response.status_code in (401, 403) and attempt == 0:
                body = (response.text or "").lower()
                if "expired" in body or "invalid" in body or response.status_code == 401:
                    refresh_rupeestop_bearer_force()
                    continue
            response.raise_for_status()
            payload = response.json()
            break
        except Exception as exc:
            logger.info("category rating skipped %s/%s: %s", fund_type, category, exc)
            if attempt == 0 and "403" in str(exc):
                from news_rag.rupeestop_auth import refresh_rupeestop_bearer_force

                refresh_rupeestop_bearer_force()
                continue
            return {"_error": str(type(exc).__name__), "data": {"ratings": []}}
    else:
        return {"_error": "auth", "data": {"ratings": []}}
    if not isinstance(payload, dict):
        return {}
    with _cache_lock:
        _cache[key] = (now, deepcopy(payload))
    return deepcopy(payload)


def _rows_from_payload(payload: dict[str, Any], *, fund_type: str, category: str) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    ratings = data.get("ratings") if isinstance(data, dict) else None
    if not isinstance(ratings, list):
        return []
    rows: list[dict[str, Any]] = []
    for raw in ratings:
        if not isinstance(raw, dict):
            continue
        row = _public_row(raw, fund_type=fund_type, category=category)
        if row is not None:
            rows.append(row)
    return rows


def _keep(row: dict[str, Any], spec: RatingScreenSpec, *, skip_label: bool = False) -> bool:
    if spec.amc and not _amc_matches(str(row.get("isin") or ""), spec.amc):
        return False
    if not skip_label and spec.label and str(row.get("rs_label") or "") != spec.label:
        return False
    if spec.min_score is not None:
        score = row.get("final_score")
        if score is None or float(score) < spec.min_score:
            return False
    return True


def _uses_label_cascade(spec: RatingScreenSpec) -> bool:
    if spec.return_window or spec.return_direction:
        return False
    if spec.min_score is not None or spec.highest_score:
        return False
    if spec.random_sample:
        return True
    if spec.count > 1 and (not spec.label or spec.label == "Best in category"):
        return True
    return False


def _cascade_labels_for_spec(spec: RatingScreenSpec) -> tuple[str, str]:
    from news_rag.fund_rating_labels import PREFERRED_PICK_MAX_TIER, normalize_rs_label

    explicit = normalize_rs_label(spec.label) if spec.label else ""
    if explicit and explicit != "Best in category":
        return explicit, explicit
    return "Best in category", PREFERRED_PICK_MAX_TIER


def _strip(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not str(key).startswith("_")}


def _price(rows: list[dict[str, Any]], window: str) -> list[dict[str, Any]]:
    from news_rag.tools import enrich_rankings_with_nav

    if not rows:
        return []
    enriched = enrich_rankings_with_nav(
        [_strip(row) | {"_trail_keep": row.get(f"_trail_{window}")} for row in rows],
        direction="any",
        top_n=len(rows),
        sort_by="exposure",
        return_window=window,
    )
    field = {"1Y": "return_1y_pct", "3Y": "return_3y_pct", "5Y": "return_5y_pct"}.get(window, "return_1y_pct")
    for row in enriched:
        row.pop("_trail_keep", None)
        row["_return"] = row.get(field)
    return enriched


def _shortlist(rows: list[dict[str, Any]], spec: RatingScreenSpec) -> list[dict[str, Any]]:
    key = f"_trail_{spec.return_window}"
    usable = [row for row in rows if row.get(key) is not None]
    if spec.return_direction == "positive":
        usable = [row for row in usable if float(row[key]) > 0][:_POSITIVE_CAP]
        return usable
    reverse = spec.return_direction != "lowest"
    usable.sort(key=lambda row: float(row[key]), reverse=reverse)
    return usable[:_SHORTLIST]


def _order(rows: list[dict[str, Any]], spec: RatingScreenSpec) -> list[dict[str, Any]]:
    pool = list(rows)
    if _uses_label_cascade(spec):
        start, max_tier = _cascade_labels_for_spec(spec)
        picked, _ = pick_funds_by_label_cascade(
            pool,
            spec.count,
            start_label=start,
            max_tier=max_tier,
            random_within_tier=False,
        )
        if picked:
            return picked
    if spec.return_window and spec.return_direction:
        pool.sort(key=lambda row: float(row.get("_return") or -10**9), reverse=spec.return_direction != "lowest")
        return pool
    pool.sort(key=lambda row: float(row.get("final_score") or -1), reverse=True)
    return pool


def rating_spec_for_forced_screen(
    question: str,
    *,
    top_n: int = 1,
    user_question: str = "",
) -> RatingScreenSpec | None:
    """When rating_screen is set but the question is not a rating-list phrase (e.g. holdings ask)."""
    full = (user_question or question or "").strip()
    balanced = balanced_portfolio_examples_spec(full)
    if balanced is not None:
        return balanced
    spec = parse_rating_screen(question)
    if spec is not None:
        return spec
    match = match_scheme_category(question or "")
    if not (match and match.locked and match.category):
        return None
    return RatingScreenSpec(
        count=max(1, min(int(top_n or 1), 20)),
        fund_type=match.fund_type or "equity",
        category=match.category,
        locked=True,
        label="Best in category",
        min_score=None,
        highest_score=False,
        return_window="",
        return_direction="",
        compare_category=False,
        random_sample=False,
        amc="",
        suggestion="rated",
        label_fallback="Recommended",
    )


def _alternate_row_excluded(
    row: dict[str, Any],
    exclude_isins: set[str],
    exclude_names: set[str],
) -> bool:
    isin = str(row.get("isin") or "").strip().upper()
    if isin and isin in exclude_isins:
        return True
    name = str(row.get("fund_name") or "").strip().lower()
    if not name or not exclude_names:
        return False
    for ex in exclude_names:
        if ex == name or name.startswith(ex) or ex.startswith(name):
            return True
    return False


def _rating_quality_sort_key(row: dict[str, Any]) -> tuple[int, float]:
    from news_rag.fund_rating_labels import tier_rank

    label = str(row.get("rs_label") or "")
    score = float(row.get("final_score") or -1)
    return (tier_rank(label), -score)


def pick_better_rated_fund_in_category(
    *,
    fund_type: str,
    category: str,
    exclude_isins: list[str] | None = None,
    exclude_names: list[str] | None = None,
    anchor_rs_label: str = "",
    anchor_rs_score: float | None = None,
    top_n: int = 1,
    question: str = "",
    fetch: Callable[[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Recommend by RupeeStop rating: upgrade first, else next-best by score in the category."""
    from news_rag.fund_rating_labels import is_higher_rated_than, normalize_rs_label

    loader = fetch or fetch_category_ratings
    exclude_isins_set = {str(x).strip().upper() for x in (exclude_isins or []) if str(x).strip()}
    exclude_names_set = {str(x).strip().lower() for x in (exclude_names or []) if str(x).strip()}
    anchor_label = normalize_rs_label(anchor_rs_label) or infer_anchor_label_from_excludes(list(exclude_isins_set))
    payload = loader(fund_type, category)
    rows = [
        row
        for row in _rows_from_payload(payload, fund_type=fund_type, category=category)
        if not _alternate_row_excluded(row, exclude_isins_set, exclude_names_set)
    ]
    if not rows:
        return {"success": False, "rankings": [], "ranking_note": "", "screen_type": "rs_rating"}

    upgrades = [
        row
        for row in rows
        if is_higher_rated_than(
            str(row.get("rs_label") or ""),
            row.get("final_score"),
            anchor_label,
            anchor_rs_score,
        )
    ]
    upgrades.sort(key=_rating_quality_sort_key)
    if upgrades:
        picked = upgrades[: max(1, int(top_n or 1))]
        note = (
            f"Higher RupeeStop rating than your current {category} holding"
            f" ({anchor_label or 'rated'} fund"
            + (f", score {float(anchor_rs_score):.1f}" if anchor_rs_score is not None else "")
            + ")."
        )
    else:
        rows.sort(key=_rating_quality_sort_key)
        picked = rows[: max(1, int(top_n or 1))]
        top = picked[0] if picked else {}
        note = (
            f"Your holding is already among the top-rated {category} names on our list; "
            f"showing the next best by RupeeStop score — "
            f"{top.get('rs_label') or 'rated'}"
            + (f" (score {float(top.get('final_score')):.1f})" if top.get("final_score") is not None else "")
            + ", which may be a lower label tier than what you hold."
        )

    public = [_strip(row) for row in picked]
    try:
        from news_rag.tools import _attach_screen_facts

        _attach_screen_facts(public, question)
    except Exception:
        logger.info("better-rated screen facts skipped", exc_info=True)

    return {
        "success": True,
        "screen_type": "rs_rating",
        "rankings": public,
        "ranking_note": note.strip(),
        "categories_called": [category],
        "priced_isins": [],
        "count": len(public),
        "return_window": "",
        "anchor_rs_label": anchor_label,
        "picked_rs_label": str((picked[0] if picked else {}).get("rs_label") or ""),
        "rating_pick_mode": "upgrade" if upgrades else "next_by_score",
    }


def infer_anchor_label_from_excludes(exclude_isins: list[str] | None) -> str:
    from news_rag.fund_rating_labels import normalize_rs_label
    from news_rag.fund_risk import fetch_public_rating

    for raw in exclude_isins or []:
        isin = str(raw or "").strip().upper()
        if not isin:
            continue
        rating = fetch_public_rating(isin)
        if not isinstance(rating, dict):
            continue
        label = normalize_rs_label(str(rating.get("label") or rating.get("rs_label") or ""))
        if label:
            return label
    return ""


def pick_alternate_funds_in_category(
    *,
    fund_type: str,
    category: str,
    exclude_isins: list[str] | None = None,
    exclude_names: list[str] | None = None,
    rs_label: str = "",
    top_n: int = 1,
    question: str = "",
    fetch: Callable[[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Another fund in the same scheme category, walking down RS label tiers if needed."""
    from news_rag.fund_rating_labels import is_lower_tier_than, label_tiers_from, normalize_rs_label

    loader = fetch or fetch_category_ratings
    exclude_isins_set = {str(x).strip().upper() for x in (exclude_isins or []) if str(x).strip()}
    exclude_names_set = {str(x).strip().lower() for x in (exclude_names or []) if str(x).strip()}
    anchor = normalize_rs_label(rs_label) or infer_anchor_label_from_excludes(list(exclude_isins_set))
    anchor_score = None
    if exclude_isins_set:
        payload_probe = loader(fund_type, category)
        all_rows = _rows_from_payload(payload_probe, fund_type=fund_type, category=category)
        for row in all_rows:
            isin = str(row.get("isin") or "").strip().upper()
            if isin and isin in exclude_isins_set:
                anchor_score = row.get("final_score")
                if not anchor:
                    anchor = normalize_rs_label(str(row.get("rs_label") or ""))
                break

    better = pick_better_rated_fund_in_category(
        fund_type=fund_type,
        category=category,
        exclude_isins=list(exclude_isins_set),
        exclude_names=list(exclude_names_set),
        anchor_rs_label=anchor,
        anchor_rs_score=float(anchor_score) if anchor_score is not None else None,
        top_n=top_n,
        question=question,
        fetch=loader,
    )
    if better.get("rankings"):
        return better

    payload = loader(fund_type, category)
    rows = [
        row
        for row in _rows_from_payload(payload, fund_type=fund_type, category=category)
        if not _alternate_row_excluded(row, exclude_isins_set, exclude_names_set)
    ]
    tiers = label_tiers_from(anchor or None)
    picked: list[dict[str, Any]] = []
    used_tier = ""
    for tier in tiers:
        tier_rows = [row for row in rows if str(row.get("rs_label") or "") == tier]
        tier_rows.sort(key=lambda row: float(row.get("final_score") or -1), reverse=True)
        if tier_rows:
            picked = tier_rows[: max(1, int(top_n or 1))]
            used_tier = tier
            break

    if not picked:
        return {"success": False, "rankings": [], "ranking_note": "", "screen_type": "rs_rating"}

    public = [_strip(row) for row in picked]
    try:
        from news_rag.tools import _attach_screen_facts

        _attach_screen_facts(public, question)
    except Exception:
        logger.info("alternate rating screen facts skipped", exc_info=True)

    note_parts: list[str] = []
    if anchor and used_tier and is_lower_tier_than(used_tier, anchor):
        note_parts.append(
            f"No other {anchor} fund in {category} after excluding the one already shown. "
            f"This pick is from the {used_tier} tier in the same category."
        )
    elif used_tier:
        note_parts.append(f"Another {used_tier} fund in {category}.")
    return {
        "success": True,
        "screen_type": "rs_rating",
        "rankings": public,
        "ranking_note": " ".join(note_parts).strip(),
        "categories_called": [category],
        "priced_isins": [],
        "count": len(public),
        "return_window": "",
        "anchor_rs_label": anchor,
        "picked_rs_label": used_tier,
    }


def pick_funds_by_label_cascade(
    rows: list[dict[str, Any]],
    top_n: int,
    *,
    start_label: str = "Best in category",
    max_tier: str = "Good Choice",
    exclude_isins: list[str] | None = None,
    exclude_names: list[str] | None = None,
    random_within_tier: bool = False,
) -> tuple[list[dict[str, Any]], str]:
    """Fill top_n across RS tiers: Best → Recommended → Good Choice (by default)."""
    from news_rag.fund_rating_labels import is_lower_tier_than, label_tiers_up_to, normalize_rs_label

    exclude_isins_set = {str(x).strip().upper() for x in (exclude_isins or []) if str(x).strip()}
    exclude_names_set = {str(x).strip().lower() for x in (exclude_names or []) if str(x).strip()}
    usable = [
        row
        for row in rows
        if isinstance(row, dict) and not _alternate_row_excluded(row, exclude_isins_set, exclude_names_set)
    ]
    start = normalize_rs_label(start_label) or "Best in category"
    cap = normalize_rs_label(max_tier) or "Good Choice"
    tiers = label_tiers_up_to(cap, start=start)
    picked: list[dict[str, Any]] = []
    seen_isins: set[str] = set()
    tier_notes: list[str] = []
    for tier in tiers:
        tier_rows = [row for row in usable if str(row.get("rs_label") or "") == tier]
        if random_within_tier and len(tier_rows) > 1:
            random.shuffle(tier_rows)
        else:
            tier_rows.sort(key=lambda row: float(row.get("final_score") or -1), reverse=True)
        before = len(picked)
        for row in tier_rows:
            isin = str(row.get("isin") or "").strip().upper()
            if isin and isin in seen_isins:
                continue
            picked.append(row)
            if isin:
                seen_isins.add(isin)
            if len(picked) >= top_n:
                break
        if len(picked) >= top_n:
            break
        if tier_rows and len(picked) > before and len(picked) < top_n:
            tier_notes.append(f"Added a {tier} fund; only one higher-tier name was available.")
    note = " ".join(tier_notes).strip()
    if start and picked and is_lower_tier_than(str(picked[0].get("rs_label") or ""), start):
        downgrade = (
            f"No {start} fund was available in this filter; showing a {picked[0].get('rs_label')} fund instead."
        )
        note = " ".join(part for part in (downgrade, note) if part).strip()
    return picked[: max(0, int(top_n or 1))], note


def pick_compare_pair_in_category(
    *,
    fund_type: str,
    category: str,
    question: str = "",
    fetch: Callable[[str, str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Two distinct funds in one category for compare — Best, then Recommended, then Good Choice."""
    loader = fetch or fetch_category_ratings
    payload = loader(fund_type, category)
    rows = _rows_from_payload(payload, fund_type=fund_type, category=category)
    if not rows:
        return {"success": False, "rankings": [], "ranking_note": "", "screen_type": "rs_rating"}

    picked, tier_note = pick_funds_by_label_cascade(rows, 2, max_tier="Good Choice")

    if len(picked) < 2:
        return {
            "success": False,
            "rankings": [_strip(row) for row in picked],
            "ranking_note": f"Only {len(picked)} rated fund(s) found in {category}.",
            "screen_type": "rs_rating",
            "categories_called": [category],
            "count": len(picked),
        }

    public = [_strip(row) for row in picked[:2]]
    try:
        from news_rag.tools import _attach_screen_facts

        _attach_screen_facts(public, question)
    except Exception:
        logger.info("compare pair rating screen facts skipped", exc_info=True)

    labels = [str(row.get("rs_label") or "") for row in public]
    note = (
        f"Compare pair in {category}: {public[0].get('fund_name', '')} ({labels[0]}) "
        f"and {public[1].get('fund_name', '')} ({labels[1]})."
    )
    if tier_note:
        note = f"{note} {tier_note}"
    return {
        "success": True,
        "screen_type": "rs_rating",
        "rankings": public,
        "ranking_note": note.strip(),
        "categories_called": [category],
        "priced_isins": [],
        "count": 2,
        "return_window": "",
        "compare_pair": True,
    }


def pick_rows_by_label_cascade(
    rows: list[dict[str, Any]],
    *,
    rs_label: str = "",
    exclude_isins: list[str] | None = None,
    exclude_names: list[str] | None = None,
    top_n: int = 1,
) -> tuple[list[dict[str, Any]], str]:
    """Catalog/NAV rows with rs_label attached — pick by tier walk."""
    from news_rag.fund_rating_labels import is_lower_tier_than, label_tiers_from, normalize_rs_label

    exclude_isins_set = {str(x).strip().upper() for x in (exclude_isins or []) if str(x).strip()}
    exclude_names_set = {str(x).strip().lower() for x in (exclude_names or []) if str(x).strip()}
    anchor = normalize_rs_label(rs_label) or infer_anchor_label_from_excludes(list(exclude_isins_set))
    usable = [
        row
        for row in rows
        if isinstance(row, dict) and not _alternate_row_excluded(row, exclude_isins_set, exclude_names_set)
    ]
    if int(top_n or 1) > 1:
        return pick_funds_by_label_cascade(
            usable,
            top_n,
            start_label=anchor or "Best in category",
            max_tier="Good Choice",
            exclude_isins=list(exclude_isins_set),
            exclude_names=list(exclude_names_set),
        )
    tiers = label_tiers_from(anchor or None)
    for tier in tiers:
        tier_rows = [row for row in usable if str(row.get("rs_label") or "") == tier]
        tier_rows.sort(key=lambda row: float(row.get("final_score") or -1), reverse=True)
        if tier_rows:
            picked = tier_rows[:1]
            note = ""
            if anchor and is_lower_tier_than(tier, anchor):
                note = (
                    f"No other {anchor} fund available; showing a {tier} fund "
                    f"(Good Choice and lower tiers are used when higher tiers are exhausted)."
                )
            return picked, note
    return [], ""


def run_rating_list(
    question: str,
    *,
    fetch: Callable[[str, str], dict[str, Any]] | None = None,
    price: Callable[[list[dict[str, Any]], str], list[dict[str, Any]]] | None = None,
    spec: RatingScreenSpec | None = None,
) -> dict[str, Any]:
    if spec is None:
        spec = parse_rating_screen(question)
    if spec is None:
        return {"success": False, "rankings": [], "ranking_note": ""}
    loader = fetch or fetch_category_ratings
    pricer = price or _price
    if spec.suggestion == "period":
        return _run_period_peer(spec, question, loader, pricer)
    result = _execute_rating_list(spec, question, loader, pricer)
    if result["rankings"] or not spec.label_fallback:
        return result
    from news_rag.fund_rating_labels import label_tiers_from, normalize_rs_label

    start = normalize_rs_label(spec.label) or normalize_rs_label(spec.label_fallback)
    tiers = label_tiers_from(start)[1:] if start else label_tiers_from("Best in category")[1:]
    prior_note = str(result.get("ranking_note") or "").strip()
    for tier in tiers:
        attempt = replace(spec, label=tier, label_fallback="")
        result = _execute_rating_list(attempt, question, loader, pricer)
        if result.get("rankings"):
            downgrade = (
                f"No {spec.label} fund was available in this filter; showing a {tier} fund instead."
                if spec.label and tier != spec.label
                else f"Showing a {tier} fund."
            )
            result["ranking_note"] = " ".join(part for part in (prior_note, downgrade) if part).strip()
            return result
    return result


def _load_category_payloads(
    loader: Callable[[str, str], dict[str, Any]],
    fund_type: str,
    names: list[str],
) -> dict[str, dict[str, Any]]:
    """Fetch a small category set together. One category stays on the calling thread."""
    if len(names) <= 1:
        return {name: loader(fund_type, name) for name in names}
    from concurrent.futures import ThreadPoolExecutor

    out: dict[str, dict[str, Any]] = {}
    workers = min(4, len(names))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(loader, fund_type, name): name for name in names}
        for future, name in futures.items():
            try:
                payload = future.result()
            except Exception:
                logger.info("category rating skipped %s/%s", fund_type, name, exc_info=True)
                payload = {}
            out[name] = payload if isinstance(payload, dict) else {}
    return out


_QUALITY_LABELS = ("Best in category", "Recommended", "Good Choice")


def _spread_quality(rows: list[dict[str, Any]], spec: RatingScreenSpec) -> list[dict[str, Any]]:
    """Take higher rating tiers first, and rotate categories so ETF and fund-of-funds both appear."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    order = list(spec.walk_categories) or []
    for row in rows:
        category = str(row.get("category") or "")
        grouped.setdefault(category, []).append(row)
        if category and category not in order:
            order.append(category)
    for category, bucket in grouped.items():
        bucket.sort(key=lambda item: float(item.get("final_score") or -1), reverse=True)
    picked: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _take(label: str) -> None:
        pending = {
            category: [row for row in grouped.get(category, []) if str(row.get("rs_label") or "") == label]
            for category in order
        }
        moved = True
        while moved and len(picked) < spec.count:
            moved = False
            for category in order:
                bucket = pending.get(category) or []
                while bucket:
                    row = bucket.pop(0)
                    isin = str(row.get("isin") or "")
                    if not isin or isin in seen:
                        continue
                    seen.add(isin)
                    picked.append(row)
                    moved = True
                    break
                if len(picked) >= spec.count:
                    return

    for label in _QUALITY_LABELS:
        if len(picked) >= spec.count:
            break
        _take(label)
    if len(picked) < spec.count:
        rest = [row for row in rows if str(row.get("isin") or "") not in seen]
        rest.sort(key=lambda item: float(item.get("final_score") or -1), reverse=True)
        for row in rest:
            isin = str(row.get("isin") or "")
            if not isin or isin in seen:
                continue
            seen.add(isin)
            picked.append(row)
            if len(picked) >= spec.count:
                break
    return picked[: spec.count]


def _best_rated_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """One fund: Best in category, else Recommended, else Good Choice, else highest score."""
    if not rows:
        return None
    order = ("Best in category", "Recommended", "Good Choice")
    for label in order:
        tier = [row for row in rows if str(row.get("rs_label") or "") == label]
        if tier:
            return max(tier, key=lambda row: float(row.get("final_score") or -1))
    return max(rows, key=lambda row: float(row.get("final_score") or -1))


def _execute_rating_list(
    spec: RatingScreenSpec,
    question: str,
    loader: Callable[[str, str], dict[str, Any]],
    pricer: Callable[[list[dict[str, Any]], str], list[dict[str, Any]]],
) -> dict[str, Any]:
    if spec.walk_category_pairs:
        steps: list[tuple[str, str]] = list(spec.walk_category_pairs)
    elif spec.walk_categories:
        steps = [(spec.fund_type, name) for name in spec.walk_categories]
    elif spec.locked:
        steps = [(spec.fund_type, spec.category)] if spec.category else []
    elif spec.walks:
        steps = [(spec.fund_type, name) for name in categories_for(spec.fund_type)]
    else:
        single = categories_for(spec.fund_type)[:1]
        steps = [(spec.fund_type, single[0])] if single else []
    picked: list[dict[str, Any]] = []
    seen: set[str] = set()
    called: list[str] = []
    priced: list[str] = []
    spread = spec.spread_categories or bool(spec.walk_category_pairs)
    payloads: dict[tuple[str, str], dict[str, Any]] = {}
    if spread:
        for fund_type, category in steps:
            payloads[(fund_type, category)] = loader(fund_type, category)

    for fund_type, category in steps:
        payload = payloads.get((fund_type, category), {}) if spread else loader(fund_type, category)
        if payload is None:
            payload = {}
        called.append(category)
        skip_label = spec.one_per_category or _uses_label_cascade(spec)
        rows = [
            row
            for row in _rows_from_payload(payload, fund_type=fund_type, category=category)
            if _keep(row, spec, skip_label=skip_label)
        ]
        if spec.return_window and spec.return_direction:
            if spec.return_direction in {"highest", "lowest"} and len(picked) >= spec.count:
                trail_key = f"_trail_{spec.return_window}"
                trails = [float(row[trail_key]) for row in rows if row.get(trail_key) is not None]
                if trails:
                    best_trail = min(trails) if spec.return_direction == "lowest" else max(trails)
                    worst = _nth_return(picked, spec.count, lowest=spec.return_direction == "lowest")
                    if worst is not None and (
                        (spec.return_direction == "lowest" and best_trail > worst)
                        or (spec.return_direction != "lowest" and best_trail < worst)
                    ):
                        continue
            short = _shortlist(rows, spec)
            priced.extend(str(row.get("isin") or "") for row in short)
            rows = pricer(short, spec.return_window)
            if spec.return_direction == "positive":
                rows = [row for row in rows if row.get("_return") is not None and float(row["_return"]) > 0]
        ordered = rows if spec.spread_categories else _order(rows, spec)
        if spec.one_per_category:
            chosen = _best_rated_row(rows)
            if chosen is not None:
                isin = str(chosen.get("isin") or "")
                if isin and isin not in seen:
                    seen.add(isin)
                    picked.append(chosen)
            continue
        for row in ordered:
            isin = str(row.get("isin") or "")
            if not isin or isin in seen:
                continue
            seen.add(isin)
            picked.append(row)
            if spec.spread_categories:
                continue
            if not spec.walks and not spec.highest_score and spec.return_direction not in {"highest", "lowest"}:
                if len(picked) >= spec.count:
                    break
        if spec.spread_categories:
            continue
        if spec.locked:
            break
        if spec.walks and spec.return_direction not in {"highest", "lowest"} and not spec.highest_score:
            if len(picked) >= spec.count:
                break

    if spec.one_per_category:
        pass
    elif spec.spread_categories:
        picked = _spread_quality(picked, spec)
    else:
        picked = _order(picked, spec)[: spec.count]
    public = [_strip(row) for row in picked]
    if spec.return_window and not spec.return_direction:
        public = [_strip(row) for row in pricer(public, spec.return_window)]
        priced.extend(str(row.get("isin") or "") for row in public)
    try:
        from news_rag.tools import _attach_screen_facts

        _attach_screen_facts(public, question)
    except Exception:
        logger.info("rating screen facts skipped", exc_info=True)
    _keep_asked_return(public, spec.return_window)
    _add_category_comparison(public, spec)
    note = _note(spec, len(public))
    return {
        "success": True,
        "screen_type": "rs_rating",
        "rankings": public,
        "ranking_note": note,
        "categories_called": called,
        "priced_isins": priced,
        "count": len(public),
        "return_window": spec.return_window,
    }


def _keep_asked_return(rows: list[dict[str, Any]], window: str) -> None:
    if not window:
        return
    from news_rag.tools import _RETURN_FIELDS

    keep = _RETURN_FIELDS.get(window, "")
    if not keep:
        return
    for row in rows:
        for key in list(row):
            if key.startswith("return_") and key != keep:
                row.pop(key, None)


def _add_category_comparison(rows: list[dict[str, Any]], spec: RatingScreenSpec) -> None:
    asked = spec.return_window or "1Y"
    pairs = {
        "1Y": ("return_1y_pct", "category_avg_1y_pct", "vs_category_1y_pct"),
        "3Y": ("return_3y_pct", "category_avg_3y_pct", "vs_category_3y_pct"),
        "5Y": ("return_5y_pct", "category_avg_5y_pct", "vs_category_5y_pct"),
    }
    fund_key, avg_key, vs_key = pairs.get(asked, ("", "", ""))
    for row in rows:
        if not spec.compare_category:
            for key in list(row):
                if key.startswith("category_avg_") or key.startswith("vs_category_"):
                    row.pop(key, None)
            continue
        for key in list(row):
            if key.startswith("category_avg_") and key != avg_key:
                row.pop(key, None)
        fund_return = row.get(fund_key)
        average = row.get(avg_key)
        if fund_return is None or average is None:
            continue
        row[vs_key] = round(float(fund_return) - float(average), 2)


def _nth_return(rows: list[dict[str, Any]], count: int, *, lowest: bool) -> float | None:
    values = [float(row["_return"]) for row in rows if row.get("_return") is not None]
    if len(values) < count:
        return None
    values.sort(reverse=not lowest)
    return values[count - 1]


def _note(spec: RatingScreenSpec, found: int) -> str:
    parts: list[str] = []
    if found < spec.count:
        if spec.locked:
            label = spec.label or spec.category
            parts.append(f"This category has {found} {label} fund(s). There are no more.")
        else:
            parts.append(f"Found {found} matching funds.")
    if spec.compare_category and spec.return_window:
        parts.append(
            f"The {spec.return_window} return is the fund's own NAV return. "
            "Category avg is that category's average. vs category is the difference."
        )
    if (spec.mix_note or "").strip():
        parts.append(spec.mix_note.strip())
    return " ".join(parts)


def rating_is_stronger(rated_score: Any, other_score: Any) -> bool:
    """The rated fund is the stronger rating only when its score is higher."""
    try:
        return float(rated_score) > float(other_score)
    except (TypeError, ValueError):
        return False


def _period_value(row: dict[str, Any], window: str) -> float | None:
    if row.get("_return") is not None:
        try:
            return float(row["_return"])
        except (TypeError, ValueError):
            return None
    trail = row.get(f"_trail_{window}")
    if trail is not None:
        try:
            return float(trail)
        except (TypeError, ValueError):
            return None
    return None


def _best_label(rows: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    matching = [row for row in rows if str(row.get("rs_label") or "") == label and row.get("final_score") is not None]
    if not matching:
        return None
    return max(matching, key=lambda row: float(row.get("final_score") or -1))


def _higher_pillars(rated: dict[str, Any], other: dict[str, Any]) -> list[str]:
    rated_pillars = rated.get("pillars") if isinstance(rated.get("pillars"), dict) else {}
    other_pillars = other.get("pillars") if isinstance(other.get("pillars"), dict) else {}
    names: list[str] = []
    for pillar in rated_pillars.values():
        if not isinstance(pillar, dict) or pillar.get("score") is None:
            continue
        label = str(pillar.get("label") or "")
        other_score = None
        for candidate in other_pillars.values():
            if isinstance(candidate, dict) and str(candidate.get("label") or "") == label:
                other_score = candidate.get("score")
                break
        if other_score is None:
            continue
        try:
            if float(pillar["score"]) > float(other_score):
                names.append(label)
        except (TypeError, ValueError):
            continue
    return names


def _run_period_peer(
    spec: RatingScreenSpec,
    question: str,
    loader: Callable[[str, str], dict[str, Any]],
    pricer: Callable[[list[dict[str, Any]], str], list[dict[str, Any]]],
) -> dict[str, Any]:
    """The period's performer, then the top-rated fund in that same category."""
    window = spec.return_window
    if spec.locked and spec.category:
        names = [spec.category]
    else:
        names = list(categories_for(spec.fund_type))
    called: list[str] = []
    performer: dict[str, Any] | None = None
    rated: dict[str, Any] | None = None
    category = ""
    for category_name in names:
        payload = loader(spec.fund_type, category_name)
        called.append(category_name)
        rows = _rows_from_payload(payload, fund_type=spec.fund_type, category=category_name)
        if window in {"1Y", "3Y", "5Y"}:
            ranked = [row for row in rows if _period_value(row, window) is not None]
        else:
            ranked = pricer(rows[:40], window)
            ranked = [row for row in ranked if _period_value(row, window) is not None]
        if spec.return_direction == "positive":
            ranked = [row for row in ranked if (_period_value(row, window) or 0) > 0]
        reverse = spec.return_direction != "lowest"
        ranked.sort(key=lambda row: _period_value(row, window) or 0, reverse=reverse)
        if not ranked:
            continue
        performer = ranked[0]
        rated = _best_label(rows, "Best in category") or _best_label(rows, "Recommended")
        category = category_name
        break
    if performer is None:
        return {
            "success": False,
            "screen_type": "rs_rating",
            "rankings": [],
            "ranking_note": "",
            "categories_called": called,
            "priced_isins": [],
            "count": 0,
            "return_window": window,
        }
    performer = ranked[0]
    rated = _best_label(rows, "Best in category") or _best_label(rows, "Recommended")
    public_performer = _strip(performer)
    public_performer["pick_role"] = "performance"
    public_performer["period_return"] = _period_value(performer, window)
    public_performer["period"] = window
    rankings = [public_performer]
    same = rated is not None and str(rated.get("isin") or "") == str(performer.get("isin") or "")
    if rated is not None and not same:
        public_rated = _strip(rated)
        public_rated["pick_role"] = "rating"
        public_rated["period_return"] = _period_value(rated, window)
        public_rated["period"] = window
        rankings.append(public_rated)
    elif same:
        public_performer["pick_role"] = "performance_and_rating"
    note_parts = []
    if category == "large cap" and "large cap" not in (question or "").lower() and "largecap" not in (question or "").lower():
        note_parts.append("The search was large cap.")
    if same or rated is None:
        note_parts.append("This fund leads the period and carries the rating label.")
    else:
        stronger = rating_is_stronger(rated.get("final_score"), performer.get("final_score"))
        if stronger:
            note_parts.append(
                "The period return is better for the performance fund. "
                "The rated fund has the stronger rating because its score is higher."
            )
        else:
            note_parts.append("The rated fund does not have the stronger rating.")
        higher = _higher_pillars(rated, performer)
        if higher:
            note_parts.append("Higher pillars on the rated fund: " + ", ".join(higher) + ".")
        performer_return = _period_value(performer, window)
        rated_return = _period_value(rated, window)
        if performer_return is not None and rated_return is not None and rated_return < performer_return and reverse:
            note_parts.append("The rated fund did not win this period.")
        if not reverse and performer_return is not None and rated_return is not None and rated_return > performer_return:
            note_parts.append("The rated fund did not have the weaker period return.")
    return {
        "success": True,
        "screen_type": "rs_rating",
        "rankings": rankings,
        "ranking_note": " ".join(note_parts),
        "categories_called": called,
        "priced_isins": [str(performer.get("isin") or "")],
        "count": len(rankings),
        "return_window": window,
    }


def rating_list_plan(question: str):
    from news_rag.insight.contracts import AnswerMode, ExecutionPlan, QueryClass, ToolCall, Wave2Policy

    spec = parse_rating_screen(question)
    count = spec.count if spec else 5
    return ExecutionPlan(
        intent="lookup",
        query_class=QueryClass.SIMPLE,
        answer_mode=AnswerMode.DATA_ONLY,
        funds=[],
        goal="Category RS rating list.",
        presentation_notes=(
            "Use the fund screen table. The RS label and score come from the API. "
            "A return column is the NAV-history return. "
            "If the note says the category has fewer funds, do not add more."
        ),
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"top_n": count, "rating_screen": True},
                why="Category RS rating screen.",
                required=True,
            )
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
        max_words=220,
        direct_reply="",
        confidence=0.98,
        routed_by="slot_router",
    )


def _followup_modules(question: str) -> list[str]:
    """Facts about the chosen fund that a rating row does not contain."""
    text = question or ""
    modules: list[str] = []
    if re.search(r"\b(?:historical|past)\s+returns?\b|\breturn\s+history\b", text, re.I):
        modules.append("return_series")
    if re.search(r"\brisk\s+analysis\b|\bhow\s+risky\b|\brisk\s+of\s+(?:the|this)\s+fund\b", text, re.I):
        modules.append("risk")
        from news_rag.fund_risk import include_drawdown_with_risk

        if include_drawdown_with_risk(text):
            modules.append("drawdown")
    return modules


def _keep_followup_plan(plan, spec: RatingScreenSpec, modules: list[str]) -> None:
    """The planner already covers later parts. Stamp the rating screen and keep them."""
    from news_rag.insight.contracts import AnswerMode, ToolCall

    screen = next((call for call in plan.tool_calls if call.tool == "screen_funds_by_exposure"), None)
    if screen is None:
        screen = ToolCall(
            tool="screen_funds_by_exposure",
            arguments={"top_n": spec.count, "rating_screen": True},
            why="Pick the rated fund, then load the later facts.",
            required=True,
        )
        plan.tool_calls = [screen, *plan.tool_calls]
    screen.arguments["rating_screen"] = True
    screen.arguments["top_n"] = spec.count
    if modules:
        plan.tool_calls = [call for call in plan.tool_calls if call.tool != "search_financial_news"]
        call = next((item for item in plan.tool_calls if item.tool == "get_fund_data"), None)
        if call is None:
            call = ToolCall(tool="get_fund_data", arguments={"modules": []}, wave=1)
            plan.tool_calls.append(call)
        call.wave = 1
        current = [str(name) for name in (call.arguments.get("modules") or [])]
        for name in modules:
            if name not in current:
                current.append(name)
        call.arguments["modules"] = current
        if "drawdown" in current and not call.arguments.get("periods"):
            call.arguments["periods"] = ["1y", "3y", "5y"]
    plan.concept_brief = ""
    plan.direct_reply = ""
    plan.requires_compose = True
    plan.answer_mode = AnswerMode.DATA_ONLY
    if (plan.max_words or 0) < 320:
        plan.max_words = 320
    note = (
        "Answer every part. Name the fund from the screen. "
        "Historical returns and the risk read come from the fund data."
    )
    if note not in (plan.presentation_notes or ""):
        plan.presentation_notes = f"{plan.presentation_notes} {note}".strip()


def _user_named_funds(question: str, funds: list[str]) -> list[str]:
    """Keep a scheme only when the user wrote its name. A category list must not invent one."""
    text = (question or "").lower()
    kept: list[str] = []
    skip = {"fund", "funds", "growth", "regular", "plan", "direct", "elss", "tax", "saver"}
    for name in funds:
        tokens = [
            word
            for word in re.findall(r"[a-z0-9]+", name.lower())
            if len(word) > 3 and word not in skip
        ]
        if tokens and any(word in text for word in tokens[:2]):
            kept.append(name)
    return kept


def _difference_brief(question: str) -> str:
    if not re.search(r"\b(?:different|difference|unlike|compared with|versus|vs)\b", question or "", re.I):
        return ""
    match = match_scheme_category(question)
    if match is None or not match.category:
        return ""
    notes = {
        "elss": (
            "ELSS is an equity fund with a lock-in of 3 years. "
            "The amount invested can be claimed under Section 80C, up to that section's limit. "
            "Other equity funds, such as large cap or flexi cap, do not have this lock-in and are not Section 80C products."
        ),
    }
    return notes.get(match.category, "")


def _apply_category_difference(question: str, plan) -> None:
    brief = _difference_brief(question)
    if not brief:
        return
    plan.concept_brief = brief
    plan.requires_compose = True
    plan.direct_reply = ""
    plan.funds = _user_named_funds(question, list(plan.funds or []))
    if (plan.max_words or 0) < 220:
        plan.max_words = 220
    note = "Name the funds from the screen when it has them. Then explain the difference from the concept brief."
    if note not in (plan.presentation_notes or ""):
        plan.presentation_notes = f"{plan.presentation_notes} {note}".strip()


def ensure_quality_fund_list(question: str, plan) -> None:
    """Unnamed random or gold/silver lists use the category rating API, not a sector scan."""
    from news_rag.insight.contracts import AnswerMode, ToolCall

    if any(call.tool == "compare_funds" for call in plan.tool_calls or []):
        return
    if any((call.arguments or {}).get("compare_pair") for call in plan.tool_calls or []):
        return
    spec = parse_rating_screen(question)
    if spec is None or spec.suggestion == "period":
        return
    if not spec.walk_categories and not spec.random_sample:
        return
    screen = next((call for call in plan.tool_calls or [] if call.tool == "screen_funds_by_exposure"), None)
    if screen is None and not spec.walk_categories:
        return
    if spec.walk_categories:
        plan.funds = []
        plan.sectors = []
        plan.tool_calls = [
            call
            for call in (plan.tool_calls or [])
            if call.tool not in ("get_market_snapshot", "get_fund_data", "screen_funds_by_exposure")
        ]
    elif screen is None:
        plan.tool_calls = list(plan.tool_calls or [])
    else:
        plan.tool_calls = [call for call in plan.tool_calls if call.tool != "screen_funds_by_exposure"]
    plan.random_fund_count = 0
    plan.random_fund_name_contains = ""
    plan.tool_calls = [
        ToolCall(
            tool="screen_funds_by_exposure",
            arguments={
                "rating_screen": True,
                "top_n": spec.count,
                "focus_question": " ".join((question or "").split())[:180],
                "random_sample": bool(spec.random_sample),
                "sector": "",
                "driver": "",
            },
            why="Category RS rating list for an unnamed fund ask.",
            required=True,
        ),
        *plan.tool_calls,
    ]
    plan.direct_reply = ""
    plan.requires_compose = True
    plan.answer_mode = AnswerMode.DATA_ONLY
    if spec.walk_categories:
        listed = ", ".join(spec.walk_categories)
        note = (
            f"Name funds only from these scheme categories: {listed}. "
            "They are gold or silver ETFs and fund-of-funds, including ETF fund of funds. "
            "Prefer Best in category, then Recommended, then Good Choice. "
            "Do not name an equity fund, a generic index ETF, or the metal's spot price."
        )
    else:
        note = (
            "Name the funds from the RupeeStop rating screen. "
            "Prefer Best in category, then Recommended, then Good Choice."
        )
    if note not in (plan.presentation_notes or ""):
        plan.presentation_notes = f"{plan.presentation_notes} {note}".strip()


def ensure_rating_screen(question: str, plan, memory: dict[str, Any] | None = None) -> None:
    """A rating list uses the category API. Later facts about that fund stay on the plan."""
    from news_rag.insight.contracts import AnswerMode
    from news_rag.insight.plan_intent import plan_wants_alternate_in_category
    from news_rag.insight.planner_policy import planner_owns

    if str(getattr(plan, "data_need", "") or "") == "portfolio_allocation":
        return

    if planner_owns(plan):
        spec = parse_rating_screen(question)
        if spec is not None and spec.suggestion:
            _install_suggestion_screen(plan, spec, question)
            return
        _apply_category_difference(question, plan)
        spec = parse_rating_screen(question)
        if spec is None:
            return
        for call in plan.tool_calls:
            if call.tool == "screen_funds_by_exposure":
                call.arguments["rating_screen"] = True
                call.arguments["top_n"] = spec.count
                if spec.random_sample:
                    call.arguments["random_sample"] = False
        return
    if plan_wants_alternate_in_category(plan):
        return
    if getattr(plan, "intent", "") == "explain_cause":
        return
    if getattr(plan, "answer_mode", None) == AnswerMode.INSIGHT_FUSION:
        return
    spec = parse_rating_screen(question)
    if spec is not None and spec.suggestion:
        _install_suggestion_screen(plan, spec, question)
        return
    if (getattr(plan, "routed_by", "") or "") == "planner":
        _apply_category_difference(question, plan)
        spec = parse_rating_screen(question)
        if spec is None:
            return
        for call in plan.tool_calls:
            if call.tool == "screen_funds_by_exposure":
                call.arguments["rating_screen"] = True
                call.arguments["top_n"] = spec.count
        return
    spec = parse_rating_screen(question)
    if spec is None:
        _apply_category_difference(question, plan)
        return
    from news_rag.insight.contracts import AnswerMode, ToolCall

    follow = _followup_modules(question)
    others = [call for call in plan.tool_calls if call.tool != "screen_funds_by_exposure"]
    if follow or ((plan.routed_by or "") == "planner" and (others or len(plan.sub_queries) > 1)):
        _keep_followup_plan(plan, spec, follow)
    else:
        plan.funds = []
        plan.direct_reply = ""
        plan.concept_brief = ""
        plan.answer_mode = AnswerMode.DATA_ONLY
        plan.requires_compose = False
        plan.tool_calls = [
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"top_n": spec.count, "rating_screen": True},
                why="Category RS rating screen.",
                required=True,
            )
        ]
    _apply_category_difference(question, plan)


def _install_suggestion_screen(plan, spec: RatingScreenSpec, question: str = "") -> None:
    """Use the rating screen and drop a sector the user did not name."""
    from news_rag.insight.contracts import AnswerMode, ToolCall

    screen = next((call for call in plan.tool_calls if call.tool == "screen_funds_by_exposure"), None)
    if screen is None:
        screen = ToolCall(
            tool="screen_funds_by_exposure",
            arguments={},
            why="Rated fund suggestion.",
            required=True,
        )
        plan.tool_calls = [screen, *plan.tool_calls]
    args = dict(screen.arguments or {})
    args["sector"] = ""
    args["driver"] = ""
    args["focus_question"] = " ".join((question or "").split())[:180]
    args["return_window"] = spec.return_window
    args["rating_screen"] = True
    args["top_n"] = spec.count
    args["random_sample"] = bool(spec.random_sample)
    screen.arguments = args
    plan.direct_reply = ""
    plan.requires_compose = True
    plan.answer_mode = AnswerMode.DATA_ONLY
    if spec.suggestion == "period":
        note = (
            "Name the period performer and the rated fund in the same category. "
            "Call the rated fund the stronger rating only when its score is higher. "
            "Do not say you cannot recommend a fund. Do not tell the reader to buy."
        )
    elif spec.walk_category_pairs:
        note = (
            f"{(spec.mix_note or '').strip()} "
            "List **one fund per category** from EVIDENCE only — never invent schemes. "
            "For each fund: name, **RupeeStop score (out of 100)**, **RS label** "
            "(Best in category / Recommended / Good Choice), and its **role** "
            "(e.g. large-cap core, debt stability, gold hedge). "
            "Open with **diversification** and **stability** (debt + conservative hybrid). "
            "Use 5Y return only as context when present; the rating is why each name appears."
        )
    else:
        note = (
            "Lead with the fund we surface from RupeeStop ratings (Best in category, else Recommended). "
            "State the RupeeStop score out of 100 and the label. "
            "You may add one recent return from the data if present, but the rating is the reason we named this fund. "
            "Do not say you cannot recommend a fund. Do not tell the reader to buy."
        )
    if note not in (plan.presentation_notes or ""):
        plan.presentation_notes = f"{plan.presentation_notes} {note}".strip()
