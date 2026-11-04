"""Trailing maximum drawdown for one fund, from the RupeeStop admin endpoint."""

from __future__ import annotations

import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

from news_rag.rupeestop_auth import rupeestop_admin_request_headers

from news_rag.fund_search import resolve_canonical_isin

logger = logging.getLogger(__name__)

_DRAWDOWN_URL = "https://backend.rupeestop.com/api/v1/admin/drawdown/trailing"
_PERIODS = ("1y", "3y", "5y", "10y", "inception")
_DEFAULT_PERIODS = ("1y", "3y", "5y")
_PERIOD_LABELS = {
    "1y": "1Y",
    "3y": "3Y",
    "5y": "5Y",
    "10y": "10Y",
    "inception": "Since start",
}
_TTL_SEC = 3600.0
_PEER_LIMIT = 30

_cache: dict[tuple[str, str], tuple[float, dict[str, Any] | None]] = {}
_lock = threading.Lock()

_DRAWDOWN_RE = re.compile(
    r"\b(?:"
    r"draw\s*downs?|draw\s*backs?|fall\s*backs?|"
    r"fall(?:en|ing)?\s+down|fell\s+down|"
    r"worst\s+down|worst\s+fall|worst\s+drop|"
    r"biggest\s+(?:fall|drop)|max(?:imum)?\s+fall|"
    r"max(?:imum)?\s+draw\s*downs?|"
    r"peak[\s-]*to[\s-]*trough|underwater|"
    r"fallen\s+from\s+(?:its|the)\s+peak|"
    r"still\s+below\s+(?:its|the)\s+(?:previous\s+)?peak|from\s+its\s+peak"
    r")\b",
    re.I,
)
_WHY_FALL_RE = re.compile(r"\bwhy\b", re.I)
_FALL_RE = re.compile(r"\b(?:fall|fell|fallen|drop(?:ped)?|drawdowns?)\b", re.I)
_PERFORMANCE_RE = re.compile(
    r"\b(?:performance|performing|how\s+(?:is|has|did)|returns?)\b",
    re.I,
)
_OVERVIEW_RE = re.compile(r"\btell\s+me\s+about\b|\boverview\b", re.I)
_MANAGER_RE = re.compile(r"\bfund\s+managers?\b|\bwho\s+manages\b|\bmanaged\s+by\b", re.I)
_CURRENT_RE = re.compile(
    r"\b(?:currently\s+in\s+a\s+drawdown|current\s+drawdown|"
    r"fallen\s+from\s+(?:its|the)\s+peak|still\s+below\s+(?:its|the)\s+(?:previous\s+)?peak)\b",
    re.I,
)
_DEFINITION_RE = re.compile(
    r"\bwhat\s+does\b.*\bdrawdown\b|\bwhat\s+is\s+a\s+drawdown\b|\bdrawdown\s+mean\b",
    re.I,
)
_CATEGORY_RE = re.compile(r"\b(?:category|peers|similar\s+funds|other\s+funds)\b", re.I)
_LONGEST_RE = re.compile(r"\blongest\s+drawdown\b|\blongest\s+fall\b", re.I)
_SUITABILITY_RE = re.compile(r"\brisk\s+tolerance\b|\bshould\s+i\s+(?:invest|buy)\b|\bfit\s+my\b", re.I)
_UNSUPPORTED_YEAR_RE = re.compile(
    r"\b(?:2|4|6|7|8|9|15|20)\s*[- ]?\s*(?:y|yr|yrs|year|years)\b",
    re.I,
)
_INCEPTION_RE = re.compile(
    r"\binception\b|\bsince\s+(?:the\s+)?(?:launch|start)\b|\bstart\s+date\b|"
    r"\bdate\s+of\s+starting\b|\bfund\s+started\b|\bsince\s+(?:it|the\s+fund)\s+started\b",
    re.I,
)
_TEN_RE = re.compile(r"\b10\s*[- ]?\s*(?:y|yr|yrs|year|years)\b|\bten\s+years?\b", re.I)
_AMOUNT_RE = re.compile(
    r"(?:₹|\brs\.?\b|\binr\b)\s*(\d+(?:,\d+)*(?:\.\d+)?)(?:\s*(lakh|lac|crore|cr))?|"
    r"(\d+(?:,\d+)*(?:\.\d+)?)\s*(lakh|lac|crore|cr)\b",
    re.I,
)
_NEWS_RE = re.compile(r"\b(?:news|why|headline)\b", re.I)

