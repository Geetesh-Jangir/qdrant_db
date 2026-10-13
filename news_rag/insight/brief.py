"""Phase 1: Question brief — what the user asked, which entities, which evidence is needed.

Two layers cooperate:
  * a deterministic reader (`_heuristic_brief`) that always works and plans evidence from the
    entities it finds (sector, macro driver, named fund, stock, commodity, direction);
  * an LLM planner that adds sub-asks and entities the rules miss.
The final evidence plan is the union, so a weak LLM reply can never drop a needed tool.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from news_rag.config import get_settings
from news_rag.insight.facets import SUB_ASK_KINDS, validate_facets
from news_rag.insight.registry import ensure_registry, registry_prompt_block
from news_rag.llm_client import call_json_llm, llm_api_key_configured, router_model
from news_rag.query_log import clip_log_text

from news_rag.prompts import build_brief_prompt

BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "goal": {"type": "string"},
        "intent": {"type": "string", "enum": ["explain_cause", "compare", "rank", "measure", "outlook"]},
        "sub_asks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string"},
                    "kind": {"type": "string"},
                },
                "required": ["id", "text", "kind"],
            },
        },
        "subjects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "raw": {"type": "string"},
                    "canonical": {"type": "string"},
                    "role": {"type": "string"},
                },
            },
        },
        "sector": {"type": "string"},
        "drivers": {"type": "array", "items": {"type": "string"}},
        "driver_direction": {"type": "string"},
        "funds": {"type": "array", "items": {"type": "string"}},
        "stocks": {"type": "array", "items": {"type": "string"}},
        "direction": {"type": "string"},
        "tone": {"type": "string"},
        "benchmark": {"type": "string"},
        "window_days": {"type": "integer"},
        "per_tool_window": {"type": "object"},
        "evidence_needs": {"type": "array", "items": {"type": "string"}},
        "analysis_angles": {"type": "array", "items": {"type": "string"}},
        "hypotheses": {"type": "array", "items": {"type": "string"}},
        "success_criteria": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["goal", "evidence_needs", "success_criteria"],
}

BRIEF_SYSTEM = build_brief_prompt(registry_prompt_block())



@dataclass
class SubAsk:
    id: str
    text: str
    kind: str = "describe"
    order: int = 0
    max_sentences: int = 3


@dataclass
class QuestionBrief:
    goal: str = ""
    intent: str = "explain_cause"
    sub_asks: list[SubAsk] = field(default_factory=list)
    subjects: list[dict[str, str]] = field(default_factory=list)
    window_days: int = 180
    window_label: str = "6 months"
    per_tool_window: dict[str, int] = field(default_factory=dict)
    benchmark: str = ""
    tone: str = "neutral"
    implicit_needs: list[str] = field(default_factory=list)
    evidence_needs: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    # entities
    sector_keys: list[str] = field(default_factory=list)
    drivers: list[str] = field(default_factory=list)
    driver_direction: str = ""
    funds: list[str] = field(default_factory=list)
    stocks: list[str] = field(default_factory=list)
    direction: str = "any"
    wants_funds_flag: bool = False


    def primary_sector(self) -> str:
        for s in self.subjects:
            if str(s.get("role") or "").lower() == "sector":
                return str(s.get("canonical") or s.get("raw") or "").strip()
        if self.sector_keys:
            return self.sector_keys[0]
        return ""

    def wants_funds(self) -> bool:
        if self.wants_funds_flag:
            return True
        blob = " ".join(a.text.lower() for a in self.sub_asks) + " " + self.goal.lower()
        return any(w in blob for w in ("fund", "impacted", "affected", "exposure", "hold"))

    def return_window(self) -> str:
        return nearest_return_window(self.window_days)


def nearest_return_window(window_days: int) -> str:
    """Catalog returns exist for 1W / 1M / 3M / 1Y; pick the closest."""
    options = {"1W": 7, "1M": 30, "3M": 90, "1Y": 365}
    return min(options, key=lambda k: abs(options[k] - max(1, int(window_days or 30))))


# ---------------------------------------------------------------------------
# Deterministic readers
# ---------------------------------------------------------------------------

_DRIVER_PATTERNS: list[tuple[str, str]] = [
    ("rbi_repo", r"\brbi\b|\brepo\b|rate (?:hike|cut)|interest rates?|monetary policy"),
    ("crude_oil", r"\bcrude\b|\bbrent\b|\boil (?:price|prices|shock)\b|\boil\b"),
    ("usd_inr", r"\brupee\b|usd\s*/?\s*inr|\bdollar\b|\bforex\b"),
    ("cpi_inflation", r"\binflation\b|\bcpi\b|\bwpi\b"),
    ("fpi_flows", r"\bfii\b|\bfpi\b|foreign (?:investors?|flows?|portfolio)"),
    ("gsec_10y", r"\bbond yields?\b|\bg-?sec\b|10[- ]?year yield"),
    ("us_fed_yields", r"\bfed\b|federal reserve|treasury yields?"),
    ("monsoon", r"\bmonsoon\b|\brainfall\b"),
    ("govt_capex", r"\bbudget\b|\bcapex\b|\bfiscal\b"),
    ("growth_indicators", r"\bgdp\b|\bpmi\b|\biip\b"),
]
_DRIVER_DIRECTION_PATTERNS: list[tuple[str, str]] = [
    ("tighten", r"rate hike|\bhike[sd]?\b|\bhawkish\b|tighten"),
    ("ease", r"rate cut|\bcuts?\b|\bdovish\b|\beas(?:e|es|ing)\b"),
    ("up", r"\brise[sn]?\b|\bsurg\w+|\bspik\w+|\bhigher\b|\bjump\w*|\bup\b"),
    ("down", r"\bfall(?:s|ing)?\b|\bdrop\w*|\bdecline\w*|\bslump\w*|\blower\b|\bdown\b"),
    ("weaken", r"\bweaken\w*|\bdepreciat\w+|\bweak rupee\b"),
    ("strengthen", r"\bstrengthen\w*|\bappreciat\w+"),
]
_POSITIVE_RE = re.compile(r"\bpositiv\w*|\bbenefit\w*|\bgain\w*|\bwinners?\b|\bhelped\b|\bupside\b", re.I)
_NEGATIVE_RE = re.compile(r"\bnegativ\w*|\bhurt\b|\bhit\b|\blosers?\b|\bhurting\b|\bdownside\b|\badverse\w*", re.I)
_FUND_WORD_RE = re.compile(r"\bfunds?\b|\bschemes?\b|\bmutual funds?\b|\bamc\b", re.I)
_IMPACT_WORD_RE = re.compile(r"impact\w*|affect\w*|exposed|exposure|heavy|heavily|highly|hold\w*", re.I)
_METAL_RE = re.compile(r"\bgold\b|\bsilver\b|\bbullion\b", re.I)
_MARKET_RE = re.compile(
    r"what(?:'s|s| is) (?:happening|going on)|market (?:today|now|overview|pulse|update|right now)|overall market|"
    r"how is the (?:indian )?market|stock market",
    re.I,
)
_COMPARE_RE = re.compile(r"\bcompare\b|\bversus\b|\bvs\.?\b|better than", re.I)
_HOLDERS_RE = re.compile(r"which (?:mutual )?funds? (?:hold|own|have)|funds? (?:holding|that hold)", re.I)
_SCREEN_RE = re.compile(
    r"\b(?:best|top|worst|highest|lowest)\s+(?:performing|performers?|funds?)|\bperforming (?:well|best)|\bwhich funds?\b.*\b(?:amc|category|large cap|mid cap|small cap|elss|flexi)\b",
    re.I,
)
_SECTOR_LIST_RE = re.compile(
    r"\bwhich sectors?\b|\bsectors?\s+(?:are\s+)?(?:going\s+)?(?:down|up|falling|rising|declining|weak|strong|under\s+pressure)\b|"
    r"\b(?:hurt|hit|weak|down|falling)\s+sectors?\b",
    re.I,
)


_WEAK_SECTOR_RE = re.compile(
    r"\b(?:not working well|not doing well|underperform\w*|struggl\w*|lagg\w*|worst)\b.*\bsectors?\b|"
    r"\bsectors?\b.*\b(?:not working well|not doing well|underperform\w*|struggl\w*|lagg\w*|worst|weak)\b",
    re.I,
)


_RANDOM_FUNDS_RE = re.compile(
    r"\b(?:any|random)\b.{0,48}\bfunds?\b|\btwo random funds\b|\brandom(?:ly)?\b.{0,24}\bfunds?\b",
    re.I,
)


def asks_random_fund_compare(question: str) -> bool:
    """User wants two funds compared but did not name them."""
    q = question or ""
    return bool(_COMPARE_RE.search(q) and _RANDOM_FUNDS_RE.search(q))


def asks_weak_sector(question: str) -> bool:
    """User wants the sector that performed poorly, judged from returns, not from a news headline."""
    return bool(_WEAK_SECTOR_RE.search(question or ""))


def asks_sector_lists(question: str, brief: QuestionBrief | None = None) -> bool:
    """User wants a cross-sector hurt/help list (market-wide), not a single-sector deep dive."""
    q = question or ""
    if _SECTOR_LIST_RE.search(q):
        return True
    if brief:
        for a in brief.sub_asks:
            t = a.text or ""
            if _SECTOR_LIST_RE.search(t):
                return True
    return bool(
        re.search(
            r"\bwhich sectors?\b.*\b(benefit|hurt|affected|positive|negative|down|up|weak|strong)",
            q,
            re.I,
        )
    )


def _detect_sector(question: str) -> tuple[str, list[str]]:
    """Whole-word alias match so 'hit' never reads as the IT sector."""
    from news_rag.sector_fund_ranking import _SECTOR_ALIASES, get_sector_fund_ranking_index

    lower = (question or "").lower()
    idx = get_sector_fund_ranking_index()
    keys: list[str] = []
    for alias in sorted(_SECTOR_ALIASES, key=len, reverse=True):
        if alias in {"rbi", "repo", "repo rate", "rate hike", "crude", "oil", "brent", "rupee", "dollar", "inflation"}:
            continue  # macro drivers, not a sector subject
        if re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", lower):
            keys.extend(_SECTOR_ALIASES[alias])
    for name in idx.sector_names:
        if _NOT_A_SECTOR_RE.search(name):
            continue
        if len(name) > 4 and re.search(rf"(?<![a-z]){re.escape(name.lower())}(?![a-z])", lower):
            keys.append(name)
    resolved = [k for k in idx.resolve_sector_keys(keys) if not _NOT_A_SECTOR_RE.search(k)]
    return (resolved[0] if resolved else ""), resolved


# Holdings-taxonomy labels that are not market sectors (fund-of-funds, cash, tenor buckets, cap sizes...).
_NOT_A_SECTOR_RE = re.compile(
    r"\bfunds?\b|\bdays?\b|\bcash\b|\bunits?\b|\bgold\b|\bsilver\b|\bdebt\b|\betf\b|"
    r"\blarge\s*cap\b|\bmid\s*cap\b|\bsmall\s*cap\b|\bflexi\s*cap\b|\bmulti\s*cap\b",
    re.I,
)


def _detect_drivers(question: str) -> tuple[list[str], str]:
    lower = (question or "").lower()
    drivers = [name for name, pat in _DRIVER_PATTERNS if re.search(pat, lower)]
    direction = ""
    for name, pat in _DRIVER_DIRECTION_PATTERNS:
        if re.search(pat, lower):
            direction = name
            break
    return drivers, direction


def _detect_direction(question: str) -> str:
    q = question or ""
    if re.search(r"\bonly\b.*\bposit\w*", q, re.I) or re.search(
        r"\b(?:list|show|name)\b.*\bposit\w*\s+affect", q, re.I
    ):
        return "positive"
    if re.search(r"\bonly\b.*\bneg\w*", q, re.I) or re.search(
        r"\b(?:list|show|name)\b.*\bneg\w*\s+affect", q, re.I
    ):
        return "negative"
    pos = bool(_POSITIVE_RE.search(q))
    neg = bool(_NEGATIVE_RE.search(q))
    if pos and not neg:
        return "positive"
    if neg and not pos:
        return "negative"
    return "any"


_AMC_TOKENS = {
    "hdfc", "sbi", "icici", "axis", "kotak", "dsp", "tata", "nippon",
    "uti", "mirae", "parag", "ppfas", "motilal", "aditya", "birla",
    "franklin", "canara", "bandhan", "invesco", "hsbc", "quant",
    "edelweiss", "sundaram", "pgim", "baroda", "bnp", "groww", "navi",
    "whiteoak", "mahindra", "manulife",
}


_PRICE_ASK_RE = re.compile(
    r"\b(?:share\s+price|stock\s+price|price|cmp|ltp|quote|trading at|how much(?: is| does)?)\b",
    re.I,
)
_SHARE_WORD_RE = re.compile(r"\b(?:stocks?|shares?|equity)\b", re.I)


def asks_share_price(question: str) -> bool:
    """A company price/quote question, including wording that never says 'stock'."""
    q = question or ""
    if _FUND_WORD_RE.search(q) and not _PRICE_ASK_RE.search(q):
        return False
    return bool(_PRICE_ASK_RE.search(q) or _SHARE_WORD_RE.search(q))


def _detect_stocks(question: str) -> list[str]:
    from historical_data.stocks_service import NAME_TO_NSE_TICKER

    q = (question or "").lower()
    hits: list[str] = []
    for name in sorted(NAME_TO_NSE_TICKER, key=len, reverse=True):
        if len(name) < 3:
            continue
        if any(name in earlier.lower() for earlier in hits):
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(name)}(?![a-z0-9])", q):
            hits.append(name)
        if len(hits) >= 2:
            break
    return hits


def _detect_funds(question: str) -> list[str]:
    from news_rag.fund_search import _SCHEME_NAME_TO_ISIN, lookup_extracted_fund

    out: list[str] = []
    q_lower = (question or "").lower()

    # 1. Direct colloquial / scheme aliases (e.g. "hdfc large cap", "sbi bluechip")
    for alias in sorted(_SCHEME_NAME_TO_ISIN, key=len, reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", q_lower):
            try:
                detail, ambiguous, _close = lookup_extracted_fund(name=alias)
                if detail and not ambiguous:
                    name = str(detail.get("fund_short_name") or detail.get("fund_name") or "").strip()
                    if name and name not in out:
                        out.append(name)
            except Exception:
                pass

    # 2. ISINs and phrases with explicit "fund" words
    phrases = re.findall(r"\bINF[0-9A-Z]{9}\b", question or "", re.I)
    if _FUND_WORD_RE.search(question or ""):
        phrases.append(question)
    for phrase in phrases[:3]:
        try:
            detail, ambiguous, _close = lookup_extracted_fund(name=phrase)
        except Exception:
            continue
        if detail and not ambiguous:
            name = str(detail.get("fund_short_name") or detail.get("fund_name") or "").strip()
            if name and name not in out:
                out.append(name)

    if out:
        return out

    # 3. Fuzzy match n-grams (2-5 words) strictly requiring at least one known AMC token
    raw_tokens = re.findall(r"[A-Za-z0-9]+", question or "")
    if len(raw_tokens) >= 2:
        stopwords = {"why", "is", "the", "in", "last", "one", "month", "months", "year", "down", "up", "fell", "rose", "what", "how", "are", "doing", "and"}
        for n in (5, 4, 3, 2):
            if n > len(raw_tokens):
                continue
            for i in range(len(raw_tokens) - n + 1):
                ngram_tokens = raw_tokens[i : i + n]
                low_tokens = [t.lower() for t in ngram_tokens]
                if all(t in stopwords for t in low_tokens):
                    continue
                if not any(t in _AMC_TOKENS for t in low_tokens):
                    continue
                ngram = " ".join(ngram_tokens)
                try:
                    detail, ambiguous, _close = lookup_extracted_fund(name=ngram)
                except Exception:
                    continue
                if detail and not ambiguous:
                    name = str(detail.get("fund_short_name") or detail.get("fund_name") or "").strip()
                    if name and name not in out:
                        out.append(name)
            if out:
                break
    return out



def _infer_window_days(question: str) -> tuple[int, str]:
    q = question.lower()
    m = re.search(r"(\d+)\s*month", q)
    if m:
        n = int(m.group(1))
        return max(30, n * 30), ("1 month" if n == 1 else f"{n} months")
    if "6 month" in q or "six month" in q or "last 6" in q:
        return 180, "6 months"
    if "1 year" in q or "one year" in q or "12 month" in q or "last year" in q:
        return 365, "1 year"
    if "3 month" in q or "quarter" in q:
        return 90, "3 months"
    if re.search(r"\b(last|past|this)\s+week\b|\bright now\b|\btoday\b", q):
        return 7, "7 days"
    if re.search(r"\b(last|past|this)(?:\s+one)?\s+month\b|\bone month\b", q):
        return 30, "1 month"
    return 180, "6 months"


def _split_sub_asks_from_question(question: str) -> list[SubAsk]:
    """Preserve the user's question order (before the LLM)."""
    parts = re.split(r"\?+|\band then\b|\band if\b|\balso\b(?=,)", question, flags=re.I)
    out: list[SubAsk] = []
    for i, part in enumerate(parts):
        text = part.strip().rstrip("?").strip()
        if len(text) < 12:
            continue
        kind = "describe"
        lower = text.lower()
        if any(w in lower for w in ("positively", "negative", "impacted", "affected", "which fund")):
            kind = "measure"
        elif "why" in lower or "driver" in lower or "factor" in lower or "other sector" in lower:
            kind = "explain_cause"
        elif "compare" in lower:
            kind = "compare"
        max_sent = 2 if kind == "measure" else 3
        out.append(SubAsk(f"u{i+1}", text, kind, order=i + 1, max_sentences=max_sent))
    return out


