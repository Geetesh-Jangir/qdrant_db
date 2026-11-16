"""Cosmetic sector names and number formatting. Pipeline names stay the real keys."""

from __future__ import annotations

from news_rag.indian_format import format_indian_amount

# Keys are the 30 SECTOR_QUERIES names. Values are display-only.
SECTOR_DISPLAY: dict[str, str] = {
    "Banks": "Banks",
    "Pharmaceuticals & Biotechnology": "Pharma & Biotech",
    "It - Software": "IT Software",
    "Finance": "Finance",
    "Capital Markets": "Capital Markets",
    "Automobiles": "Automobiles",
    "Auto Components": "Auto Components",
    "Retailing": "Retailing",
    "Electrical Equipment": "Electrical Equipment",
    "Consumer Durables": "Consumer Durables",
    "Industrial Products": "Industrial Products",
    "Petroleum Products": "Petroleum Products",
    "Telecom - Services": "Telecom",
    "Power": "Power",
    "Healthcare Services": "Healthcare",
    "Construction": "Construction",
    "Chemicals & Petrochemicals": "Chemicals",
    "Realty": "Realty",
    "Insurance": "Insurance",
    "Aerospace & Defense": "Aerospace & Defence",
    "Diversified Fmcg": "FMCG",
    "Financial Technology (fintech)": "Fintech",
    "Transport Services": "Transport",
    "Cement & Cement Products": "Cement",
    "Food Products": "Food Products",
    "Ferrous Metals": "Ferrous Metals",
    "Non - Ferrous Metals": "Non-Ferrous Metals",
    "Leisure Services": "Leisure",
    "Beverages": "Beverages",
    "Agricultural, Commercial & Construction Vehicles": "Agri & Commercial Vehicles",
}


def sector_label(pipeline_name: str) -> str:
    return SECTOR_DISPLAY.get(pipeline_name, pipeline_name)


def fmt_inr_crore(value: float) -> str:
    number = float(value)
    body = format_indian_amount(abs(number))
    sign = "-" if number < 0 else ""
    return f"{sign}₹{body} crore"


def fmt_pct(value: float, *, decimals: int = 2) -> str:
    return f"{float(value):+.{decimals}f}%"


def ordinal(n: int) -> str:
    number = int(n)
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    return f"{number}{suffix}"