_UNAVAILABLE = "Drawdown is available for 1, 3, 5, and 10 years, and since the fund started."
_DEFINITION = (
    "A maximum drawdown is the largest peak-to-trough fall in NAV over the period you pick. "
    "A fall of 20% means the NAV went from a high to a later low that was 20% lower. "
    "That is not the same as the current gap. The current gap is how far the latest NAV "
    "still sits under that peak, after any bounce."
)


def drawdown_words(question: str) -> bool:
    return bool(_DRAWDOWN_RE.search(question or ""))


def is_drawdown_definition(question: str) -> bool:
    return bool(_DEFINITION_RE.search(question or ""))


def asks_category_drawdown(question: str) -> bool:
    q = question or ""
    return bool(_CATEGORY_RE.search(q) and drawdown_words(q))


def _named_standard_periods(question: str) -> list[str]:
    q = question or ""
    found: list[str] = []
    checks = (
        ("1y", r"\b(?:1|one)\s*[- ]?\s*(?:y|yr|yrs|year|years)\b|\blast\s+year\b"),
        ("3y", r"\b(?:3|three)\s*[- ]?\s*(?:y|yr|yrs|year|years)\b"),
        ("5y", r"\b(?:5|five)\s*[- ]?\s*(?:y|yr|yrs|year|years)\b"),
    )
    for period, pattern in checks:
        if re.search(pattern, q, re.I):
            found.append(period)
    return found


def periods_for_question(question: str, *, comparison: bool) -> tuple[list[str], str]:
    """Horizons to fetch. Comparisons never include 10Y or since start."""
    q = question or ""
    note = _UNAVAILABLE if _UNSUPPORTED_YEAR_RE.search(q) else ""
    named = _named_standard_periods(q)
    if comparison:
        return (named or list(_DEFAULT_PERIODS), note)

    if _CURRENT_RE.search(q) and not named and not _TEN_RE.search(q) and not _INCEPTION_RE.search(q):
        return ["1y"], note

    extra: list[str] = []
    if _TEN_RE.search(q):
        extra.append("10y")
    if _INCEPTION_RE.search(q):
        extra.append("inception")
    if named:
        return named + extra, note
    if extra:
        return list(_DEFAULT_PERIODS) + extra, note
    if note:
        return [], note
    return list(_DEFAULT_PERIODS), note


def normalize_drawdown_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(data, dict) or data.get("maxDrawdown") is None:
        return None
    recovery = data.get("recovery") if isinstance(data.get("recovery"), dict) else {}
    speed = data.get("fallVsRecoverySpeed") if isinstance(data.get("fallVsRecoverySpeed"), dict) else {}
    try:
        max_drawdown = round(float(data["maxDrawdown"]), 2)
    except (TypeError, ValueError):
        return None
    return {
        "isin": str(data.get("isin") or "").strip().upper(),
        "fund_name": str(data.get("fundName") or "").strip(),
        "period": str(data.get("period") or "").strip().lower(),
        "max_drawdown": max_drawdown,
        "peak_date": data.get("peakDate"),
        "peak_date_label": data.get("peakDateLabel") or "",
        "peak_nav": data.get("peakNav"),
        "trough_date": data.get("troughDate"),
        "trough_date_label": data.get("troughDateLabel") or "",
        "trough_nav": data.get("troughNav"),
        "recovered": bool(recovery.get("recovered")),
        "recovery_date_label": recovery.get("recoveryDateLabel"),
        "recovery_time_days": recovery.get("recoveryTimeDays"),
        "drawdown_duration_days": recovery.get("drawdownDurationDays"),
        "days_underwater": recovery.get("daysUnderwater"),
        "current_pct_below_peak": recovery.get("currentPctBelowPeak"),
        "fall_days": speed.get("fallDays"),
    }


