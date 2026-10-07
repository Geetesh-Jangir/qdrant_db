"""Pre-execution guardrails: predictive/advice ban and out-of-domain rejection."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

GuardOutcome = Literal["pass", "refuse_advice", "refuse_out_of_domain"]

ADVICE_DISCLAIMER = (
    "We provide historical data, current holdings, and analytical news context only. "
    "We do not provide price predictions, forward-looking forecasts, or investment advice."
)

_OUT_OF_DOMAIN_MSG = (
    "This question is outside our financial data scope. "
    "Ask about mutual funds, sectors, stocks, commodities, or recent market news in India."
)

# Historical / descriptive phrasing that should NOT trigger the advice guard.
_HISTORICAL_CONTEXT = re.compile(
    r"\b(how did|how has|what happened|fluctuat|moved|after the|because of|due to|"
    r"impact of|affected|exposure|relation|indirect|news on|reported|according to)\b",
    re.I,
)

_PREDICTIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bwill\s+.+\s+(double|triple|crash|moon)\b", re.I),
    re.compile(r"\bpredict\b", re.I),
    re.compile(r"\bforecast\b", re.I),
    re.compile(r"\bshould\s+i\s+(buy|sell|hold|invest)\b", re.I),
    re.compile(r"\b(buy|sell)\s+(now|today|this)\b", re.I),
    re.compile(r"\btarget\s+price\b", re.I),
    re.compile(r"\bnext\s+(month|quarter|year)\b.*\b(nav|price|return)\b", re.I),
    re.compile(r"\bprice\s+prediction\b", re.I),
    re.compile(r"\brecommend\b", re.I),
)

_FINANCIAL_SIGNAL = re.compile(
    r"\b(nav|mutual\s+funds?|funds?|holdings?|sectors?|stocks?|shares?|crude|oil|gold|silver|"
    r"barrel|brent|energy|markets?|nifty|sensex|"
    r"rbi|repo|inflation|isin|inf[0-9a-z]{9}|portfolio|equity|"
    r"commodity|macro|earnings|dividend|sip|expense\s+ratio|aum|"
    r"(?:large|mid|small|flexi|multi)\s*cap|etf)\b",
    re.I,
)


@dataclass(frozen=True)
class GuardrailResult:
    outcome: GuardOutcome
    message: str = ""
    reason: str = ""


def check_guardrails(question: str) -> GuardrailResult:
    q = (question or "").strip()
    if not q:
        return GuardrailResult("refuse_out_of_domain", _OUT_OF_DOMAIN_MSG, reason="empty")

    lower = q.lower()
    if re.search(r"\bshould\s+i\s+(buy|sell|hold|invest)\b", lower):
        return GuardrailResult("refuse_advice", ADVICE_DISCLAIMER, reason="advice")

    historical = bool(_HISTORICAL_CONTEXT.search(q))
    for pat in _PREDICTIVE_PATTERNS:
        if pat.search(q):
            if historical and "should" not in pat.pattern.lower() and "recommend" not in pat.pattern.lower():
                continue
            return GuardrailResult("refuse_advice", ADVICE_DISCLAIMER, reason="predictive_or_advice")

    if not _FINANCIAL_SIGNAL.search(q):
        # Allow short concept questions
        if re.match(r"^\s*what\s+is\s+\w+", lower) and len(q) < 120:
            return GuardrailResult("pass")
        if re.search(r"\b(code|python|javascript|poem|joke|recipe)\b", lower):
            return GuardrailResult("refuse_out_of_domain", _OUT_OF_DOMAIN_MSG, reason="non_financial")
        if len(q) < 40 and not _FINANCIAL_SIGNAL.search(q):
            return GuardrailResult("refuse_out_of_domain", _OUT_OF_DOMAIN_MSG, reason="no_financial_signal")

    return GuardrailResult("pass")


def refusal_response(result: GuardrailResult) -> dict:
    return {
        "insight": result.message,
        "insight_summary": result.message,
        "insight_bullets": [],
        "sources": [],
        "intent": "refused",
        "insight_source": "guardrail",
        "outcome": "refused",
        "refused": True,
        "refusal_reason": result.reason,
        "sections": [
            {
                "id": "guard",
                "style": "refusal",
                "text": result.message,
            }
        ],
        "sub_queries": [],
    }
