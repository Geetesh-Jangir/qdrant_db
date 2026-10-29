"""Category RS-rating lists. Regular and growth stay fixed.

A named category is one URL. A fund type walks that type's categories only
when a label, score, or return filter is still short. AMC-only lists stay on
the markdown catalog.
"""

from __future__ import annotations

import logging
import random
import re
import threading
import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import quote

import httpx

from news_rag.fund_rating_categories import (
    asks_taxonomy,
    categories_for,
    match_scheme_category,
)
from news_rag.tools import explicit_fund_count

logger = logging.getLogger(__name__)

_RATING_URL = (
    "https://backend.rupeestop.com/api/v1/admin/rs-rating/by-category/"
    "{fund_type}/{category}/regular/growth"
)
_CACHE_TTL_SEC = 3600
_HTTP_TIMEOUT = 12.0
_SHORTLIST = 10
_POSITIVE_CAP = 40

_cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}
_cache_lock = threading.Lock()

_LABELS = (
    ("best in category", "Best in category"),
    ("underperformer", "Underperformer"),
    ("good choice", "Good Choice"),
    ("recommended", "Recommended"),
    ("average", "Average"),
)

_RETURN_RE = re.compile(
    r"\b(?:returns?|performance|performed|performing|gave|giving|yield)\b|"
    r"\b(?:1|3|5)\s*[- ]?(?:y|yr|year)s?\b|\b(?:one|three|five)\s+years?\b",
    re.I,
)
_POSITIVE_RE = re.compile(r"\b(?:positive|gained|gain|up|rose|risen|in the green)\b", re.I)
_HIGHEST_RE = re.compile(r"\b(?:highest|best|top|maximum|max)\b", re.I)
_LOWEST_RE = re.compile(r"\b(?:lowest|worst|minimum|min|bottom)\b", re.I)
_SCORE_RE = re.compile(
    r"\b(?:rs[\s_-]*rating|final[\s_-]*score|rupeestop[\s_-]*score|score|rat(?:ing|ed))\b",
    re.I,
)
_ABOVE_RE = re.compile(
    r"\b(?:above|over|greater than|more than|at least|>=)\s*(\d{1,3}(?:\.\d+)?)\b",
    re.I,
)
_LIST_RE = re.compile(r"\bfunds?\b", re.I)
_RANK_WORD_RE = re.compile(r"\b(?:highest|best|top|lowest|worst|random)\b", re.I)


def _looks_like_fund_list(question: str) -> bool:
    """A list of funds, including one fund asked for as the best or the highest."""
    if explicit_fund_count(question) is not None:
        return True
    if re.search(r"\bfunds\b", question or "", re.I):
        return True
    if _LIST_RE.search(question or "") and _RANK_WORD_RE.search(question or ""):
        return True
    return False


@dataclass
class RatingScreenSpec:
    count: int
    fund_type: str
    category: str
    locked: bool
    label: str
    min_score: float | None
    highest_score: bool
    return_window: str
    return_direction: str
    compare_category: bool
    random_sample: bool
    amc: str

    @property
    def walks(self) -> bool:
        if self.locked:
            return False
        return bool(self.label or self.min_score is not None or self.return_direction or self.highest_score)


def _return_direction(question: str, label: str, window: str) -> str:
    """Rank by a return only when the user asked for the highest or the lowest.

    "Best in category" is a label. It is not a request to sort by 1Y return.
    """
    if not window:
        return ""
    text = question or ""
    if label:
        text = re.sub(re.escape(label), " ", text, flags=re.I)
    if _POSITIVE_RE.search(text):
        return "positive"
    if _LOWEST_RE.search(text):
        return "lowest"
    if _HIGHEST_RE.search(text):
        return "highest"
    return ""


def _amc_token(question: str) -> str:
    from news_rag.tools import screen_hints_from_question

    return str(screen_hints_from_question(question).get("amc") or "").strip()