def fetch_trailing_drawdown(isin: str, period: str, *, timeout: float = 12.0) -> dict[str, Any] | None:
    isin_clean = resolve_canonical_isin((isin or "").strip().upper())
    period_clean = str(period or "").strip().lower()
    if not isin_clean or period_clean not in _PERIODS:
        return None
    now = time.time()
    key = (isin_clean, period_clean)
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > now:
            cached = hit[1]
            return dict(cached) if isinstance(cached, dict) else cached
    try:
        headers = rupeestop_admin_request_headers(_DRAWDOWN_URL)
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(_DRAWDOWN_URL, params={"isin": isin_clean, "period": period_clean}, headers=headers)
            if resp.status_code != 200:
                logger.warning("drawdown API status %s for %s %s", resp.status_code, isin_clean, period_clean)
                return None
            normalized = normalize_drawdown_payload(resp.json())
    except Exception as exc:
        logger.warning("drawdown fetch failed for %s %s: %s", isin_clean, period_clean, exc)
        return None
    with _lock:
        _cache[key] = (now + _TTL_SEC, normalized)
    return dict(normalized) if isinstance(normalized, dict) else normalized


def fetch_drawdown_periods(isin: str, periods: list[str]) -> list[dict[str, Any]]:
    wanted = [p for p in periods if p in _PERIODS]
    if not isin or not wanted:
        return []
    with ThreadPoolExecutor(max_workers=min(5, len(wanted))) as pool:
        rows = list(pool.map(lambda period: fetch_trailing_drawdown(isin, period), wanted))
    by_period = {row["period"]: row for row in rows if isinstance(row, dict)}
    return [by_period[period] for period in wanted if period in by_period]


