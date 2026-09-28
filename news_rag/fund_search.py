"""Fast search and autocomplete recommendations across mutual funds."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from news_rag.config import get_settings

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _extract_plan_option(isin: str, name: str, direct_growth_isins: set[str]) -> tuple[str, str]:
    name_lower = name.lower()
    
    # 1. Determine Plan
    if "direct" in name_lower or isin in direct_growth_isins:
        plan = "Direct"
    elif "regular" in name_lower:
        plan = "Regular"
    else:
        plan = "Regular"

    # 2. Determine Option
    if "reinvestment" in name_lower or "reinvest" in name_lower:
        option = "IDCW Reinvestment"
    elif "payout" in name_lower:
        option = "IDCW Payout"
    elif "idcw" in name_lower:
        option = "IDCW"
    elif "dividend" in name_lower:
        option = "Dividend"
    elif "bonus" in name_lower:
        option = "Bonus"
    elif "monthly" in name_lower:
        option = "Monthly"
    elif "quarterly" in name_lower:
        option = "Quarterly"
    elif "weekly" in name_lower:
        option = "Weekly"
    elif "fortnightly" in name_lower:
        option = "Fortnightly"
    elif "annually" in name_lower or "annual" in name_lower:
        option = "Annual"
    elif "daily" in name_lower:
        option = "Daily"
    elif "growth" in name_lower or isin in direct_growth_isins:
        option = "Growth"
    else:
        option = "Growth"

    return plan, option


class FundIndex:
    def __init__(self) -> None:
        self._loaded: bool = False
        self._entries: list[dict[str, Any]] = []
        self._data_path: Path | None = None
        self._full_map: dict[str, dict[str, Any]] | None = None
        self._direct_growth_isins: set[str] = set()

    def _find_data_file(self) -> Path | None:
        settings = get_settings()
        candidates = [
            _REPO_ROOT / settings.allisin_sectors_holdings_json,
            _REPO_ROOT / "data/fund_holdings_aggregate/allisin_sectors_with_holdings.json",
            _REPO_ROOT / "data/fund_holdings_aggregate/fund_sectors_and_holdings_aggregate.json",
        ]
        for path in candidates:
            if path.is_file():
                return path
        return None

    def _load_direct_growth_isins(self) -> set[str]:
        direct_file = _REPO_ROOT / "data" / "direct_plan_growth_isins.txt"
        if direct_file.is_file():
            try:
                return set(direct_file.read_text(encoding="utf-8").splitlines())
            except Exception:
                pass
        return set()

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        data_path = self._find_data_file()
        if not data_path or not data_path.is_file():
            logger.warning("No fund aggregate JSON file found for search index")
            self._loaded = True
            return

        self._data_path = data_path
        self._direct_growth_isins = self._load_direct_growth_isins()

        try:
            with open(data_path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            entries: list[dict[str, Any]] = []
            full_map: dict[str, dict[str, Any]] = {}

            if isinstance(raw, dict):
                for isin, val in raw.items():
                    if isin.startswith("_") or not isinstance(val, dict):
                        continue
                    name = str(val.get("fund_short_name") or val.get("fund_name") or isin).strip()
                    category = str(val.get("category") or "").strip()
                    scheme_type = str(val.get("scheme_type") or "").strip()
                    as_on = str(val.get("as_on") or "").strip()
                    
                    plan, option = _extract_plan_option(isin, name, self._direct_growth_isins)

                    entry = {
                        "isin": isin,
                        "fund_short_name": name,
                        "plan": plan,
                        "option": option,
                        "category": category,
                        "scheme_type": scheme_type,
                        "as_on": as_on,
                        "name_lower": name.lower(),
                        "isin_lower": isin.lower(),
                    }
                    entries.append(entry)
                    
                    # Augment full map with plan and option
                    val_copy = dict(val)
                    val_copy["plan"] = plan
                    val_copy["option"] = option
                    full_map[isin] = val_copy

            self._entries = entries
            self._full_map = full_map
            self._loaded = True
            logger.info("Loaded %d funds into search index from %s", len(self._entries), data_path.name)
        except Exception as exc:
            logger.exception("Failed to load fund index from %s: %s", data_path, exc)
            self._loaded = True

    def search(self, query: str, limit: int = 15) -> list[dict[str, Any]]:
        """Search funds by name or ISIN with autocomplete ranking."""
        self._ensure_loaded()
        q = (query or "").strip().lower()
        if not q:
            # Return top sample
            return [
                {
                    "isin": e["isin"],
                    "fund_short_name": e["fund_short_name"],
                    "plan": e.get("plan", "Regular"),
                    "option": e.get("option", "Growth"),
                    "category": e["category"],
                    "scheme_type": e["scheme_type"],
                    "as_on": e["as_on"],
                }
                for e in self._entries[:limit]
            ]

        # Scoring buckets:
        # 1. Exact ISIN match
        # 2. ISIN prefix match
        # 3. Name starts with query
        # 4. Word in name starts with query
        # 5. Query substring in name or ISIN
        exact_isin: list[dict] = []
        prefix_isin: list[dict] = []
        name_starts: list[dict] = []
        word_starts: list[dict] = []
        contains: list[dict] = []

        q_words = q.split()

        for e in self._entries:
            isin_lower = e["isin_lower"]
            name_lower = e["name_lower"]

            if isin_lower == q:
                exact_isin.append(e)
            elif isin_lower.startswith(q):
                prefix_isin.append(e)
            elif name_lower.startswith(q):
                name_starts.append(e)
            elif any(w.startswith(q) for w in name_lower.split()):
                word_starts.append(e)
            elif all(w in name_lower for w in q_words) or q in isin_lower:
                contains.append(e)

        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        for group in (exact_isin, prefix_isin, name_starts, word_starts, contains):
            for e in group:
                if e["isin"] not in seen:
                    seen.add(e["isin"])
                    results.append(
                        {
                            "isin": e["isin"],
                            "fund_short_name": e["fund_short_name"],
                            "plan": e.get("plan", "Regular"),
                            "option": e.get("option", "Growth"),
                            "category": e["category"],
                            "scheme_type": e["scheme_type"],
                            "as_on": e["as_on"],
                        }
                    )
                    if len(results) >= limit:
                        return results

        return results

    def get_fund_detail(self, isin: str) -> dict[str, Any] | None:
        """Get full details (sectors, holdings, info) for an ISIN."""
        self._ensure_loaded()
        isin_clean = isin.strip().upper()
        if not self._full_map or isin_clean not in self._full_map:
            # Try case-insensitive lookup
            for k, val in (self._full_map or {}).items():
                if k.upper() == isin_clean:
                    return {"isin": k, **val}
            return None

        val = self._full_map[isin_clean]
        return {"isin": isin_clean, **val}


_fund_index: FundIndex | None = None


def get_fund_index() -> FundIndex:
    global _fund_index
    if _fund_index is None:
        _fund_index = FundIndex()
    return _fund_index