def plan_evidence(brief: QuestionBrief, question: str) -> list[str]:
    """Deterministic evidence plan from the entities found. Never depends on the LLM."""
    q = question or ""
    needs: list[str] = []
    has_sector = bool(brief.primary_sector())
    has_driver = bool(brief.drivers)
    wants_funds = bool(brief.wants_funds_flag or _FUND_WORD_RE.search(q) and _IMPACT_WORD_RE.search(q))

    if has_sector:
        needs += ["news_drivers", "entity_state_over_time", "benchmark"]
    if has_driver:
        needs += ["macro_driver_map"]
        if not has_sector:
            needs += ["news_drivers"]
    if has_sector or has_driver:
        if wants_funds or (_FUND_WORD_RE.search(q) and has_driver):
            needs += ["exposure_link", "fund_composition", "return_series"]
            if has_driver and not has_sector:
                needs.insert(needs.index("exposure_link"), "sector_impact_direction")
    if brief.funds:
        from news_rag.insight.fund_why import named_fund_why

        needs += ["fund_facts_nav", "fund_composition", "return_series"]
        if _COMPARE_RE.search(q):
            needs.append("peer_compare")
        if not asks_random_fund_compare(q) and not named_fund_why(q, brief):
            needs.append("news_drivers")
    if brief.stocks:
        needs.append("stock_price")
        if not asks_share_price(q):
            needs.append("holding_drivers")
        if _HOLDERS_RE.search(q):
            needs.append("stock_holders")
    if _METAL_RE.search(q):
        needs += ["commodity_spot", "news_drivers"]
    if _MARKET_RE.search(q) and not has_sector and not brief.funds and not brief.stocks:
        needs.append("market_overview")
    if _SCREEN_RE.search(q) and not has_sector and not has_driver and not brief.funds:
        needs.append("fund_screen")
    if asks_sector_lists(q, brief):
        needs += ["news_drivers", "sector_impact_direction"]
    if not needs:
        needs = ["market_overview"] if not brief.funds else ["fund_facts_nav"]
    return validate_facets(needs)


