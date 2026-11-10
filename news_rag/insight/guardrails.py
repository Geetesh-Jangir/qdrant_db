"""Deterministic pre-planner guards. A match costs no LLM call.

Order matters: internals, advice, gibberish, then the "<unknown thing> fund" trap.
"""

from __future__ import annotations

import difflib
import re

from news_rag.insight.greeting import CAPABILITIES_REPLY

INTERNALS_REPLY = (
    "I can't share how I work internally. I can help with funds, your portfolio, and market news."
)
APP_RECOMMENDATION_REPLY = (
    "For personalised recommendations, please visit our app. "
    "I can share facts such as returns, holdings, ratings and news for any fund."
)

EXAMPLES = (
    "- A fund's NAV, returns, rating or risk (e.g. \"1 year return of HDFC Large Cap Fund\")\n"
    "- What a fund holds (e.g. \"top 5 holdings of Axis Bluechip\")\n"
    "- Comparing funds, or your own portfolio (e.g. \"one month return of my funds\")\n"
    "- Market news and how it affects sectors and funds"
)
NOT_UNDERSTOOD_REPLY = "I didn't get what you are asking. You can ask me about:\n" + EXAMPLES
UNKNOWN_FUND_REPLY = (
    "I couldn't find a fund called \"{phrase}\". Please check the name, or ask about:\n" + EXAMPLES
)
GIBBERISH_REPLY = CAPABILITIES_REPLY

_INTERNALS_RE = re.compile(
    r"\b(?:system\s+(?:prompt|message|instructions?)|your\s+(?:prompt|instructions?|rules|tools?|code)|"
    r"(?:show|reveal|print|repeat)\s+(?:me\s+)?(?:your|the)\s+(?:prompt|instructions?)|"
    r"ignore\s+(?:all\s+|your\s+)?(?:previous|prior|above)\s+instructions?|"
    r"(?:which|what)\s+(?:llm|model|ai|api|database|framework)\b|"
    r"api\s*(?:endpoint|key|url|route)s?|endpoints?|\bapis?\b|qdrant|opensearch|langgraph|"
    r"architecture|pipeline|planner|composer|source\s+code|backend|tech\s+stack|"
    r"claude|openai|anthropic|gpt|gemini|haiku|"
    r"how\s+(?:do|does|are)\s+(?:you|this|the\s+(?:bot|system|assistant))\s+(?:work|built|made|trained|implemented))\b",
    re.I,
)

_ADVICE_RE = re.compile(
    r"\b(?:should\s+i\s+(?:buy|sell|invest|switch|redeem|hold|exit|stop)|"
    r"recommend(?:ation)?s?\b|suggest\s+(?:me|a|some)\b|"
    r"(?:good|right|best)\s+time\s+to\s+(?:buy|sell|invest|exit)|"
    r"(?:worth|safe)\s+(?:investing|to\s+invest)|"
    r"which\s+(?:fund|funds|stock|stocks)\s+(?:to|should\s+i)\s+(?:buy|invest|pick|choose)|"
    r"where\s+(?:to|should\s+i)\s+invest)",
    re.I,
)
# A data ask next to an advice phrase still goes to the planner; the composer redirects the advice part.
_DATA_ASK_RE = re.compile(
    r"\b(?:returns?|nav|aum|holdings?|sectors?|rating|risk|compare|news|xirr|sip|expense|portfolio|why|"
    r"perform\w*|category|average|avg|benchmark|large|mid|small|flexi|multi|elss|debt|equity|hybrid|"
    r"index|liquid|cap|top|best|rated|\d+\s+(?:\w+\s+)?funds?)\b",
    re.I,
)

_KEYBOARD_RUNS = ("asdf", "qwer", "zxcv", "sdfg", "dfgh", "hjkl", "wert", "xcvb", "poiu", "lkjh")
_VOWELS = set("aeiouy")

