"""Fix common LLM placeholder fragments before the answer is shown."""

from __future__ import annotations

import re


_BROKEN_PHRASES = (
    (re.compile(r"\b(?:was|is)\s+\*{0,2}ahead\s+by\s+percentage\s+points\*{0,2}\b", re.I), "was ahead on returns"),
    (re.compile(r"\b(?:was|is)\s+\*{0,2}behind\s+by\s+percentage\s+points\*{0,2}\b", re.I), "trailed on returns"),
    (re.compile(r"about\s+\*\*\s*crore\s*\*\*", re.I), ""),
    (re.compile(r"\*\*\s*percentage\s+points\s*\*\*", re.I), ""),
)


def repair_compose_placeholders(text: str) -> str:
    out = str(text or "")
    for pattern, repl in _BROKEN_PHRASES:
        out = pattern.sub(repl, out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()