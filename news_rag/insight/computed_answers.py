"""Questions the composer can answer by calculating, with no catalog tool."""

from __future__ import annotations

import re

_TOPIC_RE = re.compile(
    r"\b(?:sip|swp|stp|fire|corpus|step[\s-]?up|retirement)\b",
    re.I,
)
_ASK_RE = re.compile(
    r"\b(?:plan|calculate|calculation|how\s+much|reach|goal|corpus|crore|lakh|years?)\b",
    re.I,
)


def asks_computed_illustration(question: str) -> bool:
    """SIP / FIRE / goal math the model can work out without fund data."""
    q = question or ""
    return bool(_TOPIC_RE.search(q) and _ASK_RE.search(q))