_FUND_WORDS = {
    "cap", "large", "mid", "small", "flexi", "multi", "elss", "tax", "saver", "index", "etf", "liquid",
    "debt", "equity", "hybrid", "balanced", "growth", "value", "contra", "focused", "dividend", "yield",
    "gold", "silver", "sectoral", "thematic", "banking", "pharma", "it", "technology", "infra", "infrastructure",
    "psu", "bond", "gilt", "overnight", "arbitrage", "momentum", "quality", "nifty", "sensex", "midcap",
    "smallcap", "largecap", "bluechip", "blue", "chip", "top", "direct", "regular", "plan", "sip", "money",
    "market", "short", "long", "term", "duration", "ultra", "low", "corporate", "credit", "risk", "conservative",
    "aggressive", "dynamic", "asset", "allocation", "fof", "international", "global", "us", "overseas",
    "consumption", "manufacturing", "energy", "auto", "fmcg", "healthcare", "financial", "services", "next",
    "50", "100", "200", "250", "500", "mutual", "my", "the", "a", "an", "this", "that", "which", "what", "any",
    "best", "good", "better", "all", "some", "other", "another", "same", "one", "two", "of", "in", "on", "for",
    "and", "or", "is", "are", "to", "me", "show", "tell", "about", "give", "list", "compare", "vs", "versus",
    "above", "these", "those", "them", "both", "previous", "earlier", "mentioned", "listed", "following",
    "suggested", "recommended", "said",
    "how", "does", "do", "has", "have", "with", "from", "fund", "funds", "scheme", "schemes", "your", "our",
    "performing", "performance", "returns", "return", "nav", "holding", "holdings", "invested", "investing",
    "category", "type", "types", "open", "ended", "close", "closed", "bank", "banks", "psu", "capital",
}
_FUND_PHRASE_RE = re.compile(r"\b([a-z][a-z0-9&'.-]{2,})\s+(?:mutual\s+)?funds?\b", re.I)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def asks_internals(question: str) -> bool:
    return bool(_INTERNALS_RE.search(question or ""))


def mentions_advice(question: str) -> bool:
    """A buy / sell / recommend phrase anywhere in the question (data asks may sit beside it)."""
    return bool(_ADVICE_RE.search(question or ""))


def asks_advice_only(question: str) -> bool:
    text = question or ""
    if re.search(r"\bshould\s+i\s+(?:buy|sell|invest|switch|redeem|exit)\b", text, re.I):
        # Fund-type words (large cap) do not count as a data ask here; metrics do.
        return not re.search(r"\b(?:returns?|nav|aum|holdings?|rating|risk|compare|news|xirr|expense|why|perform\w*)\b", text, re.I)
    return bool(_ADVICE_RE.search(text)) and not _DATA_ASK_RE.search(text)


def looks_like_gibberish(question: str) -> bool:
    text = (question or "").strip()
    if not text:
        return False
    toks = _tokens(text)
    if not toks:
        return True
    if all(t in _FUND_WORDS for t in toks):
        return False

    def bad(tok: str) -> bool:
        if tok.isdigit() or len(tok) < 3:
            return False
        if any(run in tok for run in _KEYBOARD_RUNS):
            return True
        if len(tok) >= 4 and not (set(tok) & _VOWELS):
            return True
        return len(set(tok)) <= 2 and len(tok) >= 4

    return all(bad(t) or (t.isdigit()) or len(t) < 3 for t in toks) and any(bad(t) for t in toks)


def _close_to_known(word: str) -> bool:
    return bool(difflib.get_close_matches(word, _FUND_WORDS, n=1, cutoff=0.78))


def unknown_fund_phrase(question: str) -> str:
    """The word before 'fund' when it is not a scheme, AMC, category or sector. Empty when fine."""
    text = (question or "").strip()
    if not text or len(_tokens(text)) > 10:
        return ""
    match = _FUND_PHRASE_RE.search(text)
    if not match:
        return ""
    word = match.group(1).lower()
    if word in _FUND_WORDS or _close_to_known(word):
        return ""
    try:
        from news_rag.fund_search import _amc_hints_from_tokens, resolve_fund_for_query

        if _amc_hints_from_tokens([word]):
            return ""
        from news_rag.insight.entity_candidates import _sector_candidates

        if _sector_candidates(word):  # "defence fund", "pharma fund" are sector funds
            return ""
        detail, ambiguous, close = resolve_fund_for_query(text)
        if detail or ambiguous or close:
            return ""
    except Exception:  # noqa: BLE001
        return ""  # shortcut: catalog unavailable, let the planner decide
    return word


SIGN_IN_REPLY = "Please sign in to see your own portfolio. Meanwhile I can answer questions about any fund, a sector, or market news."
_OWN_BOOK_RE = re.compile(r"\bmy\s+(?:portfolio|funds?|holdings?|sips?|stps?|xirr|investments?|mutual\s+funds?)\b", re.I)


def guard_reply(
    question: str,
    *,
    portfolio_enabled: bool = True,
    has_history: bool = False,
) -> tuple[str, str] | None:
    """Return (kind, reply) for a question that must not reach the planner, else None."""
    if not portfolio_enabled and _OWN_BOOK_RE.search(question or ""):
        return "sign_in", SIGN_IN_REPLY
    if asks_internals(question):
        return "internals", INTERNALS_REPLY
    if asks_advice_only(question):
        return "advice", APP_RECOMMENDATION_REPLY
    if looks_like_gibberish(question):
        return "gibberish", GIBBERISH_REPLY
    if has_history:
        return None
    phrase = unknown_fund_phrase(question)
    if phrase:
        return "unknown_fund", UNKNOWN_FUND_REPLY.format(phrase=phrase)
    return None