def validate_brief_plan(brief: QuestionBrief, question: str) -> list[str]:
    """Deterministic validator enforcing playbooks and dependency closures."""
    q = question or ""
    needs = list(brief.evidence_needs)
    has_sector = bool(brief.primary_sector())
    wants_funds = brief.wants_funds()

    # 1. Enforce tool-order playbooks
    if brief.funds:
        from news_rag.insight.fund_why import named_fund_why

        for f in ["fund_facts_nav", "fund_composition", "return_series"]:
            if f not in needs:
                needs.append(f)
        if not named_fund_why(q, brief) and "news_drivers" not in needs:
            needs.append("news_drivers")
    elif has_sector and wants_funds:
        for f in ["news_drivers", "entity_state_over_time", "benchmark", "exposure_link", "fund_composition", "return_series"]:
            if f not in needs:
                needs.append(f)
    elif has_sector and not wants_funds:
        for f in ["news_drivers", "entity_state_over_time", "benchmark"]:
            if f not in needs:
                needs.append(f)
    elif brief.stocks:
        if "stock_price" not in needs:
            needs.append("stock_price")
        if not asks_share_price(q) and "holding_drivers" not in needs:
            needs.append("holding_drivers")
    elif asks_sector_lists(q, brief):
        for f in ["news_drivers", "sector_impact_direction"]:
            if f not in needs:
                needs.append(f)

    # 2. Dependency closure
    if "sector_impact_direction" in needs and "news_drivers" not in needs:
        needs.insert(0, "news_drivers")
    if "driver_affected_funds" in needs or ("exposure_link" in needs and bool(brief.drivers) and not has_sector):
        if "sector_impact_direction" not in needs:
            idx = needs.index("exposure_link") if "exposure_link" in needs else len(needs)
            needs.insert(idx, "sector_impact_direction")
        if "news_drivers" not in needs:
            needs.insert(0, "news_drivers")

    return validate_facets(list(dict.fromkeys(needs)))



