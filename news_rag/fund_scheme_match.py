"""Whether natural-language text names a specific scheme — AMC + distinctive tokens from the catalog."""

from __future__ import annotations

import difflib
import re

from news_rag.fund_catalog import is_quant_amc_entry, is_quantum_amc_entry
from news_rag.fund_search import _amc_hints_from_tokens, _needles_for_amc_hint, _normalize_fund_text

# Generic scheme / plan words — not enough alone to pick one fund within an AMC.
SCHEME_MATCH_SKIP = frozenset(
    {
        "fund",
        "funds",
        "growth",
        "regular",
        "plan",
        "direct",
        "elss",
        "tax",
        "saver",
        "equity",
        "debt",
        "hybrid",
        "minimum",
        "maximum",
        "redemption",
        "redeem",
        "period",
        "load",
        "exit",
        "settlement",
        "systematic",
        "option",
        "variance",
        "index",
        "cap",
        "large",
        "small",
        "mid",
        "flexi",
        "multi",
        "about",
        "tell",
        "show",
        "what",
        "when",
        "who",
        "manager",
        "managers",
        "detail",
        "details",
        "nav",
        "xirr",
        "aum",
        "sip",
        "expense",
        "returns",
        "return",
        "benchmark",
        "rating",
        "risk",
        "year",
        "years",
        "month",
        "months",
        "week",
        "weeks",
        "day",
        "days",
        "annual",
        "quarter",
        "quarterly",
        "tenure",
        "doing",
        "going",
        "performance",
        "analysis",
        "compare",
        "comparison",
        "news",
        "sector",
        "sectors",
        "holding",
        "holdings",
    }
)

_AMC_FUZZY_BLOCK = frozenset(
    {
        "assets",
        "asset",
        "ideal",
        "categories",
        "category",
        "portfolio",
        "portfolios",
        "allocation",
        "holdings",
        "holding",
    }
)

_SHORT_SCHEME_TOKENS = frozenset({"elss", "psu", "etf", "fof", "nav", "sip"})

_EXTRA_SCHEME_VOCAB = frozenset(
    {
        "contra",
        "value",
        "dividend",
        "momentum",
        "quant",
        "focus",
        "focused",
        "opportunities",
        "bluechip",
        "shariah",
        "infra",
        "pharma",
        "banking",
        "defence",
        "defense",
        "thematic",
        "technology",
        "consumption",
        "manufacturing",
        "innovation",
        "business",
        "cycle",
        "esg",
        "alpha",
        "income",
        "credit",
        "gilt",
        "overnight",
        "corporate",
        "floater",
        "arbitrage",
        "children",
        "retirement",
        "nifty",
        "sensex",
        "bank",
        "energy",
        "power",
        "gold",
        "silver",
        "liquid",
        "variance",
        "minimum",
        "opportunity",
        "opportunit",
        "special",
        "opportunities",
        "advantage",
        "dynamic",
        "balanced",
        "hybrid",
        "savings",
    }
)


_VOCAB_STOP = frozenset(
    {
        "and",
        "the",
        "for",
        "domestic",
        "funds",
        "fund",
        "of",
        "in",
        "on",
        "to",
        "or",
        "by",
        "with",
        "from",
        "other",
        "others",
        "oriented",
        "solution",
    }
)


def _scheme_vocab_tokens() -> frozenset[str]:
    from news_rag.fund_rating_categories import CATEGORIES

    vocab: set[str] = set(_EXTRA_SCHEME_VOCAB)
    for phrases in CATEGORIES.values():
        for phrase in phrases:
            for tok in re.findall(r"[a-z0-9]+", (phrase or "").lower()):
                if tok in SCHEME_MATCH_SKIP or tok in _VOCAB_STOP:
                    continue
                if len(tok) > 3 or tok in _SHORT_SCHEME_TOKENS:
                    vocab.add(tok)
    return frozenset(vocab)


def amc_token_in_question(token: str, amc_tokens: set[str]) -> str:
    if token in _AMC_FUZZY_BLOCK:
        return ""
    if token in amc_tokens:
        return token
    if len(token) < 5:
        return ""
    hits = difflib.get_close_matches(token, list(amc_tokens), n=1, cutoff=0.8)
    if not hits:
        return ""
    match = hits[0]
    if match in _AMC_FUZZY_BLOCK:
        return ""
    return match


