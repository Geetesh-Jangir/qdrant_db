"""Human sector label for insight headlines (not Nifty index names)."""

from __future__ import annotations

import re

from lib.portfolio_scope import normalize_sector_label, sector_query_for_label

# Canonical SECTOR_QUERIES key → headline phrase (lowercase, includes "sector" where natural).
_PHRASE_BY_KEY: dict[str, str] = {
    "Banks": "banking sector",
    "It - Software": "IT sector",
    "Automobiles": "auto sector",
    "Pharmaceuticals & Biotechnology": "pharma sector",
    "Diversified Fmcg": "FMCG sector",
    "Ferrous Metals": "metal sector",
    "Non - Ferrous Metals": "metals sector",
    "Realty": "realty sector",
    "Petroleum Products": "energy sector",
    "Power": "power sector",
    "Construction": "infrastructure sector",
    "Finance": "financial services sector",
    "Telecom - Services": "telecom sector",
    "Healthcare Services": "healthcare sector",
    "Retailing": "retail sector",
    "Capital Markets": "capital markets sector",
    "Insurance": "insurance sector",
    "Auto Components": "auto components sector",
    "Electrical Equipment": "electrical equipment sector",
    "Consumer Durables": "consumer durables sector",
    "Chemicals & Petrochemicals": "chemicals sector",
    "Aerospace And Defense": "defence sector",
    "Aerospace & Defense": "defence sector",
}

_AND_RE = re.compile(r"\s+&\s+", re.I)


def _default_phrase(label: str) -> str:
    text = normalize_sector_label(label)
    text = _AND_RE.sub(" and ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    if not text:
        return "sector"
    if text.endswith(" sector"):
        return text
    return f"{text} sector"


def sector_headline_phrase(canonical_sector: str) -> str:
    """Map portfolio/catalog sector label to headline wording (e.g. Banks → banking sector)."""
    raw = str(canonical_sector or "").strip()
    if not raw:
        return "sector"
    mapped = sector_query_for_label(raw)
    key = mapped[0] if mapped else raw
    fold = key.casefold()
    for k, phrase in _PHRASE_BY_KEY.items():
        if k.casefold() == fold:
            return phrase
    return _default_phrase(key)


def primary_sector_headline_phrase(sectors: list[str]) -> str:
    if not sectors:
        return "sector"
    return sector_headline_phrase(sectors[0])