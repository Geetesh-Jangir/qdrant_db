"""User phrasing → canonical sector index keys (see sector_to_isin_weights.json).

Edit this file to add synonyms; longest alias wins at match time (word boundaries).
Keys are lowercase phrases; values are tuples of index sector names.
"""

from __future__ import annotations

# fmt: off
SECTOR_ALIAS_MAP: dict[str, tuple[str, ...]] = {
    # —— Information technology ——
    "information technology": ("It - Software", "It - Services", "Software"),
    "information technology sector": ("It - Software", "It - Services", "Software"),
    "it sector": ("It - Software", "It - Services"),
    "it software": ("It - Software", "Software"),
    "it services": ("It - Services",),
    "it software sector": ("It - Software", "Software"),
    "software sector": ("It - Software", "Software"),
    "software technology": ("It - Software", "Software"),
    "technology sector": ("It - Software", "It - Services", "Technology Hardware & Equipment"),
    "technology": ("It - Software", "It - Services", "Technology Hardware & Equipment"),
    "tech sector": ("It - Software", "It - Services"),
    "tech": ("It - Software", "It - Services"),
    "software": ("It - Software", "Software"),
    # "it" alone: resolved only with IT disambiguation in sector_fund_ranking (not pronoun "it")

    # —— Banking & financials ——
    "banking sector": ("Banks", "Finance"),
    "banking & financials": ("Banks", "Finance", "Financial Services"),
    "banking & financial services": ("Banks", "Finance", "Financial Services"),
    "banking and financial services": ("Banks", "Finance", "Financial Services"),
    "banking": ("Banks", "Finance"),
    "bank sector": ("Banks", "Finance"),
    "banks sector": ("Banks", "Finance"),
    "banks": ("Banks", "Finance"),
    "bank": ("Banks", "Finance"),
    "financials": ("Banks", "Finance", "Financial Services"),
    "financial services": ("Banks", "Finance", "Financial Services", "Capital Markets"),
    "financial services sector": ("Banks", "Finance", "Financial Services"),
    "financial": ("Banks", "Finance", "Capital Markets"),
    "finance sector": ("Banks", "Finance", "Financial Services"),
    "finance": ("Banks", "Finance", "Financial Services"),
    "psu banks": ("Banks",),
    "public sector banks": ("Banks",),
    "private banks": ("Banks",),
    "rbi": ("Banks", "Finance"),
    "repo rate": ("Banks", "Finance"),
    "repo": ("Banks", "Finance"),
    "rate hike": ("Banks", "Finance"),
    "monetary policy": ("Banks", "Finance"),

    # —— Healthcare / pharma ——
    "pharmaceuticals & healthcare": ("Pharmaceuticals & Biotechnology", "Healthcare Services", "Healthcare"),
    "pharmaceuticals": ("Pharmaceuticals & Biotechnology", "Healthcare"),
    "pharma sector": ("Pharmaceuticals & Biotechnology", "Healthcare Services", "Healthcare"),
    "pharma": ("Pharmaceuticals & Biotechnology", "Healthcare Services", "Healthcare"),
    "healthcare sector": ("Healthcare Services", "Pharmaceuticals & Biotechnology", "Healthcare"),
    "healthcare": ("Healthcare Services", "Pharmaceuticals & Biotechnology", "Healthcare"),
    "health care": ("Healthcare Services", "Pharmaceuticals & Biotechnology"),

    # —— Auto ——
    "automotive sector": ("Automobiles", "Auto Components", "Auto Ancillaries"),
    "automotive": ("Automobiles", "Auto Components", "Auto Ancillaries"),
    "auto sector": ("Automobiles", "Auto Components"),
    "automobile sector": ("Automobiles", "Auto Components"),
    "automobile": ("Automobiles", "Auto Components"),
    "automobiles": ("Automobiles", "Auto Components"),

    # —— Capital goods / industrial ——
    "capital goods": ("Capital Goods", "Industrial Manufacturing", "Industrial Products"),
    "capital goods sector": ("Capital Goods", "Industrial Manufacturing", "Industrial Products"),
    "industrial sector": ("Industrial Manufacturing", "Industrial Products", "Capital Goods"),
    "industrial": ("Industrial Manufacturing", "Industrial Products", "Capital Goods"),
    "industrials": ("Industrial Manufacturing", "Industrial Products", "Capital Goods"),
    "infrastructure sector": ("Construction", "Power", "Industrial Products"),
    "infrastructure": ("Construction", "Power", "Industrial Products"),

    # —— Energy / oil / petroleum ——
    "petroleum sector": ("Petroleum Products", "Energy"),
    "petroleum": ("Petroleum Products", "Energy"),
    "petrol sector": ("Petroleum Products", "Energy"),
    "petrol": ("Petroleum Products", "Energy"),
    "oil sector": ("Petroleum Products", "Energy"),
    "oil and gas": ("Petroleum Products", "Energy"),
    "oil & gas": ("Petroleum Products", "Energy"),
    "oil": ("Petroleum Products", "Energy"),
    "crude oil": ("Petroleum Products", "Energy"),
    "crude": ("Petroleum Products", "Energy"),
    "barrel": ("Petroleum Products", "Energy"),
    "brent": ("Petroleum Products", "Energy"),
    "energy sector": ("Power", "Petroleum Products", "Energy"),
    "energy": ("Power", "Petroleum Products", "Energy"),
    "power sector": ("Power", "Energy"),
    "power": ("Power", "Energy"),

    # —— Real estate ——
    "real estate sector": ("Realty", "Real Estate"),
    "real estate": ("Realty", "Real Estate"),
    "realty": ("Realty", "Real Estate"),

    # —— Metals ——
    "metals sector": ("Ferrous Metals", "Non - Ferrous Metals", "Metals & Mining"),
    "metal sector": ("Ferrous Metals", "Non - Ferrous Metals", "Metals & Mining"),
    "metals": ("Ferrous Metals", "Non - Ferrous Metals", "Metals & Mining"),
    "metal": ("Ferrous Metals", "Non - Ferrous Metals", "Metals & Mining"),

    # —— FMCG / consumption (common asks) ——
    "fmcg sector": ("FMCG", "Consumer Non Durables"),
    "fmcg": ("FMCG", "Consumer Non Durables"),
    "consumption sector": ("Consumer Durables", "FMCG"),

    # —— Defence ——
    "defence sector": ("Aerospace & Defence", "Capital Goods"),
    "defense sector": ("Aerospace & Defence", "Capital Goods"),
    "defence": ("Aerospace & Defence", "Capital Goods"),
    "defense": ("Aerospace & Defence", "Capital Goods"),
}
# fmt: on


def sorted_aliases_longest_first() -> list[tuple[str, tuple[str, ...]]]:
    return sorted(SECTOR_ALIAS_MAP.items(), key=lambda kv: len(kv[0]), reverse=True)