def question_amc_hints(question: str) -> list[str]:
    from news_rag.insight.brief import _amc_token_set

    tokens = re.findall(r"[a-z0-9]+", (question or "").lower())
    hints = _amc_hints_from_tokens(tokens)
    amc_tokens = _amc_token_set()
    for tok in tokens:
        canon = amc_token_in_question(tok, amc_tokens)
        if canon and canon not in hints:
            hints.append(canon)
    return [h for h in dict.fromkeys(hints) if h not in _AMC_FUZZY_BLOCK]


def _prune_distinctive_constraints(constraints: list[str]) -> list[str]:
    """Drop standalone 'mid cap' / 'large cap' when the question locked large & mid cap."""
    normed = {c.strip().lower() for c in constraints}
    if not any("large" in b and "mid" in b for b in normed):
        return list(dict.fromkeys(constraints))
    drop = {"mid cap", "large cap"}
    return [c for c in constraints if c.strip().lower() not in drop]


def _category_phrases_in_question(question: str) -> list[str]:
    from news_rag.fund_rating_categories import _CATEGORY_ALIASES, _phrase_in

    text = (question or "").strip().lower()
    if not text:
        return []
    found: list[str] = []
    matched_phrases: list[str] = []
    for phrase, _fund_type, _category in _CATEGORY_ALIASES:
        p = (phrase or "").strip().lower()
        if not p or len(p) < 3:
            continue
        if not _phrase_in(p, text):
            continue
        if any(p != longer and p in longer for longer in matched_phrases):
            continue
        matched_phrases.append(p)
        if p not in found:
            found.append(p)
    return found


def _scheme_name_tokens(fund_name: str) -> list[str]:
    return [
        w
        for w in re.findall(r"[a-z0-9]+", (fund_name or "").lower())
        if (len(w) > 3 or w in _SHORT_SCHEME_TOKENS) and w not in SCHEME_MATCH_SKIP
    ]


_PERIOD_PHRASE_RE = re.compile(
    r"\b\d+[\s\-]*(year|years|month|months|week|weeks|day|days)\b"
    r"|\b(?:1y|3y|5y|6m|3m|1m|1w|ytd)\b",
    re.I,
)


def _text_for_vocab_constraints(question: str) -> str:
    """Drop return-window phrases so '1-year' does not surface a bogus 'year' constraint."""
    scrubbed = _PERIOD_PHRASE_RE.sub(" ", question or "")
    return re.sub(r"\s+", " ", scrubbed).strip().lower()


def _scheme_flavor_penalty(question: str, fund_name: str) -> int:
    """Down-rank schemes whose name adds global/overseas/fof flavour the user did not say."""
    q = (question or "").lower()
    name = (fund_name or "").lower()
    penalty = 0
    for token in (
        "global",
        "overseas",
        "international",
        "world",
        "offshore",
        "fof",
        "fund of fund",
    ):
        if token in name and token not in q:
            penalty += 3
    if re.search(r"\bemerging\s+equity\b", q):
        if re.search(r"\bemerging\s+equity\b", name.replace("-", " ")):
            penalty -= 4
    return penalty


def _distinctive_constraints(question: str) -> list[str]:
    """Category phrases and catalog scheme-flavour tokens — not free English from the sentence."""
    text = (question or "").strip().lower()
    vocab_text = _text_for_vocab_constraints(question)
    if not text:
        return []
    constraints: list[str] = list(_category_phrases_in_question(question))
    vocab = _scheme_vocab_tokens()
    for word in sorted(vocab, key=len, reverse=True):
        if word in constraints or word in SCHEME_MATCH_SKIP:
            continue
        if re.search(rf"\b{re.escape(word)}\b", vocab_text):
            constraints.append(word)
    return _prune_distinctive_constraints(list(dict.fromkeys(constraints)))


def _scheme_matches_amc(question: str, fund_name: str) -> bool:
    hints = question_amc_hints(question)
    if not hints:
        return True
    name_lower = (fund_name or "").lower()
    name_norm = _normalize_fund_text(fund_name)
    blob = f"{name_norm} {name_lower}"
    for hint in hints:
        if hint == "quant":
            others = [h for h in hints if h != "quant"]
            if others:
                if re.search(r"\bquant\b", name_lower) and not name_lower.startswith("quantum"):
                    return True
                continue
            if is_quant_amc_entry(amc_header="", fund_name=fund_name):
                return True
            if re.search(r"\bquant\b", name_lower) and not name_lower.startswith("quantum"):
                return True
        if hint == "quantum":
            if is_quantum_amc_entry(amc_header="", fund_name=fund_name) or "quantum" in name_lower:
                return True
            continue
        if re.search(rf"\b{re.escape(hint)}\b", name_lower):
            return True
        for needle in _needles_for_amc_hint(hint):
            if needle and needle.lower() in blob:
                return True
    return False