def _amc_outside_label(question: str, label: str) -> str:
    """A rating label such as Good Choice is not the Choice AMC."""
    amc = _amc_token(question)
    if not amc or not label:
        return amc
    if amc.lower() not in label.lower():
        return amc
    without_label = re.sub(re.escape(label), " ", question or "", flags=re.I)
    if re.search(rf"\b{re.escape(amc)}\b", without_label, re.I):
        return amc
    return ""


def _return_window(question: str) -> str:
    from news_rag.tools import explicit_return_window

    return explicit_return_window(question)


def _label_in(question: str) -> str:
    low = (question or "").lower()
    for phrase, label in _LABELS:
        if phrase in low:
            return label
    return ""


def parse_rating_screen(question: str) -> RatingScreenSpec | None:
    """A category rating list, or None when the catalog should answer."""
    q = question or ""
    if asks_taxonomy(q):
        return None
    if not _looks_like_fund_list(q):
        return None
    from news_rag.tools import asks_funds_with_sector_exposure

    if asks_funds_with_sector_exposure(q) and not _label_in(q) and not _SCORE_RE.search(q):
        return None

    match = match_scheme_category(q)
    label = _label_in(q)
    window = _return_window(q) if _RETURN_RE.search(q) else ""
    direction = _return_direction(q, label, window)
    above = _ABOVE_RE.search(q)
    min_score = float(above.group(1)) if above and _SCORE_RE.search(q) else None
    highest_score = bool(_SCORE_RE.search(q) and _HIGHEST_RE.search(q) and not window)
    amc = _amc_outside_label(q, label)
    fund_type = match.fund_type if match else ""
    category = match.category if match else ""
    locked = bool(match and match.locked)
    has_rating_filter = bool(label or min_score is not None or highest_score or window)
    if not explicit_fund_count(q) and not re.search(r"\brandom\b", q, re.I) and not has_rating_filter:
        return None
    if amc and not has_rating_filter:
        return None
    if not fund_type and not has_rating_filter:
        return None
    if not fund_type:
        fund_type = "equity"
    count = explicit_fund_count(q)
    if count is None:
        count = 1 if (highest_score or direction in {"highest", "lowest"}) else 5
    return RatingScreenSpec(
        count=count,
        fund_type=fund_type,
        category=category,
        locked=locked,
        label=label,
        min_score=min_score,
        highest_score=highest_score,
        return_window=window,
        return_direction=direction,
        compare_category=bool(re.search(r"\bcategory\s+averages?\b|\bcompare\b", q, re.I)),
        random_sample=bool(re.search(r"\brandom\b", q, re.I)),
        amc=amc,
    )


def asks_rating_list(question: str) -> bool:
    return parse_rating_screen(question) is not None


def _public_row(raw: dict[str, Any], *, fund_type: str, category: str) -> dict[str, Any] | None:
    isin = str(raw.get("isin") or "").strip().upper()
    if not isin:
        return None
    inputs = raw.get("inputs") if isinstance(raw.get("inputs"), dict) else {}
    try:
        score = round(float(raw.get("finalScore")), 2)
    except (TypeError, ValueError):
        score = None
    name = _catalog_name(isin) or str(raw.get("fundName") or isin).strip()
    row = {
        "isin": isin,
        "fund_name": name,
        "final_score": score,
        "rs_label": str(raw.get("label") or "").strip(),
        "category": str(raw.get("schemeCategory") or category).strip(),
        "fund_type": str(raw.get("fundType") or fund_type).strip(),
        "benchmark": str(raw.get("benchmark") or "").strip(),
        "as_on": str(raw.get("asOnDate") or "").strip(),
    }
    for field, key in (("1Y", "trailing1Y"), ("3Y", "trailing3Y"), ("5Y", "trailing5Y")):
        try:
            row[f"_trail_{field}"] = float(inputs.get(key))
        except (TypeError, ValueError):
            row[f"_trail_{field}"] = None
    for field, key in (("1y", "categoryAvg1Y"), ("3y", "categoryAvg3Y"), ("5y", "categoryAvg5Y")):
        try:
            row[f"category_avg_{field}_pct"] = round(float(inputs.get(key)), 2)
        except (TypeError, ValueError):
            pass
    return row


