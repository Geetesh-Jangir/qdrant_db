"""Public fund risk lines: official riskometer, RupeeStop score, and portfolio mix.

Pillar scores and rating inputs are dropped before anything is cached or shown.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

import httpx

from news_rag.insight.contracts import AnswerMode, ExecutionPlan, ToolCall, Wave2Policy

logger = logging.getLogger(__name__)

_RATING_URL = "https://backend.rupeestop.com/api/v1/admin/rs-rating/{isin}"
_TTL_SEC = 3600
_PILLAR_SENTENCE = (
    "It is generated from four pillars: performance against the benchmark, the category, and rolling results; "
    "risk; portfolio quality; and the fund manager."
)
_RATING_CONCEPT = (
    "The RS rating is RupeeStop's score for a mutual fund, out of 100. "
    + _PILLAR_SENTENCE
    + " Each pillar is scored out of a maximum that depends on the fund type (equity, debt, and others); "
    "do not quote fixed caps like 40/25/25/10 for every scheme unless those exact max marks are in the data for that fund. "
    "For a named fund, use the max beside each pillar score from the rating. "
    "Pillar sub-scores, weights, and the formula are not shown. "
    "The label comes with the rating: 80 to 100 Best in category, 70 to 79 Recommended, "
    "60 to 69 Good Choice, 50 to 59 Average, and 0 to 49 Underperformer. "
    "The SEBI riskometer is a separate official risk label, such as Very High. "
    "A Good Choice score is not a statement that the fund is low risk. "
    "A fund can carry a Good Choice label and still be Very High on the riskometer."
)
_SCHEME_RE = re.compile(
    r"\bINF[A-Z0-9]{8,}\b|"
    r"\b(?:hdfc|sbi|icici|axis|bandhan|nippon|kotak|mirae|parag parikh|quant|motilal|"
    r"tata|uti|dsp|franklin|invesco|edelweiss|canara|absl|aditya birla|birla|sundaram|"
    r"pgim|quantum|bajaj|hsbc|whiteoak|samco|groww|zerodha|navi|helios|mahindra|shriram)\b",
    re.I,
)
_RATING_CONCEPT_RE = re.compile(
    r"\b(?:rs|rupeestop|rupee\s*stop)\s+(?:rating|score)\b|"
    r"\bgood choice\b|\bbest in category\b|\bunderperformer\b|"
    r"\bvery high\b.{0,48}\brisk|\brisk\b.{0,48}\bvery high\b|"
    r"\bhow\b.{0,48}\b(?:measure|measured|pillars?)\b|"
    r"\bfour\s+pillars\b",
    re.I,
)
_HIDDEN_REPLY = "Internal calculations are not shown."

_RISK_RE = re.compile(
    r"\brisky\b|\brisk(?:ometer| analysis)?\b|\bsebi\b.{0,24}\brisk\b|"
    r"\brupeestop score\b|\bfinal score\b|\bgood choice\b|"
    r"\b(?:rs|rupeestop|rupee\s*stop)\s+(?:rating|score)\b",
    re.I,
)
_HIDDEN_RE = re.compile(
    r"\bhow (?:do you|is the score|are we) (?:calculat|scor)|"
    r"\bmethodology\b|\binternal (?:score|calculation)|"
    r"\b(?:sharpe|sortino)\b|"
    r"\b(?:pillar|score)\b.{0,24}\bweights?\b|"
    r"\bweights?\b.{0,24}\b(?:pillar|score)\b",
    re.I,
)
_PRIVATE_RE = re.compile(
    r"\b(?:which|what)\s+(?:llm|model|ai)\b|"
    r"\bwhat model\b|\bwhich model\b|"
    r"\b(?:system|your)\s+prompt\b|"
    r"\bapi\s+endpoint\b|\bbackend\.rupeestop\b|"
    r"\bqdrant\b|\barchitecture\b|"
    r"\bhow (?:does|do) (?:the|this|your) (?:system|pipeline|router)\b",
    re.I,
)
_PRIVATE_REPLY = "I can help with a fund, a return, or the news. I don't share how this assistant is built."
_PILLARS = (
    ("performance", "Performance", 40),
    ("risk", "Risk", 25),
    ("portfolioQuality", "Portfolio quality", 25),
    ("fundManager", "Fund manager", 10),
)
_PILLAR_SCORE_RE = re.compile(
    r"\b(?:portfolio[\s_]*quality\s+score|(?:risk|performance|fund manager)\s+pillar|pillar\s+scores?|"
    r"fund\s+quality|sharpe|sortino)\b",
    re.I,
)
_SUITABILITY_Q_RE = re.compile(
    r"\bsmall cap\b.{0,40}\bsafe\b|"
    r"\b(?:safe|conservative)\b.{0,40}\b(?:fund|investor)\b|"
    r"\b(?:fund|investor)\b.{0,40}\b(?:safe|conservative)\b",
    re.I,
)
_SCORE_ONLY_RE = re.compile(
    r"\brupeestop score\b|\bfinal score\b|\bgood choice\b|"
    r"\b(?:rs|rupeestop|rupee\s*stop)\s+(?:rating|score)\b",
    re.I,
)
_FALL_RE = re.compile(
    r"\bhow risky\b|\brisk analysis\b|\bwhy\b.{0,48}\bvery high\b|\bfallen\b|\bfall\b",
    re.I,
)
_SUITABILITY_RE = re.compile(r"\bconservative\b|\bsuitable\b|\bsafe\b|\bright for me\b", re.I)
_BAND_Q_RE = re.compile(
    r"\bhow\b.{0,48}\bcategor|"
    r"\b(?:score|rating|label)s?\b.{0,32}\b(?:bands?|ranges?|categor)|"
    r"\bwhat does\b.{0,48}\b(?:good choice|recommended|best in category|underperformer|average)\b|"
    r"\b(?:good choice|recommended|best in category|underperformer)\b.{0,24}\bmean\b|"
    r"\bwhy\b.{0,40}\b(?:good choice|recommended|best in category|underperformer)\b",
    re.I,
)
_BAND_EXPLANATION = (
    "The labels run from 80 to 100 Best in category, 70 to 79 Recommended, "
    "60 to 69 Good Choice, 50 to 59 Average, and 0 to 49 Underperformer."
)

_cache: dict[str, tuple[float, dict[str, Any]]] = {}


def asks_pillar_structure(question: str) -> bool:
    """General question about the four pillars and their maximum scores."""
    text = question or ""
    if _SCHEME_RE.search(text) and re.search(r"\b(?:of|for)\s+(?:the\s+)?[\w&]+\s+fund\b", text, re.I):
        return False
    if _PILLAR_SCORE_RE.search(text) and pillar_focus(text):
        return False
    return bool(
        re.search(
            r"\b(?:four|4)\s+pillars?\b|"
            r"\bpillars?\s+(?:and|&)\s+(?:their\s+)?(?:max|maximum)\b|"
            r"\b(?:max|maximum)\s+(?:score\s+)?(?:for\s+)?(?:each\s+)?pillars?\b|"
            r"\bwhat\s+(?:are\s+)?(?:the\s+)?(?:rupeestop\s+)?pillars?\b",
            text,
            re.I,
        )
    )


def asks_rating_concept(question: str) -> bool:
    """A question about the rating itself, not one named scheme."""
    text = question or ""
    if asks_pillar_structure(text):
        return True
    if _SCHEME_RE.search(text) or _PILLAR_SCORE_RE.search(text):
        return False
    if asks_about_score_bands(text):
        return True
    if not _RATING_CONCEPT_RE.search(text):
        return False
    if re.search(r"\b(?:of|for)\s+(?:the\s+)?[A-Z][\w&]+(?:\s+[A-Z][\w&]+){0,4}\s+fund\b", text):
        return False
    return True


def asks_about_score_bands(question: str) -> bool:
    """The ranges are an explanation. They are not used to pick a fund's label."""
    return bool(_BAND_Q_RE.search(question or ""))


