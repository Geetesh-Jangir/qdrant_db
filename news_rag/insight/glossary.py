"""Short direct answers for finance glossary / acronym questions (no tools, no long compose)."""

from __future__ import annotations

import re

from news_rag.insight.contracts import (
    AnswerMode,
    ExecutionPlan,
    QueryClass,
    ScopeKind,
    Wave2Policy,
)

_TERM_ALIASES: dict[str, str] = {
    "nav": "nav",
    "net asset value": "nav",
    "sip": "sip",
    "stp": "stp",
    "swp": "swp",
    "elss": "elss",
    "etf": "etf",
    "amc": "amc",
    "aum": "aum",
    "ter": "ter",
    "expense ratio": "ter",
    "idcw": "idcw",
    "idc": "idcw",
    "nfo": "nfo",
    "sebi": "sebi",
    "amfi": "amfi",
    "nse": "nse",
    "bse": "bse",
}

_REPLIES: dict[str, str] = {
    "nav": "NAV stands for **Net Asset Value** — the per-unit price of a mutual fund scheme.",
    "sip": "SIP stands for **Systematic Investment Plan** — investing a fixed amount in a fund at regular intervals.",
    "stp": "STP stands for **Systematic Transfer Plan** — moving money periodically from one scheme to another within the same AMC.",
    "swp": "SWP stands for **Systematic Withdrawal Plan** — redeeming a fixed amount from a fund at regular intervals.",
    "elss": "ELSS stands for **Equity Linked Savings Scheme** — a tax-saving equity mutual fund with a lock-in under Section 80C.",
    "etf": "ETF stands for **Exchange Traded Fund** — a fund that trades on the stock exchange like a share.",
    "amc": "AMC stands for **Asset Management Company** — the company that manages mutual fund schemes.",
    "aum": "AUM stands for **Assets Under Management** — the total market value of investments a fund or AMC manages.",
    "ter": "TER is the **Total Expense Ratio** — the annual fee charged by a mutual fund, expressed as a percentage of assets.",
    "idcw": "IDCW stands for **Income Distribution cum Capital Withdrawal** — payouts from a mutual fund (formerly often called dividend options).",
    "nfo": "NFO stands for **New Fund Offer** — when a mutual fund scheme is launched and opens for first subscriptions.",
    "sebi": "SEBI is the **Securities and Exchange Board of India** — the regulator for securities markets and mutual funds in India.",
    "amfi": "AMFI is the **Association of Mutual Funds in India** — the industry body for mutual funds in India.",
    "nse": "NSE is the **National Stock Exchange** — a major stock exchange in India.",
    "bse": "BSE is the **Bombay Stock Exchange** — a major stock exchange in India.",
}

_FULL_FORM_RE = re.compile(
    r"\b(?:what\s+is\s+the\s+)?(?:full\s+form|expanded\s+form|expansion)\s+of\s+(.+?)\s*\??\s*$",
    re.I,
)
_STANDS_FOR_RE = re.compile(
    r"\bwhat\s+(?:does|do)\s+(.+?)\s+stand\s+for\s*\??\s*$",
    re.I,
)
_MEANING_RE = re.compile(
    r"\b(?:what\s+is\s+the\s+)?(?:meaning|definition)\s+of\s+(.+?)\s*\??\s*$",
    re.I,
)
_SHORT_WHAT_IS_RE = re.compile(r"^what\s+is\s+(.+?)\s*\??\s*$", re.I)


def _normalize_term(raw: str) -> str | None:
    t = re.sub(r"[^\w\s]", "", (raw or "").lower()).strip()
    t = re.sub(r"\s+", " ", t)
    if not t:
        return None
    for prefix in ("the ", "a ", "an "):
        if t.startswith(prefix) and t[len(prefix):] in _TERM_ALIASES:
            t = t[len(prefix):]
            break
    if t in _TERM_ALIASES:
        return _TERM_ALIASES[t]
    if t in _REPLIES:
        return t
    # single token acronym
    if " " not in t and len(t) <= 8 and t in _REPLIES:
        return t
    return _TERM_ALIASES.get(t)


_SECOND_PART_RE = re.compile(
    r"\bwhat\s+does\b.+\bmeans?\b|"
    r"\bwhat\s+is\s+meant\s+by\b|"
    r"\bmeaning\s+of\b|"
    r"\b(?:and|also)\b.{0,80}\b(?:why|explain|how)\b",
    re.I,
)
_WHAT_DOES_MEAN_RE = re.compile(r"\bwhat\s+does\s+(.+?)\s+means?\b", re.I)


def has_second_part(question: str) -> bool:
    """A figure plus a meaning, or a later why or explain, is more than one question."""
    return bool(_SECOND_PART_RE.search(question or ""))


def meaning_reply(question: str) -> str:
    """The glossary line for a 'what does this mean' clause, including a small misspelling."""
    match = _WHAT_DOES_MEAN_RE.search(question or "")
    if not match:
        return ""
    raw = re.sub(r"\s+", " ", match.group(1).lower()).strip()
    raw = raw.replace("ration", "ratio")
    if "expense" in raw:
        return _REPLIES["ter"]
    key = _normalize_term(raw)
    if key and key in _REPLIES:
        return _REPLIES[key]
    return ""


def extract_glossary_term(question: str) -> str | None:
    q = (question or "").strip()
    if not q:
        return None
    for pat in (_FULL_FORM_RE, _STANDS_FOR_RE, _MEANING_RE):
        m = pat.search(q)
        if m:
            return _normalize_term(m.group(1))
    m = _SHORT_WHAT_IS_RE.match(q)
    if m:
        return _normalize_term(m.group(1))
    return None


def asks_precise_definition(question: str) -> bool:
    """Glossary / acronym ask with no fund lookup — answer should be one line, not an essay."""
    q = (question or "").strip()
    if not q:
        return False
    if re.search(r"\b(?:nav|price|return|performance)\s+of\b", q, re.I):
        return False
    if _FULL_FORM_RE.search(q) or _STANDS_FOR_RE.search(q) or _MEANING_RE.search(q):
        return True
    key = extract_glossary_term(q)
    if key and key in _REPLIES and _SHORT_WHAT_IS_RE.match(q):
        return True
    try:
        from news_rag.domain_intake import question_mentions_fund_scheme

        if question_mentions_fund_scheme(q):
            return False
    except Exception:
        pass
    return False


def direct_glossary_reply(question: str) -> str | None:
    key = extract_glossary_term(question)
    if not key:
        return None
    return _REPLIES.get(key)


def glossary_execution_plan(question: str) -> ExecutionPlan | None:
    reply = direct_glossary_reply(question)
    if not reply:
        return None
    return ExecutionPlan(
        scope_kind=ScopeKind.IN_SCOPE,
        goal="Answer the acronym or definition asked",
        intent="lookup",
        answer_mode=AnswerMode.DATA_ONLY,
        query_class=QueryClass.SIMPLE,
        can_answer_directly=True,
        direct_reply=reply,
        tool_calls=[],
        wave_2_policy=Wave2Policy(trigger="none"),
        response_shape="short_answer",
        max_words=35,
        presentation_notes="One sentence only. No extra sections.",
        routed_by="slot_router",
        confidence=0.99,
    )
