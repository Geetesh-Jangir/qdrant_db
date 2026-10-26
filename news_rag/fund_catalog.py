"""AMC names and search prefixes derived from regular-growth-by-amc.md (not hand-maintained per fund)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Colloquial AMC tokens → catalog brand phrase (still small; schemes match via fuzzy on 2194 names).
_COLL_AMC_SHORTHAND: dict[str, str] = {
    "absl": "aditya birla sun life",
    "ppfas": "parag parikh",
    "icici": "icici prudential",
    "pru": "prudential",
    "hdfc": "hdfc",
    "sbi": "sbi",
    "boi": "bank of india",
    "lic": "lic",
    "uti": "uti",
    "jm": "jm financial",
    "nj": "nj",
    "bnp": "baroda bnp paribas",
    "baroda": "baroda bnp paribas",
    "canara": "canara robeco",
    "robeco": "canara robeco",
    "franklin": "franklin templeton",
    "templeton": "franklin templeton",
    "nippon": "nippon india",
    "motilal": "motilal oswal",
    "oswal": "motilal oswal",
    "mirae": "mirae asset",
    "mahindra": "mahindra manulife",
    "manulife": "mahindra manulife",
    "jio": "jio blackrock",
    "blackrock": "jio blackrock",
    "old": "old bridge",
    "bridge": "old bridge",
    "whiteoak": "whiteoak capital",
    "white": "whiteoak capital",
    "oak": "whiteoak capital",
    "360": "360 one",
}

_HEADER_SUFFIX_RE = re.compile(
    r"\s+(?:"
    r"Mutual Fund|MF|QSIF|SIF|Arudha SIF|Altiva SIF|RedHex SIF|Prism SIF|"
    r"Titanium SIF|Arthaya SIF|WSIF|APEX SIF|Sapphire SIF|Platinum SIF"
    r")\s*$",
    re.I,
)


def bare_amc_name(header: str) -> str:
    s = (header or "").strip()
    s = _HEADER_SUFFIX_RE.sub("", s).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _prefixes_for_amc_header(header: str) -> list[str]:
    bare = bare_amc_name(header)
    if not bare:
        return []
    low = bare.lower()
    out: list[str] = [low]
    parts = low.split()
    if len(parts) >= 3:
        out.append(" ".join(parts[:3]))
    if len(parts) >= 2:
        out.append(" ".join(parts[:2]))
    if parts:
        out.append(parts[0])
    # Header like "AMC 400091" — skip numeric-only junk prefixes
    if low.startswith("amc ") and low[4:].strip().isdigit():
        return []
    return out


@dataclass
class AmcCatalogIndex:
    amc_headers: list[str] = field(default_factory=list)
    prefixes: list[str] = field(default_factory=list)
    prefix_re: re.Pattern[str] | None = None
    hint_tokens: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def needles_for_hint(self, hint: str) -> tuple[str, ...]:
        return self.hint_tokens.get(hint, (hint,))


def build_amc_catalog(amc_headers: list[str]) -> AmcCatalogIndex:
    headers = [h.strip() for h in amc_headers if (h or "").strip()]
    prefix_to_amc: dict[str, str] = {}
    hints: dict[str, set[str]] = {}

    def add_prefix(prefix: str, header: str) -> None:
        p = prefix.strip().lower()
        if len(p) < 2 or p in ("amc", "fund", "the"):
            return
        if p.isdigit():
            return
        bare = bare_amc_name(header).lower()
        amc_blob = header.lower()
        if len(p) >= 3 or p in ("jm", "nj", "uti", "lic", "dsp", "hsbc", "quant"):
            prefix_to_amc[p] = bare
        for needle in (bare, amc_blob):
            if not needle:
                continue
            for tok in re.findall(r"[a-z0-9]+", p):
                if len(tok) >= 2:
                    hints.setdefault(tok, set()).add(needle)
            if " " in p:
                hints.setdefault(p.replace(" ", ""), set()).add(needle)
                hints.setdefault(p, set()).add(needle)

    for header in headers:
        for p in _prefixes_for_amc_header(header):
            add_prefix(p, header)

    for shorthand, brand in _COLL_AMC_SHORTHAND.items():
        add_prefix(shorthand, brand)
        add_prefix(brand, brand)

    ordered = sorted(prefix_to_amc.keys(), key=lambda x: (-len(x), x))
    if ordered:
        alt = "|".join(re.escape(p) for p in ordered)
        prefix_re = re.compile(rf"\b({alt})\b", re.I)
    else:
        prefix_re = re.compile(r"(?!x)x")

    hint_tokens = {k: tuple(sorted(v)) for k, v in hints.items()}
    return AmcCatalogIndex(
        amc_headers=headers,
        prefixes=ordered,
        prefix_re=prefix_re,
        hint_tokens=hint_tokens,
    )


_CATALOG: AmcCatalogIndex | None = None


def get_amc_catalog() -> AmcCatalogIndex | None:
    return _CATALOG


def install_amc_catalog(amc_headers: list[str]) -> AmcCatalogIndex:
    global _CATALOG
    _CATALOG = build_amc_catalog(amc_headers)
    return _CATALOG