def collapse_episodes(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep one block when two horizons share the same peak and trough."""
    groups: list[dict[str, Any]] = []
    for episode in episodes:
        key = (episode.get("peak_date"), episode.get("trough_date"), episode.get("max_drawdown"))
        if groups and groups[-1]["key"] == key:
            groups[-1]["periods"].append(episode.get("period"))
            continue
        groups.append({"key": key, "periods": [episode.get("period")], "episode": episode})
    return groups


def _period_heading(periods: list[str]) -> str:
    labels = [_PERIOD_LABELS.get(str(period), str(period).upper()) for period in periods if period]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return ", ".join(labels)


def _money(value: Any) -> str:
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return ""


def status_phrase(episode: dict[str, Any]) -> str:
    if episode.get("recovered"):
        when = episode.get("recovery_date_label") or "a later date"
        return f"recovered on {when}"
    pct = episode.get("current_pct_below_peak")
    days = episode.get("days_underwater")
    if pct is None:
        return "not recovered"
    if days is None:
        return f"still {float(pct):.2f}% below the peak"
    return f"still {float(pct):.2f}% below the peak, {int(days)} days"


def screen_drawdown_cell(episode: dict[str, Any]) -> str:
    fall = abs(float(episode.get("max_drawdown") or 0))
    return f"{fall:.2f}% · {status_phrase(episode)}"


def average_peer_drawdown(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def peer_gap_sentence(fund_drawdown: float, peer_average: float, count: int, truncated: bool) -> str:
    gap = round(abs(peer_average) - abs(fund_drawdown), 2)
    scope = f"{count} other funds" if truncated or count else "other funds"
    if gap > 0:
        relation = f"{gap:.2f} percentage points shallower"
    elif gap < 0:
        relation = f"{abs(gap):.2f} percentage points deeper"
    else:
        relation = "the same size"
    return (
        f"The average worst fall of {scope} in this category was {abs(peer_average):.2f}%. "
        f"This fund's fall was {relation}."
    )


def investment_amount(question: str) -> float | None:
    q = question or ""
    if not re.search(r"\b(?:invest\w*|lose|lost|loss)\b", q, re.I):
        return None
    match = _AMOUNT_RE.search(q)
    if not match:
        return None
    raw = match.group(1) or match.group(3) or ""
    try:
        amount = float(raw.replace(",", ""))
    except ValueError:
        return None
    unit = (match.group(2) or match.group(4) or "").lower()
    if unit in ("lakh", "lac"):
        amount *= 100_000
    elif unit in ("crore", "cr"):
        amount *= 10_000_000
    if amount <= 0:
        return None
    return amount


def rupee_loss(amount: float, max_drawdown: float) -> float:
    return round(amount * abs(max_drawdown) / 100.0, 2)


def _rupee_line(question: str, episode: dict[str, Any]) -> str:
    amount = investment_amount(question)
    if amount is None or episode.get("max_drawdown") is None:
        return ""
    loss = rupee_loss(amount, float(episode["max_drawdown"]))
    return (
        f"On ₹{amount:,.0f} invested before that peak, the loss at the trough would have been "
        f"₹{loss:,.2f}. That is the historical fall on that amount, not a forecast."
    )


def render_drawdown_body(payload: dict[str, Any] | None, question: str = "") -> str:
    if not isinstance(payload, dict):
        return ""
    episodes = [row for row in (payload.get("episodes") or []) if isinstance(row, dict)]
    if not episodes:
        note = str(payload.get("note") or "").strip()
        return note
    lines: list[str] = []
    name = str(payload.get("fund_name") or "").strip()
    if name:
        lines.append(name)
    note = str(payload.get("note") or "").strip()
    if note:
        lines.append(note)
    money_added = False
    if payload.get("longest_check"):
        lines.append(
            "These figures are the deepest fall in each period, not a list of every fall, "
            "so they do not identify the longest drawdown."
        )
    for group in collapse_episodes(episodes):
        episode = group["episode"]
        heading = _period_heading(group["periods"])
        fall = abs(float(episode.get("max_drawdown") or 0))
        peak = _money(episode.get("peak_nav"))
        trough = _money(episode.get("trough_nav"))
        peak_on = episode.get("peak_date_label") or "the peak"
        trough_on = episode.get("trough_date_label") or "the low"
        path = f"from {peak} on {peak_on} to {trough} on {trough_on}".replace("  ", " ")
        lines.append(f"**{heading}:** worst fall {fall:.2f}%, {path}.")
        if episode.get("recovered"):
            fall_days = episode.get("fall_days")
            back_days = episode.get("recovery_time_days")
            sentence = f"Recovered on {episode.get('recovery_date_label') or 'a later date'}."
            if fall_days is not None and back_days is not None:
                sentence += f" It fell for {int(fall_days)} days and took {int(back_days)} days to get back."
            lines.append(sentence)
        else:
            lines.append(f"It has not recovered. {status_phrase(episode).capitalize()}.")
        if episode.get("category_sentence"):
            lines.append(str(episode["category_sentence"]))
        money = _rupee_line(question, episode)
        if money and not money_added:
            lines.append(money)
            money_added = True
    if payload.get("current_check") and episodes and episodes[0].get("recovered"):
        lines.append(
            "The worst fall in the last year has been repaired. "
            "This feed does not report a separate distance from a later high."
        )
    if _SUITABILITY_RE.search(question or ""):
        lines.append(
            "This is what happened in that period. It does not say whether the fund fits a risk tolerance, "
            "and it is not a forecast of the next fall."
        )
    return "\n".join(lines)


def _peer_average_for_period(isin: str, period: str, category: str) -> tuple[float | None, int, bool]:
    from news_rag.fund_search import get_fund_index

    peers, truncated = get_fund_index().isins_in_category(category, exclude_isin=isin, limit=_PEER_LIMIT)
    if not peers:
        return None, 0, False
    with ThreadPoolExecutor(max_workers=min(8, len(peers))) as pool:
        rows = list(pool.map(lambda peer: fetch_trailing_drawdown(peer, period), peers))
    values = [float(row["max_drawdown"]) for row in rows if isinstance(row, dict) and row.get("max_drawdown") is not None]
    return average_peer_drawdown(values), len(values), truncated


def load_fund_drawdown(fund_name: str, periods: list[str], question: str = "", *, include_category: bool = False) -> dict[str, Any]:
    from news_rag.fund_search import get_fund_index, resolve_fund_for_query

    detail, _ambiguous, _close = resolve_fund_for_query(fund_name)
    isin = str((detail or {}).get("isin") or "").strip().upper()
    catalog = get_fund_index().catalog_entry(isin) if isin else None
    category = str((catalog or {}).get("category") or (detail or {}).get("category") or "").strip()
    resolved, note = periods_for_question(question, comparison=False)
    wanted = [period for period in periods if period in _PERIODS] or resolved
    episodes = fetch_drawdown_periods(isin, wanted) if isin else []
    if include_category and isin and category:
        for episode in episodes:
            if str(episode.get("period") or "") not in _DEFAULT_PERIODS:
                continue
            try:
                average, count, truncated = _peer_average_for_period(
                    isin, str(episode.get("period") or ""), category
                )
            except Exception as exc:
                logger.warning("category drawdown average failed for %s: %s", isin, exc)
                continue
            if average is None:
                continue
            episode["category_sentence"] = peer_gap_sentence(
                float(episode["max_drawdown"]), average, count, truncated
            )
    fund_label = ""
    if episodes:
        fund_label = str(episodes[0].get("fund_name") or "")
    if not fund_label:
        fund_label = str((detail or {}).get("fund_short_name") or (detail or {}).get("fund_name") or fund_name)
    return {
        "fund_name": fund_label,
        "isin": isin,
        "periods": wanted,
        "episodes": episodes,
        "note": note,
        "current_check": bool(_CURRENT_RE.search(question or "")),
        "longest_check": bool(_LONGEST_RE.search(question or "")),
        "question": question or "",
    }


def ensure_drawdown_tools(question: str, plan: Any) -> Any:
    """Add the drawdown fetch for a fund, a comparison, or a screen. Leave news in place."""
    from news_rag.insight.contracts import AnswerMode, ToolCall, Wave2Policy
    from news_rag.insight.multi_fact import requested_fund_facts
    from news_rag.insight.planner_policy import planner_owns

    if planner_owns(plan):
        return plan
    q = question or ""
    if is_drawdown_definition(q):
        plan.tool_calls = []
        plan.direct_reply = _DEFINITION
        plan.answer_mode = AnswerMode.DATA_ONLY
        plan.requires_compose = False
        plan.wave_2_policy = Wave2Policy(trigger="none")
        return plan

    tools = [call.tool for call in plan.tool_calls]
    has_screen = "screen_funds_by_exposure" in tools
    has_compare = "compare_funds" in tools
    wants = _question_needs_drawdown(q, plan, has_screen=has_screen, has_compare=has_compare)
    if not wants:
        return plan

    periods, note = periods_for_question(q, comparison=has_screen or has_compare)
    if note:
        plan.presentation_notes = f"{plan.presentation_notes} {note}".strip()
    if has_screen:
        return plan
    if has_compare:
        for call in plan.tool_calls:
            if call.tool == "compare_funds":
                call.arguments = {**(call.arguments or {}), "drawdown_periods": periods}
        return plan
    if not periods:
        plan.tool_calls = []
        plan.direct_reply = note or _UNAVAILABLE
        plan.answer_mode = AnswerMode.DATA_ONLY
        plan.requires_compose = False
        plan.wave_2_policy = Wave2Policy(trigger="none")
        return plan

    why = bool(_NEWS_RE.search(q))
    overview = bool(_OVERVIEW_RE.search(q)) and not drawdown_words(q)
    precise = not why and not overview
    include_category = asks_category_drawdown(q) and not has_compare and not has_screen
    _add_drawdown_call(
        plan,
        periods,
        include_category=include_category,
        also_snapshot=(precise and bool(_PERFORMANCE_RE.search(q))) or overview,
        tool_call=ToolCall,
    )
    if precise:
        plan.answer_mode = AnswerMode.DATA_ONLY
        plan.requires_compose = False
        plan.wave_2_policy = Wave2Policy(trigger="none")
        plan.tool_calls = [
            call for call in plan.tool_calls if call.tool in ("get_fund_data", "get_portfolio_data")
        ]
        asked = set(plan.asked_facts or [])
        asked.add("drawdown")
        asked.update(requested_fund_facts(q))
        if _PERFORMANCE_RE.search(q):
            asked.add("returns")
        plan.asked_facts = sorted(asked)
        if len(plan.asked_facts) >= 2:
            plan.requires_compose = True
            plan.max_words = max(int(plan.max_words or 0), 320)
            named = ", ".join(plan.asked_facts)
            plan.presentation_notes = (
                f"{plan.presentation_notes} The user named several facts ({named}). "
                "Write one readable note that covers every fact, with a blank line between topics. "
                "Name each sector and its weight when sectors were asked. Do not use a table."
            ).strip()
        if set(plan.asked_facts) <= {"drawdown"}:
            for call in plan.tool_calls:
                if call.tool == "get_fund_data":
                    arguments = {**(call.arguments or {}), "modules": ["drawdown"], "periods": periods}
                    _set_category_flag(arguments, include_category)
                    call.arguments = arguments
    return plan


def _question_needs_drawdown(question: str, plan: Any, *, has_screen: bool, has_compare: bool) -> bool:
    from news_rag.insight.multi_fact import requested_fund_facts

    if has_compare:
        return True
    if has_screen:
        return drawdown_words(question)
    if drawdown_words(question) or (_WHY_FALL_RE.search(question) and _FALL_RE.search(question)):
        return True
    if _MANAGER_RE.search(question):
        return False
    specific = requested_fund_facts(question) - {"returns", "drawdown"}
    if specific:
        return False
    return bool(plan.funds) and bool(_PERFORMANCE_RE.search(question) or _OVERVIEW_RE.search(question))


def _add_drawdown_call(plan: Any, periods: list[str], *, include_category: bool, also_snapshot: bool, tool_call: Any) -> None:
    found = False
    for call in plan.tool_calls:
        if call.tool != "get_fund_data":
            continue
        modules = list((call.arguments or {}).get("modules") or [])
        if "drawdown" not in modules:
            modules.append("drawdown")
        arguments = {**(call.arguments or {}), "modules": modules, "periods": periods}
        _set_category_flag(arguments, include_category)
        call.arguments = arguments
        found = True
    if found:
        return
    modules = ["snapshot", "drawdown"] if also_snapshot else ["drawdown"]
    arguments: dict[str, Any] = {"modules": modules, "periods": periods}
    _set_category_flag(arguments, include_category)
    plan.tool_calls.append(tool_call(tool="get_fund_data", arguments=arguments, wave=1))


def _set_category_flag(arguments: dict[str, Any], include_category: bool) -> None:
    if include_category:
        arguments["include_category"] = True
    else:
        arguments.pop("include_category", None)


def attach_screen_drawdown(row: dict[str, Any], question: str) -> None:
    isin = str(row.get("isin") or "").strip()
    if not isin:
        return
    periods, note = periods_for_question(question, comparison=True)
    episodes = fetch_drawdown_periods(isin, periods)
    for episode in episodes:
        period = str(episode.get("period") or "")
        if period in _DEFAULT_PERIODS:
            row[f"drawdown_{period}"] = screen_drawdown_cell(episode)
    if note:
        row["drawdown_note"] = note


def compare_drawdown_rows(briefs: list[dict[str, Any]], periods: list[str]) -> dict[str, list[str]]:
    """One status cell per fund for each horizon, in brief order."""
    allowed = [period for period in periods if period in _DEFAULT_PERIODS]
    if not allowed:
        allowed = list(_DEFAULT_PERIODS)
    cells: dict[str, list[str]] = {period: [] for period in allowed}
    for brief in briefs:
        isin = str(brief.get("isin") or "").strip()
        episodes = {row["period"]: row for row in fetch_drawdown_periods(isin, allowed)}
        for period in allowed:
            episode = episodes.get(period)
            cells[period].append(screen_drawdown_cell(episode) if episode else "—")
    return cells
