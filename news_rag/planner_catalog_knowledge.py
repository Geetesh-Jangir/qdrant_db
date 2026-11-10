"""Catalog facts baked into the planner system prompt: AMCs, aliases, categories, schemes."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from news_rag.fund_catalog import _COLL_AMC_SHORTHAND, bare_amc_name

_GROWTH_TAIL = re.compile(
    r"\s+-\s+(?:Regular Plan\s+-\s+)?Growth\s*$",
    re.I,
)
_SCHEME_LINE = re.compile(r"^-\s+(.+?)\s+—\s+`[^`]+`\s*$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _scheme_categories_block(text: str) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return ""
    lines = ["Asset types and their scheme categories (use these exact category words):"]
    if not isinstance(data, dict):
        return ""
    for asset, cats in data.items():
        if not isinstance(cats, list):
            continue
        names = [str(c).strip() for c in cats if str(c).strip() and str(c).strip().lower() != "unknown"]
        lines.append(f"- {asset}: {', '.join(names)}")
    return "\n".join(lines)


def _catalog_block(md: str) -> str:
    aliases = [
        f"{token} = {brand}"
        for token, brand in sorted(_COLL_AMC_SHORTHAND.items())
    ]
    lines = [
        "AMC aliases (a user token means that brand, not a different house):",
        ", ".join(aliases),
        "",
        "How scheme names are built: «AMC brand» + strategy (Flexi Cap, Liquid, Nifty 50 Index, BSE Sensex ETF, Gold ETF, ELSS, Retirement, Children's, Arbitrage, Balanced Advantage, sector or thematic name) + optional «Regular Plan - Growth». An ETF line often has no plan suffix. Quant Mutual Fund is not Quantum Mutual Fund and not a scheme whose strategy word is Quant (Axis Quant Fund).",
        "",
        "Every Regular Growth scheme and listed ETF in the catalog, grouped by AMC. Copy a name from the question or from conversation history. Use this list to spell the house and the strategy. Do not name a scheme from this list unless the user asked which funds to look at, or the name is already in the conversation.",
    ]
    current = ""
    schemes: list[str] = []

    def flush() -> None:
        if current and schemes:
            lines.append(f"## {current}")
            lines.append("; ".join(schemes))

    for raw in md.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            flush()
            current = line[3:].strip()
            schemes = []
            continue
        match = _SCHEME_LINE.match(line)
        if not match or not current:
            continue
        name = _GROWTH_TAIL.sub("", match.group(1)).strip()
        if name:
            schemes.append(name)
    flush()
    bare = []
    for raw in md.splitlines():
        if raw.startswith("## "):
            name = bare_amc_name(raw[3:])
            if name and name not in bare:
                bare.append(name)
    if bare:
        lines.insert(0, "AMC brands: " + ", ".join(bare))
        lines.insert(1, "")
    return "\n".join(lines)


@lru_cache(maxsize=1)
def planner_catalog_knowledge() -> str:
    root = _repo_root()
    folder = root / "data" / "fund_holdings_aggregate"
    categories = _scheme_categories_block(_read(folder / "assetType_and_their_schemeCategories.txt"))
    catalog = _catalog_block(_read(folder / "regular-growth-by-amc.md"))
    parts = [p for p in (categories, catalog) if p]
    if not parts:
        return ""
    return "### FUND NAMES AND CATEGORIES\n" + "\n\n".join(parts)