def asks_hidden_rating(question: str) -> bool:
    """The formula and the rating inputs are not shown. The pillar marks are."""
    return bool(_HIDDEN_RE.search(question or ""))


def asks_private_system(question: str) -> bool:
    """Model, prompt, endpoint, and architecture questions are refused."""
    return bool(_PRIVATE_RE.search(question or ""))


def blocked_reply(question: str) -> str:
    if asks_hidden_rating(question):
        return _HIDDEN_REPLY
    if asks_private_system(question):
        return _PRIVATE_REPLY
    return ""


def asks_fund_risk(question: str) -> bool:
    if asks_hidden_rating(question):
        return False
    text = question or ""
    if _RISK_RE.search(text) or _SUITABILITY_Q_RE.search(text):
        return True
    return bool(re.search(r"\bwhy\b.{0,48}\bvery high\b|\bvery high\b.{0,24}\brisk", text, re.I))


def asks_score_only(question: str) -> bool:
    text = question or ""
    if not _SCORE_ONLY_RE.search(text):
        return False
    if re.search(r"\brisky\b|\briskometer\b|\brisk analysis\b|\bhow risky\b|\ballocation\b|\bmarket cap\b", text, re.I):
        return False
    return True


def asks_sebi_riskometer(question: str) -> bool:
    """The official SEBI risk label — not the RupeeStop risk pillar or final score."""
    text = question or ""
    if asks_hidden_rating(question):
        return False
    if not re.search(r"\bsebi\b|\briskometer\b", text, re.I):
        return False
    if re.search(r"\b(?:rupeestop|final score|good choice|pillar)\b", text, re.I):
        return False
    return True


