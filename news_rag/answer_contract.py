"""Agent 2: Answer Contract & Alignment — locks the answer to what was asked."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from news_rag.config import get_settings
from news_rag.llm_client import call_json_llm, contract_model
from news_rag.llm_text import parse_json_from_text
from news_rag.query_log import QueryLogger
from news_rag.query_router import RouterResult

logger = logging.getLogger(__name__)

CONTRACT_PLAN_SYSTEM_PROMPT = """You are an elite financial answer contract architect.
Your job is to read the user's question, the router classification, and an inventory of retrieved evidence, then output a strict, disciplined ANSWER CONTRACT in JSON format.

The contract defines:
1. "must_answer": 1 to 3 core questions/points the answer MUST directly address.
2. "forbidden": Specific topics or blocks that MUST NOT appear in the answer (e.g., "Do not list fund holdings", "Do not cite NAV numbers", "Do not duplicate or re-list items in a narrative summary", "Do not discuss general macro trends", "No buy/sell recommendation", "Do not mention unrelated companies").
3. "use_articles": Array of 0-based integer indices of articles from the article inventory that directly bear on the question. Drop indices of articles that are tangential, generic recaps, or off-topic.
4. "include_nav": boolean (true ONLY if user asked for NAV / fund price / fund return performance).
5. "include_holdings": boolean (true ONLY if user asked for fund holdings / underlying stocks).
6. "include_sectors": boolean (true ONLY if user asked for sector allocations / sector breakdown).
7. "include_stock_price": boolean (true ONLY if user asked about stock price / returns of a specific company).
8. "include_metals": boolean (true ONLY if user asked about gold/silver spot prices / bullion).

RULES:
- Keep the contract minimal, precise, and laser-focused on the user's explicit intent.
- For list queries (fund_sectors, fund_holdings), forbid duplicate narrative re-listing in summary.
- Never include holdings or NAV booleans as true for general concept or macro questions.
- For concept questions, "use_articles" should be [] and all include_* booleans false.
- For fund_nav questions, include_nav is true, include_holdings is false, include_sectors is false.
- For fund_holdings questions, include_holdings is true, include_nav is false, include_sectors is false.
- For fund_sectors questions, include_sectors is true, include_nav is false, include_holdings is false.

OUTPUT FORMAT (ONLY VALID JSON):
{
  "must_answer": ["..."],
  "forbidden": ["..."],
  "use_articles": [0, 1],
  "include_nav": false,
  "include_holdings": false,
  "include_sectors": false,
  "include_stock_price": false,
  "include_metals": false
}"""

ALIGNMENT_CHECK_SYSTEM_PROMPT = """You are a strict compliance and alignment validator for financial answers.
Your job is to compare a generated draft answer against the user's question and the strict answer contract.

Evaluate:
1. Did the draft answer all points in "must_answer"? (If anything was omitted, list in "missing").
2. Did the draft include any prohibited, off-topic, or forbidden content from "forbidden"? (If anything forbidden was included, list in "extra").
3. Is "aligned" true (true if missing is empty and extra is empty)?