def _constraint_in_scheme_name(constraint: str, fund_name: str) -> bool:
    c = (constraint or "").strip().lower()
    if not c:
        return True
    name_lower = fund_name.lower()
    name_norm = _normalize_fund_text(fund_name)
    cnorm = _normalize_fund_text(c)
    if cnorm in name_norm or c in name_lower:
        return True
    words = [w for w in cnorm.split() if w and w not in SCHEME_MATCH_SKIP]
    if words and all(w in name_norm for w in words):
        return True
    return False


def user_text_names_scheme(question: str, fund_name: str) -> bool:
    """True when question text targets this scheme, not just its AMC."""
    text = (question or "").strip()
    name = (fund_name or "").strip()
    if not text or not name:
        return False
    if not _scheme_matches_amc(question, name):
        return False

    constraints = _distinctive_constraints(question)
    if constraints:
        return all(_constraint_in_scheme_name(c, name) for c in constraints)

    if question_amc_hints(question) and not constraints:
        return True

    fund_tokens = _scheme_name_tokens(name)
    if not fund_tokens:
        return False
    text_lower = text.lower()
    hits = sum(1 for t in fund_tokens if re.search(rf"\b{re.escape(t)}\b", text_lower))
    return hits >= 2


def scheme_match_score(question: str, fund_name: str) -> tuple[int, int, int, int]:
    """Higher is better: (constraint_fit, token_overlap, flavor_penalty, name_length)."""
    if not user_text_names_scheme(question, fund_name):
        return (-1, 0, 0, 0)
    text_lower = (question or "").lower()
    constraints = _distinctive_constraints(question)
    constraint_fit = len(constraints)
    if constraints:
        constraint_fit = sum(1 for c in constraints if _constraint_in_scheme_name(c, fund_name))
    tokens = list(dict.fromkeys(_scheme_name_tokens(fund_name)))
    token_hits = sum(1 for t in tokens if re.search(rf"\b{re.escape(t)}\b", text_lower))
    extra_in_name = sum(1 for t in tokens if not re.search(rf"\b{re.escape(t)}\b", text_lower))
    penalty = _scheme_flavor_penalty(question, fund_name)
    return (constraint_fit, token_hits, -penalty, -extra_in_name, -len(fund_name))


def pick_best_matching_scheme(question: str, candidates: list[str]) -> str:
    best = ""
    best_score = (-1, 0, 0, 0)
    for raw in candidates:
        name = str(raw or "").strip()
        if not name:
            continue
        score = scheme_match_score(question, name)
        if score > best_score:
            best_score = score
            best = name
    return best


def question_resolves_to_canonical_fund(question: str) -> str:
    """Unambiguous catalog name from the user question (no planner, no chat)."""
    from news_rag.fund_search import lookup_extracted_fund, prefer_resolved_fund_name, resolve_fund_from_question

    detail, ambiguous, close = resolve_fund_from_question(question)
    if detail and not ambiguous:
        shown = prefer_resolved_fund_name(detail, detail)
        name = str(shown.get("fund_name") or detail.get("fund_name") or "").strip()
        if name and user_text_names_scheme(question, name):
            return name
        return ""
    if ambiguous and close:
        if not _distinctive_constraints(question):
            return ""
        pick = pick_best_matching_scheme(question, close)
        if pick and user_text_names_scheme(question, pick):
            detail2, amb2, _ = lookup_extracted_fund(name=pick)
            if detail2 and not amb2:
                shown = prefer_resolved_fund_name(detail2, detail2)
                return str(shown.get("fund_name") or detail2.get("fund_name") or pick).strip()
    return ""


def catalog_fund_matches_question(question: str, fund_name: str) -> bool:
    """True when the fund is what the question resolves to, or explicit scheme tokens match."""
    name = str(fund_name or "").strip()
    if not name:
        return False
    if user_text_names_scheme(question, name):
        return True
    resolved = question_resolves_to_canonical_fund(question)
    if not resolved:
        return False
    from news_rag.fund_search import lookup_extracted_fund

    r_detail, r_amb, _ = lookup_extracted_fund(name=resolved)
    c_detail, c_amb, _ = lookup_extracted_fund(name=name)
    if (
        r_detail
        and c_detail
        and not r_amb
        and not c_amb
        and str(r_detail.get("isin") or "").upper() == str(c_detail.get("isin") or "").upper()
    ):
        return True
    return _normalize_fund_text(resolved) == _normalize_fund_text(name)