def asks_risk_trend_comparison(question: str) -> bool:
    """Whether the fund became more or less risky than an earlier point."""
    text = question or ""
    return bool(
        re.search(
            r"\b(?:less|more|lower|higher)\s+(?:risky|risk(?:ier)?)\b|"
            r"\brisk(?:ier|iness)?\s+(?:now|today|than|compared)\b|"
            r"\b(?:less|more)\s+risk(?:ier)?\b",
            text,
            re.I,
        )
    )


def _ensure_risk_trend_plan(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """No historical riskometer in the API — one sentence for the comparison, then current risk facts."""
    plan.requires_compose = True
    plan.max_words = max(int(plan.max_words or 0), 280)
    note = (
        "The user asked if risk is lower or higher than before. "
        "When EVIDENCE has no earlier SEBI riskometer or risk-pillar history, "
        "answer that comparison in exactly one sentence: We can't get that data right now. "
        "Then state the current SEBI riskometer, risk pillar score, asset mix, and drawdown episodes "
        "(heading ### Maximum drawdown across periods) from EVIDENCE. "
        "Do not say snapshot, earlier reading, cannot show trend, supports reading current position, "
        "or that the data cannot show whether risk changed."
    )
    existing = (plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    return plan


def include_drawdown_with_risk(question: str) -> bool:
    """Drawdown rides along only when the question is about the fall or the risk label."""
    if asks_score_only(question) or asks_hidden_rating(question):
        return False
    return bool(_FALL_RE.search(question or ""))


def normalize_rating(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Keep fund type, score, max score, and the API label. Drop pillars and inputs."""
    if not isinstance(payload, dict):
        return None
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(data, dict):
        return None
    label = str(data.get("label") or "").strip()
    score = None
    if data.get("finalScore") is not None:
        try:
            score = round(float(data["finalScore"]), 2)
        except (TypeError, ValueError):
            score = None
    if score is None and not label:
        return None
    try:
        max_score = int(float(data.get("maxPossibleScore") or 100))
    except (TypeError, ValueError):
        max_score = 100
    summary: dict[str, Any] = {
        "fund_type": str(data.get("fundType") or "").strip(),
        "max_score": max_score,
        "label": label,
    }
    if score is not None:
        summary["final_score"] = score
    pillars = _public_pillars(data.get("pillars"))
    if pillars:
        summary["pillars"] = pillars
    return summary


def _pillar_maximum(block: dict[str, Any], default_max: int) -> int:
    """API uses maxScore on debt and other types; older rows may use max."""
    for key in ("maxScore", "max", "maximum", "maxPossibleScore"):
        if block.get(key) is None:
            continue
        try:
            return int(float(block[key]))
        except (TypeError, ValueError):
            continue
    return default_max


def _public_pillars(raw: Any) -> dict[str, dict[str, Any]]:
    """Score and max mark only. Inputs used to calculate a pillar are dropped."""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, label, default_max in _PILLARS:
        block = raw.get(key)
        if not isinstance(block, dict) or block.get("score") is None:
            continue
        try:
            score = round(float(block["score"]), 2)
        except (TypeError, ValueError):
            continue
        maximum = _pillar_maximum(block, default_max)
        out[key] = {"label": label, "score": score, "max": maximum}
    return out


def pillar_focus(question: str) -> str:
    """The one pillar a question is about. Empty when the whole rating should lead."""
    from news_rag.insight.manager_view import asks_manager_roster

    text = question or ""
    if asks_manager_roster(text):
        return ""
    if re.search(r"\bfund\s+manager\s+pillar\b", text, re.I):
        return "fundManager"
    if re.search(r"\bfund\s+managers?\b", text, re.I) and re.search(
        r"\bpillar\b|\bscore\b|\bout\s+of\b|/\s*10\b", text, re.I
    ):
        return "fundManager"
    if re.search(r"portfolio[\s_]*quality|\bfund\s+quality\b", text, re.I):
        return "portfolioQuality"
    if re.search(r"\bperformance\b", text, re.I):
        return "performance"
    if re.search(r"\brisk(?:y|ometer| analysis)?\b", text, re.I):
        return "risk"
    return ""


def asks_pillar_mark(question: str) -> bool:
    """One fund's pillar score. Not the generic RS rating explainer."""
    text = question or ""
    if _PILLAR_SCORE_RE.search(text):
        return True
    return bool(re.search(r"\bpillar\b", text, re.I) and pillar_focus(text))


def _ensure_pillar_rating_plan(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    """Pillar scores come from rs-rating. Override a wrong planner module list."""
    focus = pillar_focus(question)
    focus_label = {
        "risk": "risk pillar",
        "performance": "performance pillar",
        "portfolioQuality": "portfolio quality pillar",
        "fundManager": "fund manager pillar",
    }.get(focus, "pillar mark")

    kept = [call for call in plan.tool_calls if call.tool != "get_fund_data"]
    call = ToolCall(tool="get_fund_data", arguments={"modules": ["rating"]}, wave=1)
    plan.tool_calls = [call, *kept]

    asked = set(plan.asked_facts or [])
    asked.add("rating")
    plan.asked_facts = sorted(asked)
    plan.sub_queries = []
    plan.response_shape = "short_answer"
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.requires_compose = True
    plan.wave_2_policy = Wave2Policy(trigger="none")
    plan.max_words = max(int(plan.max_words or 0), 220)
    note = (
        f"The user asked about the {focus_label}. Lead with that pillar score from the rating rows "
        "(score out of max). The risk pillar is a score, not a statement that the fund is more or less risky. "
        "Include the SEBI riskometer when it is in the rows. Do not say pillar data is missing when the score is present."
    )
    existing = (plan.presentation_notes or "").strip()
    if note not in existing:
        plan.presentation_notes = f"{existing} {note}".strip()
    return plan


def rating_lead(summary: dict[str, Any] | None, question: str = "") -> str:
    """The opening lines. One pillar when that is the question, otherwise the score and four marks."""
    from news_rag.insight.manager_view import asks_manager_roster

    if not isinstance(summary, dict):
        return ""
    if asks_manager_roster(question):
        return ""
    pillars = summary.get("pillars") if isinstance(summary.get("pillars"), dict) else {}
    focus = pillar_focus(question)
    if focus and focus in pillars:
        row = pillars[focus]
        name = "Risk pillar" if focus == "risk" else row["label"]
        line = f"**{name}:** {row['score']} out of {row['max']}."
        if focus == "risk":
            line += " This mark is a score. It does not say the fund is more risky or less risky."
        return line
    if summary.get("final_score") is None:
        return ""
    marks = [
        f"{pillars[key]['label']} {pillars[key]['score']}/{pillars[key]['max']}"
        for key, _label, _max in _PILLARS
        if key in pillars
    ]
    line = (
        f"**RupeeStop rating:** {float(summary['final_score']):.2f} out of "
        f"{int(summary.get('max_score') or 100)}, {summary.get('label') or ''}."
    )
    if marks:
        line += " " + " · ".join(marks) + "."
    return line.strip()


def exposure_from_detail(detail: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(detail, dict):
        return {}
    assets = _weights(detail.get("asset_allocation"))
    caps = _weights(detail.get("market_cap"))
    out: dict[str, Any] = {
        "riskometer": str(detail.get("sebi_riskometer") or detail.get("risk_label") or "").strip(),
        "assets": assets,
        "market_cap": caps,
    }
    total = round(sum(row["percentage"] for row in caps), 2) if caps else 0.0
    if caps and abs(total - 100) > 0.5:
        out["market_cap_shortfall"] = True
    smaller = [
        float(row["percentage"])
        for row in caps
        if "mid" in str(row.get("label") or "").lower() or "small" in str(row.get("label") or "").lower()
    ]
    if smaller:
        out["smaller_companies_pct"] = round(sum(smaller), 2)
    return out


def render_risk_lines(summary: dict[str, Any], question: str = "") -> str:
    """Public lines only. No pillar number, weight, or rating input."""
    lines: list[str] = []
    score_only = asks_score_only(question)
    if not score_only and summary.get("riskometer"):
        lines.append(f"SEBI riskometer: {summary['riskometer']}. This is the official label.")
    if summary.get("final_score") is not None:
        lines.append(
            f"RupeeStop assessment: {float(summary['final_score']):.2f} out of {int(summary.get('max_score') or 100)}, "
            f"{summary.get('label') or ''}. {_PILLAR_SENTENCE} "
            "This label is not a statement that the fund is low risk or suitable for every investor."
        )
    if asks_about_score_bands(question):
        lines.append(_BAND_EXPLANATION)
    if score_only:
        return "\n".join(lines)
    assets = summary.get("assets") or []
    if assets:
        mix = ", ".join(f"{row['label']} {float(row['percentage']):.2f}%" for row in assets)
        lines.append(f"Asset mix: {mix}.")
    caps = summary.get("market_cap") or []
    if caps:
        mix = ", ".join(f"{row['label']} {float(row['percentage']):.2f}%" for row in caps)
        lines.append(f"Reported market cap: {mix}.")
        if summary.get("market_cap_shortfall"):
            lines.append("The reported market-cap weights do not add to 100.")
    if _SUITABILITY_RE.search(question or ""):
        lines.append("This does not say whether the fund fits a particular investor.")
    return "\n".join(lines)


def fetch_public_rating(isin: str, *, timeout: float = 12.0) -> dict[str, Any] | None:
    key = (isin or "").strip().upper()
    if not key:
        return None
    cached = _cache.get(key)
    now = time.time()
    if cached and now - cached[0] < _TTL_SEC:
        return dict(cached[1])
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(_RATING_URL.format(isin=key))
            resp.raise_for_status()
            payload = resp.json()
    except Exception as exc:
        logger.warning("rs-rating failed for %s: %s", key, exc)
        return None
    public = normalize_rating(payload if isinstance(payload, dict) else None)
    if public:
        _cache[key] = (now, dict(public))
        return dict(public)
    return None


def load_fund_risk(fund_name: str, question: str = "") -> dict[str, Any]:
    from news_rag.fund_search import resolve_fund_for_query

    detail, _amb, _close = resolve_fund_for_query(fund_name)
    isin = str((detail or {}).get("isin") or "").strip()
    rating = fetch_public_rating(isin) if isin else None
    summary: dict[str, Any] = {}
    if rating:
        summary.update(rating)
    summary.update(exposure_from_detail(detail))
    if detail and detail.get("fund_name"):
        summary["fund_name"] = detail.get("fund_name")
    summary["lines"] = render_risk_lines(summary, question)
    return summary


def _is_band_definition(question: str, plan: ExecutionPlan) -> bool:
    """A question about the label ranges, not about one fund's score."""
    if not asks_about_score_bands(question):
        return False
    text = question or ""
    if re.search(r"\b(?:fund|scheme|risky|riskometer|rupeestop score|final score)\b", text, re.I):
        return False
    if plan.funds and re.search(r"\bwhy\b", text, re.I):
        return False
    return True


def rating_concept_plan(question: str) -> ExecutionPlan:
    """Composer answers from the measurement brief. No fund lookup."""
    from news_rag.insight.contracts import QueryClass, ScopeKind

    return ExecutionPlan(
        scope_kind=ScopeKind.IN_SCOPE,
        intent="lookup",
        goal="Explain how the RS rating is measured",
        answer_mode=AnswerMode.DATA_ONLY,
        query_class=QueryClass.SIMPLE,
        concept_brief=_RATING_CONCEPT,
        requires_compose=True,
        tool_calls=[],
        funds=[],
        wave_2_policy=Wave2Policy(trigger="none"),
        response_shape="short_answer",
        max_words=180,
        presentation_notes=(
            "Answer from concept_brief only. Explain how the RS rating is measured, including the four pillars. "
            "The RS label and the SEBI riskometer are different. Do not name a fund. Do not invent a score."
        ),
        routed_by="slot_router",
        confidence=0.99,
    )


def _use_rating_concept(plan: ExecutionPlan) -> ExecutionPlan:
    plan.tool_calls = []
    plan.funds = []
    plan.entities = []
    plan.direct_reply = ""
    plan.asked_facts = []
    plan.concept_brief = _RATING_CONCEPT
    plan.requires_compose = True
    plan.answer_mode = AnswerMode.DATA_ONLY
    plan.wave_2_policy = Wave2Policy(trigger="none")
    plan.max_words = max(int(plan.max_words or 0), 180)
    plan.presentation_notes = (
        "Answer from concept_brief only. Explain how the RS rating is measured, including the four pillars. "
        "The RS label and the SEBI riskometer are different. Do not name a fund. Do not invent a score."
    )
    return plan


def ensure_risk_tools(question: str, plan: ExecutionPlan) -> ExecutionPlan:
    from news_rag.insight.planner_policy import planner_owns

    if asks_hidden_rating(question):
        plan.tool_calls = []
        plan.direct_reply = _HIDDEN_REPLY
        plan.requires_compose = False
        plan.answer_mode = AnswerMode.DATA_ONLY
        plan.wave_2_policy = Wave2Policy(trigger="none")
        plan.asked_facts = []
        return plan
    if asks_pillar_mark(question):
        return _ensure_pillar_rating_plan(question, plan)
    if asks_risk_trend_comparison(question):
        plan = _ensure_risk_trend_plan(question, plan)
    if planner_owns(plan):
        return plan
    if asks_rating_concept(question):
        return _use_rating_concept(plan)
    if _is_band_definition(question, plan):
        plan.tool_calls = []
        plan.direct_reply = _BAND_EXPLANATION
        plan.requires_compose = False
        plan.answer_mode = AnswerMode.DATA_ONLY
        plan.wave_2_policy = Wave2Policy(trigger="none")
        plan.asked_facts = []
        return plan
    if not asks_fund_risk(question):
        return plan
    if any(call.tool in ("screen_funds_by_exposure", "compare_funds") for call in plan.tool_calls):
        return plan

    asked = set(plan.asked_facts or [])
    asked.add("risk")
    with_drawdown = include_drawdown_with_risk(question) and not asks_score_only(question)
    if with_drawdown:
        asked.add("drawdown")
    plan.asked_facts = sorted(asked)

    call = next((item for item in plan.tool_calls if item.tool == "get_fund_data"), None)
    if call is None:
        call = ToolCall(tool="get_fund_data", arguments={"modules": []}, wave=1)
        plan.tool_calls = [call, *plan.tool_calls]
    modules = [str(name) for name in (call.arguments.get("modules") or [])]
    if "risk" not in modules:
        modules.append("risk")
    if with_drawdown and "drawdown" not in modules:
        modules.append("drawdown")
        if not call.arguments.get("periods"):
            call.arguments["periods"] = ["1y", "3y", "5y"]
    call.arguments["modules"] = modules

    if len(asked) >= 2:
        plan.requires_compose = True
        plan.answer_mode = AnswerMode.DATA_ONLY
        if (plan.max_words or 0) < 320:
            plan.max_words = 320
    return plan


def _weights(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or row.get("name") or "").strip()
        try:
            percentage = round(float(row.get("percentage")), 2)
        except (TypeError, ValueError):
            continue
        if label:
            cleaned.append({"label": label, "percentage": percentage})
    return cleaned