OUTPUT FORMAT (ONLY VALID JSON):
{
  "aligned": true | false,
  "missing": ["..."],
  "extra": ["..."]
}"""


@dataclass
class AnswerContract:
    must_answer: list[str] = field(default_factory=list)
    forbidden: list[str] = field(default_factory=list)
    use_articles: list[int] = field(default_factory=list)
    include_nav: bool = False
    include_holdings: bool = False
    include_sectors: bool = False
    include_stock_price: bool = False
    include_metals: bool = False
    raw_json: dict[str, Any] = field(default_factory=dict)
    duration_sec: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, total_articles: int = 0, duration_sec: float = 0.0) -> AnswerContract:
        must_answer = [str(x).strip() for x in data.get("must_answer") or [] if str(x).strip()]
        forbidden = [str(x).strip() for x in data.get("forbidden") or [] if str(x).strip()]
        
        use_raw = data.get("use_articles") or []
        use_articles: list[int] = []
        if isinstance(use_raw, list):
            for idx in use_raw:
                try:
                    i = int(idx)
                    if 0 <= i < total_articles:
                        use_articles.append(i)
                except (ValueError, TypeError):
                    continue

        return cls(
            must_answer=must_answer,
            forbidden=forbidden,
            use_articles=use_articles,
            include_nav=bool(data.get("include_nav")),
            include_holdings=bool(data.get("include_holdings")),
            include_sectors=bool(data.get("include_sectors")),
            include_stock_price=bool(data.get("include_stock_price")),
            include_metals=bool(data.get("include_metals")),
            raw_json=data,
            duration_sec=duration_sec,
        )


@dataclass
class AlignmentResult:
    aligned: bool
    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    raw_json: dict[str, Any] = field(default_factory=dict)
    duration_sec: float = 0.0


def plan_answer_contract(
    question: str,
    router_result: RouterResult,
    inventory: dict[str, Any],
    *,
    query_log: QueryLogger | None = None,
) -> AnswerContract:
    """Plans the answer contract before the writer runs."""
    settings = get_settings()
    articles = inventory.get("articles") or []
    total_articles = len(articles)

    article_lines = []
    for i, a in enumerate(articles):
        title = a.get("title") or ""
        source = a.get("source") or ""
        entities = ", ".join(a.get("entity_names") or [])
        impact = a.get("max_impact", 0)
        direction = a.get("direction", "")
        article_lines.append(f"[{i}] {title} (Source: {source}, Entities: [{entities}], Impact: {impact}, Direction: {direction})")

    articles_text = "\n".join(article_lines) if article_lines else "(none)"

    user_content = (
        f"Question: {question.strip()}\n"
        f"Router Intent: {router_result.intent}\n"
        f"Extracted Fund: {router_result.fund.name or router_result.fund.isin or 'none'}\n"
        f"Extracted Companies: {', '.join(router_result.companies) or 'none'}\n"
        f"Event Focus: {router_result.event_focus or 'none'}\n"
        f"Available Context Blocks:\n"
        f"- NAV History Available: {bool(inventory.get('has_nav'))}\n"
        f"- Holdings Data Available: {bool(inventory.get('has_holdings'))}\n"
        f"- Sectors Data Available: {bool(inventory.get('has_sectors'))}\n"
        f"- Stock Quotes Available: {bool(inventory.get('has_stock_prices'))}\n"
        f"- Metals Prices Available: {bool(inventory.get('has_metals'))}\n"
        f"\nRetrieved Articles ({total_articles}):\n{articles_text}"
    )

    res = call_json_llm(
        system_prompt=CONTRACT_PLAN_SYSTEM_PROMPT,
        user_content=user_content,
        model_override=contract_model(settings),
        max_tokens=settings.contract_max_tokens,
        temperature=0.0,
        query_log=query_log,
    )

    parsed = parse_json_from_text(res.raw_text)
    if not parsed:
        logger.warning("Answer contract planner returned unparseable JSON: %r", res.raw_text)
        if query_log is not None:
            query_log.write(f"contract_planner_error unparseable_json text={res.raw_text[:300]}")
        # Default safe contract based on intent
        return _default_contract_for_intent(router_result, total_articles, res.duration_sec)

    contract = AnswerContract.from_dict(parsed, total_articles=total_articles, duration_sec=res.duration_sec)
    if query_log is not None:
        query_log.write(
            f"contract_plan must_answer={contract.must_answer} forbidden={contract.forbidden} "
            f"use_articles={contract.use_articles} nav={contract.include_nav} "
            f"holdings={contract.include_holdings} sectors={contract.include_sectors} "
            f"stock={contract.include_stock_price} metals={contract.include_metals} "
            f"duration={contract.duration_sec:.2f}s"
        )
    return contract


def check_answer_alignment(
    question: str,
    contract: AnswerContract,
    draft: str,
    *,
    query_log: QueryLogger | None = None,
) -> AlignmentResult:
    """Checks whether the generated draft complies with the answer contract."""
    settings = get_settings()
    user_content = (
        f"Question: {question.strip()}\n"
        f"Must Answer Points:\n" + "\n".join(f"- {p}" for p in contract.must_answer) + "\n\n"
        f"Forbidden Topics:\n" + "\n".join(f"- {f}" for f in contract.forbidden) + "\n\n"
        f"Draft Answer Text:\n{draft.strip()}"
    )

    res = call_json_llm(
        system_prompt=ALIGNMENT_CHECK_SYSTEM_PROMPT,
        user_content=user_content,
        model_override=contract_model(settings),
        max_tokens=400,
        temperature=0.0,
        query_log=query_log,
    )

    parsed = parse_json_from_text(res.raw_text)
    if not parsed:
        if query_log is not None:
            query_log.write(f"alignment_check_error unparseable_json text={res.raw_text[:300]}")
        return AlignmentResult(aligned=True, missing=[], extra=[], raw_json={}, duration_sec=res.duration_sec)

    aligned = bool(parsed.get("aligned"))
    missing = [str(x).strip() for x in parsed.get("missing") or [] if str(x).strip()]
    extra = [str(x).strip() for x in parsed.get("extra") or [] if str(x).strip()]

    # If missing or extra is present, aligned cannot be true
    if missing or extra:
        aligned = False

    result = AlignmentResult(
        aligned=aligned,
        missing=missing,
        extra=extra,
        raw_json=parsed,
        duration_sec=res.duration_sec,
    )
    if query_log is not None:
        query_log.write(
            f"alignment_check aligned={result.aligned} missing={result.missing} "
            f"extra={result.extra} duration={result.duration_sec:.2f}s"
        )
    return result


def _default_contract_for_intent(router_result: RouterResult, total_articles: int, duration_sec: float) -> AnswerContract:
    intent = router_result.intent
    all_article_indices = list(range(total_articles))

    if intent == "concept":
        return AnswerContract(
            must_answer=[router_result.asked[0] if router_result.asked else "Explain concept"],
            forbidden=["Do not cite news headlines", "Do not list fund holdings", "No buy/sell advice"],
            use_articles=[],
            include_nav=False,
            include_holdings=False,
            include_sectors=False,
            include_stock_price=False,
            include_metals=False,
            duration_sec=duration_sec,
        )
    elif intent == "fund_nav":
        return AnswerContract(
            must_answer=["State latest NAV and recent return performance"],
            forbidden=["Do not dump fund holdings list", "Do not dump sector allocations", "No buy/sell advice"],
            use_articles=[],
            include_nav=True,
            include_holdings=False,
            include_sectors=False,
            include_stock_price=False,
            include_metals=False,
            duration_sec=duration_sec,
        )
    elif intent == "fund_holdings":
        return AnswerContract(
            must_answer=["List top holdings of the mutual fund"],
            forbidden=["Do not dump NAV details", "Do not dump sector allocations", "No buy/sell advice"],
            use_articles=[],
            include_nav=False,
            include_holdings=True,
            include_sectors=False,
            include_stock_price=False,
            include_metals=False,
            duration_sec=duration_sec,
        )
    elif intent == "fund_sectors":
        return AnswerContract(
            must_answer=["List top sector allocations of the mutual fund"],
            forbidden=["Do not dump NAV details", "Do not dump holdings list", "No buy/sell advice"],
            use_articles=[],
            include_nav=False,
            include_holdings=False,
            include_sectors=True,
            include_stock_price=False,
            include_metals=False,
            duration_sec=duration_sec,
        )
    elif intent == "bullion":
        return AnswerContract(
            must_answer=["Provide spot prices and market trend for gold and silver"],
            forbidden=["Do not discuss unrelated companies", "No buy/sell advice"],
            use_articles=all_article_indices[:5],
            include_nav=False,
            include_holdings=False,
            include_sectors=False,
            include_stock_price=False,
            include_metals=True,
            duration_sec=duration_sec,
        )

    return AnswerContract(
        must_answer=router_result.asked if router_result.asked else ["Answer user question directly"],
        forbidden=["No buy/sell advice", "Do not cite unrelated news"],
        use_articles=all_article_indices[:8],
        include_nav=intent in ("fund_news", "fund_event_impact"),
        include_holdings=False,
        include_sectors=False,
        include_stock_price=intent == "single_stock",
        include_metals=False,
        duration_sec=duration_sec,
    )
