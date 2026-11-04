"""Indian digit grouping for rupee amounts (lakhs/crores commas)."""

from __future__ import annotations

import re
from typing import Any

_LAKH = 100_000.0

_RUPEE_IN_TEXT = re.compile(
    r"(?P<prefix>₹|Rs\.?\s?|INR\s?)(?P<num>[+-]?\d[\d,]*(?:\.\d+)?)",
    re.I,
)


def format_indian_integer_digits(digits: str) -> str:
    """Group integer digits Indian style: …,XX,XX,XXX."""
    raw = (digits or "").lstrip("+").lstrip("-")
    if not raw.isdigit():
        return digits
    if len(raw) <= 3:
        return raw
    last3 = raw[-3:]
    rest = raw[:-3]
    pairs: list[str] = []
    while rest:
        pairs.insert(0, rest[-2:])
        rest = rest[:-2]
    return ",".join(pairs + [last3])


def format_indian_amount(value: float, *, max_decimals: int = 2) -> str:
    sign = "-" if value < 0 else ""
    n = abs(float(value))
    if max_decimals == 0 or abs(n - round(n)) < 0.005:
        return sign + format_indian_integer_digits(str(int(round(n))))
    whole = int(n)
    frac = f"{n:.{max_decimals}f}".split(".", 1)[1].rstrip("0")
    if not frac:
        return sign + format_indian_integer_digits(str(whole))
    return sign + format_indian_integer_digits(str(whole)) + "." + frac


def format_inr(value: Any, *, symbol: str = "₹", max_decimals: int = 2) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    body = format_indian_amount(n, max_decimals=max_decimals)
    if body.startswith("-"):
        return f"-{symbol}{body[1:]}"
    return f"{symbol}{body}"


def format_rs(value: Any, *, max_decimals: int = 2) -> str:
    return format_inr(value, symbol="Rs ", max_decimals=max_decimals)


def normalize_rupee_commas_in_text(text: str, *, min_value: float = _LAKH) -> str:
    """Rewrite ₹ / Rs amounts to Indian commas when value ≥ min_value (default 1 lakh)."""

    def repl(match: re.Match[str]) -> str:
        prefix = match.group("prefix")
        num_s = match.group("num")
        try:
            value = float(num_s.replace(",", ""))
        except ValueError:
            return match.group(0)
        if abs(value) < min_value:
            return match.group(0)
        formatted = format_indian_amount(value)
        if formatted.startswith("-"):
            body = formatted[1:]
            sign = "-"
        else:
            body = formatted
            sign = ""
        if prefix.strip().lower().startswith("rs") or prefix.upper().startswith("INR"):
            sep = " " if prefix.endswith(" ") or prefix.lower() == "rs." else ""
            return f"{sign}Rs{sep}{body}"
        return f"{sign}₹{body}"

    return _RUPEE_IN_TEXT.sub(repl, text or "")