def _catalog_name(isin: str) -> str:
    try:
        from news_rag.fund_search import get_fund_index

        entry = get_fund_index().catalog_entry(isin) or {}
    except Exception:
        return ""
    return str(entry.get("fund_name") or "").strip()


def _amc_matches(isin: str, amc: str) -> bool:
    if not amc:
        return True
    try:
        from news_rag.fund_search import get_fund_index

        entry = get_fund_index().catalog_entry(isin) or {}
    except Exception:
        return False
    name = f"{entry.get('amc') or ''} {entry.get('fund_name') or ''}".lower()
    return amc.lower() in name


def fetch_category_ratings(fund_type: str, category: str) -> dict[str, Any]:
    """One category. A failed call returns an empty payload so the walk can continue."""
    key = (fund_type, category)
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < _CACHE_TTL_SEC:
            return deepcopy(hit[1])
    url = _RATING_URL.format(fund_type=quote(fund_type, safe=""), category=quote(category, safe=""))
    try:
        response = httpx.get(url, timeout=_HTTP_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        logger.info("category rating skipped %s/%s: %s", fund_type, category, exc)
        return {}
    if not isinstance(payload, dict):
        return {}
    with _cache_lock:
        _cache[key] = (now, deepcopy(payload))
    return deepcopy(payload)


def _rows_from_payload(payload: dict[str, Any], *, fund_type: str, category: str) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    ratings = data.get("ratings") if isinstance(data, dict) else None
    if not isinstance(ratings, list):
        return []
    rows: list[dict[str, Any]] = []
    for raw in ratings:
        if not isinstance(raw, dict):
            continue
        row = _public_row(raw, fund_type=fund_type, category=category)
        if row is not None:
            rows.append(row)
    return rows


def _keep(row: dict[str, Any], spec: RatingScreenSpec) -> bool:
    if spec.amc and not _amc_matches(str(row.get("isin") or ""), spec.amc):
        return False
    if spec.label and str(row.get("rs_label") or "") != spec.label:
        return False
    if spec.min_score is not None:
        score = row.get("final_score")
        if score is None or float(score) < spec.min_score:
            return False
    return True


def _strip(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if not str(key).startswith("_")}


def _price(rows: list[dict[str, Any]], window: str) -> list[dict[str, Any]]:
    from news_rag.tools import enrich_rankings_with_nav

    if not rows:
        return []
    enriched = enrich_rankings_with_nav(
        [_strip(row) | {"_trail_keep": row.get(f"_trail_{window}")} for row in rows],
        direction="any",
        top_n=len(rows),
        sort_by="exposure",
        return_window=window,
    )
    field = {"1Y": "return_1y_pct", "3Y": "return_3y_pct", "5Y": "return_5y_pct"}.get(window, "return_1y_pct")
    for row in enriched:
        row.pop("_trail_keep", None)
        row["_return"] = row.get(field)
    return enriched


def _shortlist(rows: list[dict[str, Any]], spec: RatingScreenSpec) -> list[dict[str, Any]]:
    key = f"_trail_{spec.return_window}"
    usable = [row for row in rows if row.get(key) is not None]
    if spec.return_direction == "positive":
        usable = [row for row in usable if float(row[key]) > 0][:_POSITIVE_CAP]
        return usable
    reverse = spec.return_direction != "lowest"
    usable.sort(key=lambda row: float(row[key]), reverse=reverse)
    return usable[:_SHORTLIST]


def _order(rows: list[dict[str, Any]], spec: RatingScreenSpec) -> list[dict[str, Any]]:
    pool = list(rows)
    if spec.random_sample:
        random.shuffle(pool)
        return pool
    if spec.return_window and spec.return_direction:
        pool.sort(key=lambda row: float(row.get("_return") or -10**9), reverse=spec.return_direction != "lowest")
        return pool
    pool.sort(key=lambda row: float(row.get("final_score") or -1), reverse=True)
    return pool


def run_rating_list(
    question: str,
    *,
    fetch: Callable[[str, str], dict[str, Any]] | None = None,
    price: Callable[[list[dict[str, Any]], str], list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    spec = parse_rating_screen(question)
    if spec is None:
        return {"success": False, "rankings": [], "ranking_note": ""}
    loader = fetch or fetch_category_ratings
    pricer = price or _price
    if spec.locked:
        names = [spec.category] if spec.category else []
    elif spec.walks:
        names = list(categories_for(spec.fund_type))
    else:
        names = list(categories_for(spec.fund_type)[:1])
    picked: list[dict[str, Any]] = []
    seen: set[str] = set()
    called: list[str] = []
    priced: list[str] = []

    for category in names:
        payload = loader(spec.fund_type, category)
        called.append(category)
        rows = [row for row in _rows_from_payload(payload, fund_type=spec.fund_type, category=category) if _keep(row, spec)]
        if spec.return_window and spec.return_direction:
            if spec.return_direction in {"highest", "lowest"} and len(picked) >= spec.count:
                trail_key = f"_trail_{spec.return_window}"
                trails = [float(row[trail_key]) for row in rows if row.get(trail_key) is not None]
                if trails:
                    best_trail = min(trails) if spec.return_direction == "lowest" else max(trails)
                    worst = _nth_return(picked, spec.count, lowest=spec.return_direction == "lowest")
                    if worst is not None and (
                        (spec.return_direction == "lowest" and best_trail > worst)
                        or (spec.return_direction != "lowest" and best_trail < worst)
                    ):
                        continue
            short = _shortlist(rows, spec)
            priced.extend(str(row.get("isin") or "") for row in short)
            rows = pricer(short, spec.return_window)
            if spec.return_direction == "positive":
                rows = [row for row in rows if row.get("_return") is not None and float(row["_return"]) > 0]
        ordered = _order(rows, spec)
        for row in ordered:
            isin = str(row.get("isin") or "")
            if not isin or isin in seen:
                continue
            seen.add(isin)
            picked.append(row)
            if not spec.walks and not spec.highest_score and spec.return_direction not in {"highest", "lowest"}:
                if len(picked) >= spec.count:
                    break
        if spec.locked:
            break
        if spec.walks and spec.return_direction not in {"highest", "lowest"} and not spec.highest_score:
            if len(picked) >= spec.count:
                break

    picked = _order(picked, spec)[: spec.count]
    public = [_strip(row) for row in picked]
    if spec.return_window and not spec.return_direction:
        public = [_strip(row) for row in pricer(public, spec.return_window)]
        priced.extend(str(row.get("isin") or "") for row in public)
    try:
        from news_rag.tools import _attach_screen_facts

        _attach_screen_facts(public, question)
    except Exception:
        logger.info("rating screen facts skipped", exc_info=True)
    _keep_asked_return(public, spec.return_window)
    _add_category_comparison(public, spec)
    note = _note(spec, len(public))
    return {
        "success": True,
        "screen_type": "rs_rating",
        "rankings": public,
        "ranking_note": note,
        "categories_called": called,
        "priced_isins": priced,
        "count": len(public),
        "return_window": spec.return_window,
    }


def _keep_asked_return(rows: list[dict[str, Any]], window: str) -> None:
    if not window:
        return
    from news_rag.tools import _RETURN_FIELDS

    keep = _RETURN_FIELDS.get(window, "")
    if not keep:
        return
    for row in rows:
        for key in list(row):
            if key.startswith("return_") and key != keep:
                row.pop(key, None)


def _add_category_comparison(rows: list[dict[str, Any]], spec: RatingScreenSpec) -> None:
    asked = spec.return_window or "1Y"
    pairs = {
        "1Y": ("return_1y_pct", "category_avg_1y_pct", "vs_category_1y_pct"),
        "3Y": ("return_3y_pct", "category_avg_3y_pct", "vs_category_3y_pct"),
        "5Y": ("return_5y_pct", "category_avg_5y_pct", "vs_category_5y_pct"),
    }
    fund_key, avg_key, vs_key = pairs.get(asked, ("", "", ""))
    for row in rows:
        if not spec.compare_category:
            for key in list(row):
                if key.startswith("category_avg_") or key.startswith("vs_category_"):
                    row.pop(key, None)
            continue
        for key in list(row):
            if key.startswith("category_avg_") and key != avg_key:
                row.pop(key, None)
        fund_return = row.get(fund_key)
        average = row.get(avg_key)
        if fund_return is None or average is None:
            continue
        row[vs_key] = round(float(fund_return) - float(average), 2)


def _nth_return(rows: list[dict[str, Any]], count: int, *, lowest: bool) -> float | None:
    values = [float(row["_return"]) for row in rows if row.get("_return") is not None]
    if len(values) < count:
        return None
    values.sort(reverse=not lowest)
    return values[count - 1]


def _note(spec: RatingScreenSpec, found: int) -> str:
    parts: list[str] = []
    if found < spec.count:
        if spec.locked:
            label = spec.label or spec.category
            parts.append(f"This category has {found} {label} fund(s). There are no more.")
        else:
            parts.append(f"Found {found} matching funds.")
    if spec.compare_category and spec.return_window:
        parts.append(
            f"The {spec.return_window} return is the fund's own NAV return. "
            "Category avg is that category's average. vs category is the difference."
        )
    return " ".join(parts)


def rating_list_plan(question: str):
    from news_rag.insight.contracts import AnswerMode, ExecutionPlan, QueryClass, ToolCall, Wave2Policy

    spec = parse_rating_screen(question)
    count = spec.count if spec else 5
    return ExecutionPlan(
        intent="lookup",
        query_class=QueryClass.SIMPLE,
        answer_mode=AnswerMode.DATA_ONLY,
        funds=[],
        goal="Category RS rating list.",
        presentation_notes=(
            "Use the fund screen table. The RS label and score come from the API. "
            "A return column is the NAV-history return. "
            "If the note says the category has fewer funds, do not add more."
        ),
        tool_calls=[
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"top_n": count, "rating_screen": True},
                why="Category RS rating screen.",
                required=True,
            )
        ],
        wave_2_policy=Wave2Policy(trigger="none"),
        max_words=220,
        direct_reply="",
        confidence=0.98,
        routed_by="slot_router",
    )


def _followup_modules(question: str) -> list[str]:
    """Facts about the chosen fund that a rating row does not contain."""
    text = question or ""
    modules: list[str] = []
    if re.search(r"\b(?:historical|past)\s+returns?\b|\breturn\s+history\b", text, re.I):
        modules.append("return_series")
    if re.search(r"\brisk\s+analysis\b|\bhow\s+risky\b|\brisk\s+of\s+(?:the|this)\s+fund\b", text, re.I):
        modules.append("risk")
        from news_rag.fund_risk import include_drawdown_with_risk

        if include_drawdown_with_risk(text):
            modules.append("drawdown")
    return modules


def _keep_followup_plan(plan, spec: RatingScreenSpec, modules: list[str]) -> None:
    """The planner already covers later parts. Stamp the rating screen and keep them."""
    from news_rag.insight.contracts import AnswerMode, ToolCall

    screen = next((call for call in plan.tool_calls if call.tool == "screen_funds_by_exposure"), None)
    if screen is None:
        screen = ToolCall(
            tool="screen_funds_by_exposure",
            arguments={"top_n": spec.count, "rating_screen": True},
            why="Pick the rated fund, then load the later facts.",
            required=True,
        )
        plan.tool_calls = [screen, *plan.tool_calls]
    screen.arguments["rating_screen"] = True
    screen.arguments["top_n"] = spec.count
    if modules:
        plan.tool_calls = [call for call in plan.tool_calls if call.tool != "search_financial_news"]
        call = next((item for item in plan.tool_calls if item.tool == "get_fund_data"), None)
        if call is None:
            call = ToolCall(tool="get_fund_data", arguments={"modules": []}, wave=1)
            plan.tool_calls.append(call)
        call.wave = 1
        current = [str(name) for name in (call.arguments.get("modules") or [])]
        for name in modules:
            if name not in current:
                current.append(name)
        call.arguments["modules"] = current
        if "drawdown" in current and not call.arguments.get("periods"):
            call.arguments["periods"] = ["1y", "3y", "5y"]
    plan.concept_brief = ""
    plan.direct_reply = ""
    plan.requires_compose = True
    plan.answer_mode = AnswerMode.DATA_ONLY
    if (plan.max_words or 0) < 320:
        plan.max_words = 320
    note = (
        "Answer every part. Name the fund from the screen. "
        "Historical returns and the risk read come from the fund data."
    )
    if note not in (plan.presentation_notes or ""):
        plan.presentation_notes = f"{plan.presentation_notes} {note}".strip()


def _user_named_funds(question: str, funds: list[str]) -> list[str]:
    """Keep a scheme only when the user wrote its name. A category list must not invent one."""
    text = (question or "").lower()
    kept: list[str] = []
    skip = {"fund", "funds", "growth", "regular", "plan", "direct", "elss", "tax", "saver"}
    for name in funds:
        tokens = [
            word
            for word in re.findall(r"[a-z0-9]+", name.lower())
            if len(word) > 3 and word not in skip
        ]
        if tokens and any(word in text for word in tokens[:2]):
            kept.append(name)
    return kept


def _difference_brief(question: str) -> str:
    if not re.search(r"\b(?:different|difference|unlike|compared with|versus|vs)\b", question or "", re.I):
        return ""
    match = match_scheme_category(question)
    if match is None or not match.category:
        return ""
    notes = {
        "elss": (
            "ELSS is an equity fund with a lock-in of 3 years. "
            "The amount invested can be claimed under Section 80C, up to that section's limit. "
            "Other equity funds, such as large cap or flexi cap, do not have this lock-in and are not Section 80C products."
        ),
    }
    return notes.get(match.category, "")


def _apply_category_difference(question: str, plan) -> None:
    brief = _difference_brief(question)
    if not brief:
        return
    plan.concept_brief = brief
    plan.requires_compose = True
    plan.direct_reply = ""
    plan.funds = _user_named_funds(question, list(plan.funds or []))
    if (plan.max_words or 0) < 220:
        plan.max_words = 220
    note = "Name the funds from the screen when it has them. Then explain the difference from the concept brief."
    if note not in (plan.presentation_notes or ""):
        plan.presentation_notes = f"{plan.presentation_notes} {note}".strip()


def ensure_rating_screen(question: str, plan) -> None:
    """A rating list uses the category API. Later facts about that fund stay on the plan."""
    spec = parse_rating_screen(question)
    if spec is None:
        _apply_category_difference(question, plan)
        return
    from news_rag.insight.contracts import AnswerMode, ToolCall

    follow = _followup_modules(question)
    others = [call for call in plan.tool_calls if call.tool != "screen_funds_by_exposure"]
    if follow or ((plan.routed_by or "") == "planner" and (others or len(plan.sub_queries) > 1)):
        _keep_followup_plan(plan, spec, follow)
    else:
        plan.funds = []
        plan.direct_reply = ""
        plan.concept_brief = ""
        plan.answer_mode = AnswerMode.DATA_ONLY
        plan.requires_compose = False
        plan.tool_calls = [
            ToolCall(
                tool="screen_funds_by_exposure",
                arguments={"top_n": spec.count, "rating_screen": True},
                why="Category RS rating screen.",
                required=True,
            )
        ]
    _apply_category_difference(question, plan)
