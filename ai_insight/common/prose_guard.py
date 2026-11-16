"""Shared reader voice, synthesis rules, and refusal-phrase cleanup."""

from __future__ import annotations

import re

READER_VOICE = """Voice: short sentences, everyday words, Indian retail reader. No jargon (avoid "catalyst", "range-bound trading", "profit-taking" unless you explain in plain words).

Synthesis (when ARTICLES are present):
- You receive many full articles. Use them. Name real themes (companies, policy, commodities, flows, earnings).
- Link at least one price or flow number from FACTS to at least one news theme.
- Article dates may be before trading_date — say "earlier this week" or the date, then the theme.
- Write 2–4 connected ideas: what moved, what news talked about, how they may fit together (hedged).

Hard bans — never write sentences like:
- "articles do not explain"
- "do not tie today's"
- "not identified from the news"
- "no sector articles were supplied"
- "cannot be determined"
- "we do not have enough news"
- "no single cause"
- "best read as profit-taking" without naming news that mentioned selling or books
- "specific catalyst ... not identified"
- "moves look like range-bound trading" without linking to a concrete theme
- "booking gains", "profit taking after the rise", "only a guess", "no single named cause"
- "news does not explain today's", "does not cover today's", "link to the move is only"
- Never say today's news is missing or that articles fail to cover trading_date.

If article_count is 0: explain only from FACTS bars (best/worst day, week %, where close sits in the range). Do not blame missing news.

If article_count > 0: you must cite at least two themes from ARTICLES. Do not claim the feed is empty. Build the best story you can from the week.
"""

_REFUSAL = re.compile(
    r"(articles?\s+do\s+not|do\s+not\s+explain|do\s+not\s+directly\s+tie|"
    r"does\s+not\s+tie\s+today|not\s+identified|cannot\s+be\s+determined|"
    r"no\s+sector\s+articles|were\s+not\s+supplied|no\s+articles\s+were|"
    r"we\s+do\s+not\s+have\s+enough|no\s+single\s+cause|no\s+single\s+named\s+cause|"
    r"not\s+from\s+the\s+news\s+feed|so\s+the\s+specific\s+catalyst|"
    r"news\s+feed\s+does\s+not|pullback\s+is\s+best\s+read|booking\s+gains|"
    r"profit[\s-]?taking|only\s+a\s+guess|does\s+not\s+cover\s+today|"
    r"explain\s+today'?s\s+dip|explain\s+today'?s\s+drop|"
    r"rally\s+itself\s+has\s+no|no\s+named\s+cause\s+in\s+the\s+articles)",
    re.I,
)

_JARGON = (
    (re.compile(r"\bcatalyst\b", re.I), "reason"),
    (re.compile(r"\brange-bound trading\b", re.I), "sideways moves"),
    (re.compile(r"\bprofit-taking\b", re.I), "booking gains"),
)


def split_sentences(body: str) -> list[str]:
    shielded = re.sub(r"(\d)\.(\d)", r"\1<dot>\2", body or "")
    parts = re.split(r"(?<=[.!?])\s+", shielded)
    return [part.replace("<dot>", ".").strip() for part in parts if part.strip()]


def scrub_refusal_prose(body: str) -> str:
    kept = [sentence for sentence in split_sentences(body) if not _REFUSAL.search(sentence)]
    if not kept:
        return body.strip()
    text = " ".join(kept)
    for pattern, replacement in _JARGON:
        text = pattern.sub(replacement, text)
    return text.strip()


def contains_refusal(text: str) -> bool:
    return bool(_REFUSAL.search(text or ""))