def _success_criteria(brief: QuestionBrief, question: str = "") -> list[str]:
    crit: list[str] = []
    if brief.primary_sector():
        crit.append("States sector news tone with the reasons from articles")
        crit.append("Mentions benchmark or index context")
    if brief.wants_funds():
        crit += [
            "Names multiple funds with sector exposure",
            "Lists other top sectors per fund",
            f"Gives return pattern over {brief.window_label}",
            "States positive/negative/mixed impact per fund",
        ]
    if brief.drivers and not brief.primary_sector():
        crit.append("Explains how the macro driver reaches sectors and funds")
    if asks_sector_lists(question, brief) and not brief.primary_sector() and not brief.wants_funds():
        crit.append("Names sectors the news is hurting and sectors it is helping")
    return crit


def _heuristic_brief(question: str) -> QuestionBrief:
    ensure_registry()
    window_days, window_label = _infer_window_days(question)
    sector, sector_keys = _detect_sector(question)
    if asks_weak_sector(question) and not sector:
        from news_rag.insight.index_series import worst_sector_by_return

        worst, _pct = worst_sector_by_return(window_days)
        if worst:
            sector, sector_keys = worst, [worst]
    drivers, driver_direction = _detect_drivers(question)
    funds = _detect_funds(question)
    stocks = _detect_stocks(question) if asks_share_price(question) else []
    if stocks and not _FUND_WORD_RE.search(question):
        funds = []
        sector, sector_keys = "", []
    if asks_random_fund_compare(question) and len(funds) < 2:
        from news_rag.fund_search import get_fund_index

        funds = get_fund_index().sample_fund_names(2)
    if funds:
        # a sector word inside a fund's own name is not a sector question
        sector, sector_keys = ("", []) if not re.search(r"\bsector\b", question, re.I) else (sector, sector_keys)
    subjects: list[dict[str, str]] = []
    if sector:
        subjects.append({"raw": sector, "role": "sector", "canonical": sector})
    for d in drivers:
        subjects.append({"raw": d, "role": "macro_driver", "canonical": d})
    for f in funds:
        subjects.append({"raw": f, "role": "fund_scheme", "canonical": f})
    for sname in stocks:
        subjects.append({"raw": sname, "role": "stock", "canonical": sname})
    sub_asks = _split_sub_asks_from_question(question)
    if not sub_asks:
        sub_asks = [SubAsk("s1", "Answer the question using retrieved evidence", "describe", order=1)]
    wants_funds = bool(_FUND_WORD_RE.search(question) and _IMPACT_WORD_RE.search(question))
    intent = "explain_cause"
    if _COMPARE_RE.search(question):
        intent = "compare"
    elif _SCREEN_RE.search(question):
        intent = "rank"
    elif wants_funds and _IMPACT_WORD_RE.search(question):
        intent = "measure"

    brief = QuestionBrief(
        goal=question[:300],
        intent=intent,
        sub_asks=sub_asks,
        subjects=subjects,
        window_days=window_days,
        window_label=window_label,
        implicit_needs=["confounders via full fund composition"] if sector and wants_funds else [],
        sector_keys=sector_keys,
        drivers=drivers,
        driver_direction=driver_direction,
        funds=funds,
        stocks=stocks,
        direction="negative" if asks_weak_sector(question) else _detect_direction(question),
        wants_funds_flag=wants_funds,
        raw={"source": "heuristic"},
    )
    if wants_funds and not any(a.kind == "measure" for a in sub_asks):
        sub_asks.append(
            SubAsk(
                "f1",
                "Funds with high exposure and positive or negative impact",
                "measure",
                order=len(sub_asks) + 1,
                max_sentences=2,
            )
        )
    brief.evidence_needs = plan_evidence(brief, question)
    brief.success_criteria = _success_criteria(brief, question)
    brief.assumptions = ["high exposure = top ranked funds by sector weight"] if sector else []
    return brief


