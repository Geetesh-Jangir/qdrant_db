"""Short social openers — no planner LLM."""

from __future__ import annotations

import re

# Persistent bot identity (also injected into planner/composer memory).
RUPEESTOP_IDENTITY_REPLY = "I am an AI bot by SUM."
RUPEESTOP_GREETING_REPLY = RUPEESTOP_IDENTITY_REPLY  # backward-compatible alias

CAPABILITIES_REPLY = (
    "I am an AI bot by SUM.\n\n"
    "Here's what I can help you with:\n"
    "- Explain fund terms and categories (like large cap vs mid cap, SIP, or NAV)\n"
    "- Show NAV, returns, RupeeStop ratings, and risk for a fund\n"
    "- Compare funds and find top funds in a category\n"
    "- Show what a fund holds — its stocks and sector weights\n"
    "- Look at your portfolio, SIPs, and XIRR when you're signed in\n"
    "- Explain market news and how it may affect your funds"
)

ASSISTANT_MAIN_MEMORY = {
    "who_are_you": CAPABILITIES_REPLY,
    "greeting_rule": "When the user only says hello, hi, or good morning, reply with the same greeting (Hello!, Hi!, Good morning!, etc.).",
}

_GREETING_ONLY_RE = re.compile(
    r"^\s*(?:"
    r"hi\b|hello\b|hey\b|hiya\b|howdy\b|"
    r"good\s+(?:morning|afternoon|evening|day)\b|"
    r"namaste\b|namaskar\b"
    r")(?:\s+there|\s+rupeestop|\s+rupee\s*stop)?\s*[!.?]*\s*$",
    re.I,
)

_IDENTITY_ONLY_RE = re.compile(
    r"^\s*(?:"
    r"who\s+are\s+you\b|"
    r"what\s+are\s+you\b|"
    r"who\s+r\s+u\b|"
    r"who\s+is\s+this\b|"
    r"what\s+is\s+this\b|"
    r"introduce\s+yourself\b|"
    r"tell\s+me\s+about\s+yourself\b|"
    r"what\s+can\s+you\s+do\b|"
    r"what\s+do\s+you\s+do\b|"
    r"how\s+can\s+you\s+help\b|"
    r"your\s+capabilities\b|"
    r"what\s+are\s+your\s+capabilities\b|"
    r"who\s+made\s+you\b"
    r")\s*[!.?]*\s*$",
    re.I,
)


def _mirror_greeting(question: str) -> str:
    text = (question or "").strip()
    lower = text.lower().rstrip("!.?").strip()
    if lower.startswith("hello"):
        return "Hello!"
    if re.match(r"hi\b", lower):
        return "Hi!"
    if lower.startswith("hey"):
        return "Hey!"
    if "good morning" in lower:
        return "Good morning!"
    if "good afternoon" in lower:
        return "Good afternoon!"
    if "good evening" in lower:
        return "Good evening!"
    if "good day" in lower:
        return "Good day!"
    if lower.startswith("namaste"):
        return "Namaste!"
    if lower.startswith("namaskar"):
        return "Namaskar!"
    return "Hello!"


def identity_reply(question: str) -> str | None:
    """Canned identity when the message is only 'who are you' and similar."""
    text = (question or "").strip()
    if not text:
        return None
    if _IDENTITY_ONLY_RE.match(text):
        return CAPABILITIES_REPLY
    return None


def greeting_reply(question: str) -> str | None:
    """Return a mirrored greeting when the message is only a social opener."""
    text = (question or "").strip()
    if not text:
        return None
    if _GREETING_ONLY_RE.match(text):
        return _mirror_greeting(text)
    return None
