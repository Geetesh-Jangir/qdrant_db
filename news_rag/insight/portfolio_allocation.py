"""Illustrative equity / debt / gold mix from horizon and preference. No question text."""

from __future__ import annotations

from dataclasses import dataclass, field

_BASE_EQUITY = {
    "very_short": 0,
    "short": 20,
    "medium": 40,
    "medium_long": 55,
    "long": 70,
    "very_long": 80,
}
_EQUITY_BOUNDS = {
    "very_short": (0, 0),
    "short": (0, 30),
    "medium": (20, 55),
    "medium_long": (35, 70),
    "long": (50, 85),
    "very_long": (60, 90),
}
_EQUITY_SPLIT = {
    "wide": (("large cap", 40), ("flexi cap", 25), ("mid cap", 20), ("small cap", 15)),
    "mid": (("large cap", 50), ("flexi cap", 30), ("mid cap", 20)),
    "core": (("large cap", 100),),
}
_FUND_TYPE = {
    "large cap": "equity",
    "flexi cap": "equity",
    "mid cap": "equity",
    "small cap": "equity",
    "liquid": "debt",
    "short duration": "debt",
    "corporate bond": "debt",
    "conservative hybrid": "hybrid",
    "gold etf": "others",
}


@dataclass
class AllocationCategory:
    fund_type: str
    category: str
    role: str
    weight_pct: int


@dataclass
class Allocation:
    bucket: str
    preference_used: str
    assumed_preference: bool
    equity_pct: int
    debt_pct: int
    gold_pct: int
    mismatch: str
    categories: list[AllocationCategory] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)

    def pairs(self) -> list[tuple[str, str]]:
        return [(row.fund_type, row.category) for row in self.categories]

    def composer_note(self) -> str:
        pref = self.preference_used
        if self.assumed_preference:
            pref = f"{pref} (assumed, because no equity or debt preference was given)"
        lines = [
            "This is an illustrative allocation framework from horizon and preference only.",
            f"Horizon: {self.bucket.replace('_', ' ')}. Preference: {pref}.",
            f"Equity {self.equity_pct}%, debt {self.debt_pct}%, gold {self.gold_pct}%. These sum to 100%.",
            " ".join(self.rationale),
        ]
        if self.mismatch:
            lines.append(self.mismatch)
        lines.append(
            "Risks: equity can fall, debt prices move with interest rates, and gold can fall. "
            "Do not promise returns or capital protection."
        )
        lines.append("Mutual fund investments are subject to market risks.")
        lines.append(
            "Name one fund per category below, in this order, with its RupeeStop score out of 100 "
            "and RS label. Do not add a category that is not listed. Do not invent schemes."
        )
        for row in self.categories:
            lines.append(f"- {row.category} ({row.role}): about {row.weight_pct}% of the mix")
        return " ".join(lines)


def bucket_for_years(years: float) -> str:
    if years < 0:
        raise ValueError("horizon_years must be >= 0")
    if years < 1:
        return "very_short"
    if years < 3:
        return "short"
    if years < 5:
        return "medium"
    if years < 7:
        return "medium_long"
    if years < 10:
        return "long"
    return "very_long"


def _split(total: int, parts: tuple[tuple[str, int], ...]) -> list[tuple[str, int]]:
    if total <= 0 or not parts:
        return []
    raw = [int(round(total * share / 100)) for _name, share in parts]
    drift = total - sum(raw)
    raw[-1] += drift
    out: list[tuple[str, int]] = []
    for (name, _share), weight in zip(parts, raw):
        if weight > 0:
            out.append((name, weight))
    if out:
        out[-1] = (out[-1][0], out[-1][1] + (total - sum(w for _n, w in out)))
    return [(name, weight) for name, weight in out if weight > 0]


def _categories(bucket: str, equity: int, debt: int, gold: int) -> list[AllocationCategory]:
    rows: list[AllocationCategory] = []
    if equity >= 70:
        equity_parts = _EQUITY_SPLIT["wide"]
    elif equity >= 40:
        equity_parts = _EQUITY_SPLIT["mid"]
    else:
        equity_parts = _EQUITY_SPLIT["core"]
    for name, weight in _split(equity, equity_parts):
        rows.append(AllocationCategory(_FUND_TYPE[name], name, "equity", weight))
    if bucket in ("very_short", "short"):
        debt_names = ("liquid", "short duration") if debt >= 40 else ("liquid",)
    else:
        debt_names = ("corporate bond", "conservative hybrid") if debt >= 30 else ("corporate bond",)
    debt_parts = tuple((name, 100 // len(debt_names)) for name in debt_names)
    # Last share absorbs the remainder of 100.
    if debt_parts:
        shares = [100 // len(debt_names)] * len(debt_names)
        shares[-1] += 100 - sum(shares)
        debt_parts = tuple((name, share) for name, share in zip(debt_names, shares))
    for name, weight in _split(debt, debt_parts):
        role = "stability" if name != "liquid" else "cash-like"
        rows.append(AllocationCategory(_FUND_TYPE[name], name, role, weight))
    if gold > 0:
        rows.append(AllocationCategory("others", "gold etf", "hedge", gold))
    return rows


def allocate(horizon_years: float, preference: str, include_gold: bool) -> Allocation:
    if horizon_years < 0:
        raise ValueError("horizon_years must be >= 0")
    bucket = bucket_for_years(horizon_years)
    raw_pref = (preference or "unspecified").strip().lower()
    assumed = raw_pref in ("", "unspecified")
    pref = "balanced" if assumed else raw_pref
    if pref not in ("equity_more", "debt_more", "balanced"):
        pref = "balanced"
        assumed = True
    equity = _BASE_EQUITY[bucket]
    if pref == "equity_more":
        equity += 15
    elif pref == "debt_more":
        equity -= 15
    floor, cap = _EQUITY_BOUNDS[bucket]
    clipped = equity < floor or equity > cap
    equity = max(floor, min(cap, equity))
    debt = 100 - equity
    gold = 0
    mismatch = ""
    if clipped:
        mismatch = (
            "The equity or debt preference was only applied up to the limit for this horizon. "
            "A shorter goal does not get an equity-heavy mix."
        )
    if include_gold and bucket in ("very_short", "short"):
        mismatch = (mismatch + " Gold is not used when the money is needed inside 3 years.").strip()
    elif include_gold:
        gold = 5
        base = equity + debt
        eq_cut = int(round(5 * equity / base)) if base else 0
        eq_cut = max(0, min(5, eq_cut))
        equity -= eq_cut
        debt -= 5 - eq_cut
    debt = 100 - equity - gold
    if equity < 0 or debt < 0 or gold < 0 or equity + debt + gold != 100:
        raise ValueError("allocation does not sum to 100")
    rationale = [
        f"The {bucket.replace('_', ' ')} horizon set the starting equity share.",
        "The preference then moved that share, and the horizon limit had the final say.",
    ]
    if not include_gold:
        rationale.append("Gold stays at 0% because it was not requested.")
    elif gold:
        rationale.append("Gold is 5% and was taken out of the equity and debt shares.")
    return Allocation(
        bucket=bucket,
        preference_used=pref,
        assumed_preference=assumed,
        equity_pct=equity,
        debt_pct=debt,
        gold_pct=gold,
        mismatch=mismatch,
        categories=_categories(bucket, equity, debt, gold),
        rationale=rationale,
    )