def _log_brief(query_log: Any, brief: QuestionBrief, source: str, **extra: Any) -> None:
    if query_log is None:
        return
    query_log.log_brief(
        source=source,
        brief_summary={
            "goal": clip_log_text(brief.goal, 120),
            "sector": brief.primary_sector(),
            "drivers": brief.drivers,
            "funds": brief.funds,
            "stocks": brief.stocks,
            "direction": brief.direction,
            "window": brief.window_label,
            "evidence_needs": brief.evidence_needs,
            "sub_asks": [f"{a.kind}:{a.text[:50]}" for a in brief.sub_asks[:8]],
            **extra,
        },
    )


def build_question_brief(
    question: str,
    *,
    prior_context: dict[str, Any] | None = None,
    query_log: Any = None,
) -> QuestionBrief:
    q = (question or "").strip()
    if not q:
        return QuestionBrief(goal="", evidence_needs=validate_facets(["market_overview"]))

    settings = get_settings()
    heur = _heuristic_brief(q)
    if not llm_api_key_configured(settings):
        _log_brief(query_log, heur, "heuristic", reason="no_llm_key")
        return heur

    ensure_registry()
    prior_blob = f"\nPrior turn context: {prior_context}\n" if prior_context else ""
    hints = {
        "sector_detected": heur.primary_sector(),
        "drivers_detected": heur.drivers,
        "funds_detected": heur.funds,
        "direction_detected": heur.direction,
    }
    user = f"Question:\n{q}\n{prior_blob}\nLocal hints (may be empty): {hints}\n\n{registry_prompt_block()}"
    parsed: dict[str, Any] = {}
    try:
        res = call_json_llm(
            system_prompt=BRIEF_SYSTEM,
            user_content=user,
            context_blocks=[],
            model_override=router_model(settings),
            max_tokens=1600,
            temperature=0.0,
            query_log=query_log,
            response_schema=BRIEF_SCHEMA,
            stage="brief",
        )
        parsed = res.parsed if isinstance(res.parsed, dict) else {}
        if getattr(res, "truncated", False) and not parsed:
            parsed = {}
    except Exception as exc:
        if query_log is not None:
            query_log.write(f"BRIEF_FALLBACK reason=llm_error error={exc!s}"[:200])
        parsed = {}

    if not parsed or not parsed.get("evidence_needs"):
        if query_log is not None:
            query_log.write("BRIEF_FALLBACK reason=llm_truncated_or_empty")
        _log_brief(query_log, heur, "heuristic", reason="llm_unusable")
        return heur

    sub_asks: list[SubAsk] = []
    for item in parsed.get("sub_asks") or []:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "describe").strip().lower()
        if kind not in SUB_ASK_KINDS:
            kind = "describe"
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        sub_asks.append(
            SubAsk(
                id=str(item.get("id") or f"s{len(sub_asks)+1}"),
                text=text,
                kind=kind,
                order=len(sub_asks) + 1,
                max_sentences=2 if kind == "measure" else 3,
            )
        )

    from news_rag.sector_fund_ranking import get_sector_fund_ranking_index

    idx = get_sector_fund_ranking_index()
    llm_sector = str(parsed.get("sector") or "").strip()
    sector_keys = heur.sector_keys
    if asks_weak_sector(q) and heur.sector_keys:
        llm_sector = ""
    if llm_sector and not sector_keys:
        sector_keys = idx.resolve_sector_keys([llm_sector])
    elif llm_sector and sector_keys and llm_sector.lower() not in {k.lower() for k in sector_keys}:
        extra = idx.resolve_sector_keys([llm_sector])
        sector_keys = list(dict.fromkeys(sector_keys + extra))
    drivers = list(dict.fromkeys(heur.drivers + [d for d in (parsed.get("drivers") or []) if isinstance(d, str)]))
    from news_rag.fund_search import lookup_extracted_fund

    resolved_llm_funds: list[str] = []
    for f in (parsed.get("funds") or []):
        if not isinstance(f, str) or not f.strip():
            continue
        try:
            detail, ambiguous, _close = lookup_extracted_fund(name=f.strip())
            if detail and not ambiguous:
                fn = str(detail.get("fund_short_name") or detail.get("fund_name") or f).strip()
                resolved_llm_funds.append(fn)
            else:
                resolved_llm_funds.append(f.strip())
        except Exception:
            resolved_llm_funds.append(f.strip())
    if asks_random_fund_compare(q) and len(heur.funds) >= 2:
        funds = list(heur.funds[:2])
    else:
        funds = list(dict.fromkeys(heur.funds + resolved_llm_funds))
    llm_stocks = [s for s in (parsed.get("stocks") or []) if isinstance(s, str) and s.strip()]
    if asks_share_price(q) and heur.stocks:
        stocks = list(heur.stocks)
        funds = []
    else:
        stocks = list(dict.fromkeys(heur.stocks + llm_stocks))
    direction = str(parsed.get("direction") or "").strip().lower()
    if direction not in ("positive", "negative", "any"):
        direction = heur.direction
    forced = _detect_direction(q)
    if forced in ("positive", "negative"):
        direction = forced
    if asks_weak_sector(q):
        direction = "negative"
    window_days = int(parsed.get("window_days") or 0) or heur.window_days
    months = max(1, round(window_days / 30))
    window_label = heur.window_label if window_days == heur.window_days else (
        "1 month" if months == 1 else f"{months} months"
    )

    subjects = list(heur.subjects)
    if sector_keys and not any(s.get("role") == "sector" for s in subjects):
        subjects.append({"raw": sector_keys[0], "role": "sector", "canonical": sector_keys[0]})

    intent = str(parsed.get("intent") or heur.intent or "explain_cause").strip().lower()
    tone = str(parsed.get("tone") or heur.tone or "neutral").strip().lower()
    benchmark = str(parsed.get("benchmark") or heur.benchmark or "").strip()
    ptw = parsed.get("per_tool_window") if isinstance(parsed.get("per_tool_window"), dict) else {}

    brief = QuestionBrief(
        goal=str(parsed.get("goal") or q[:300]),
        intent=intent,
        sub_asks=sub_asks or heur.sub_asks,
        subjects=subjects,
        window_days=window_days,
        window_label=window_label,
        per_tool_window=ptw,
        benchmark=benchmark,
        tone=tone,
        implicit_needs=heur.implicit_needs,
        sector_keys=sector_keys,
        drivers=drivers,
        driver_direction=str(parsed.get("driver_direction") or heur.driver_direction or ""),
        funds=funds,
        stocks=stocks,
        direction=direction,
        wants_funds_flag=heur.wants_funds_flag,
        success_criteria=[str(x) for x in (parsed.get("success_criteria") or [])] or heur.success_criteria,
        assumptions=heur.assumptions,
        raw={**parsed, "source": "llm"},
    )
    llm_needs = validate_facets([str(x) for x in (parsed.get("evidence_needs") or [])])
    det_needs = plan_evidence(brief, q)
    broad = {"market_overview", "forward_view", "peer_rank", "sector_impact_direction"}
    if asks_sector_lists(q, brief):
        broad.discard("sector_impact_direction")
    if not brief.primary_sector():
        broad |= {"benchmark", "entity_state_over_time"}
    extras = [f for f in llm_needs if f not in broad or f in det_needs]
    brief.evidence_needs = list(dict.fromkeys(det_needs + extras))
    brief.evidence_needs = validate_brief_plan(brief, q)
    _log_brief(query_log, brief, "llm", merged_from_llm=llm_needs)
    return brief

