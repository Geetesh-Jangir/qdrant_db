"""LLM ask planner types — single plan per user question."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Sentiment = Literal["positive", "negative", "any"]
EntityRole = Literal["fund_scheme", "amc", "holding", "sector", "macro_driver"]
AffectedFundsTiming = Literal["none", "now", "after_news"]

ALLOWED_PLANNER_TOOLS = frozenset(
    {
        "fund_nav",
        "fund_top_stocks",
        "fund_top_sectors",
        "fund_holdings",
        "fund_sectors",
        "holdings_news",
        "sector_news",
        "macro_news",
        "affected_funds",
        "sector_funds",
        "metals_spot",
        "stock_snapshot",
        "market_pulse",
        "common_market_news",
        "macro_news_enhanced",
        "fund_universe_search",
        "compare_funds",
        "funds_holding_stock",
        "trace_relationships",
        "expand_news",
    }
)

def _int_list(value: Any) -> list[int]:
    out: list[int] = []
    if not isinstance(value, list):
        return out
    for item in value:
        try:
            out.append(int(item))
        except (TypeError, ValueError):
            continue
    return out


# Aliases normalized at parse time
_TOOL_ALIASES = {
    "fund_holdings": "fund_top_stocks",
    "fund_sectors": "fund_top_sectors",
    "market_pulse": "common_market_news",
    "fund_universe_discovery": "fund_universe_search",
}


@dataclass
class EntityMention:
    raw: str
    role: EntityRole
    cleaned_phrase: str = ""
    why: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityMention:
        role = str(data.get("role") or "fund_scheme").strip()
        if role not in ("fund_scheme", "amc", "holding", "sector", "macro_driver"):
            role = "fund_scheme"
        return cls(
            raw=str(data.get("raw") or "").strip(),
            role=role,  # type: ignore[arg-type]
            cleaned_phrase=str(data.get("cleaned_phrase") or data.get("cleaned") or "").strip(),
            why=str(data.get("why") or "").strip(),
        )


@dataclass
class PlannedTool:
    tool: str
    fund_entity_index: int | None = None
    top_n: int = 5
    semantic_query: str = ""
    sector_name: str = ""
    stock_name: str = ""
    window_days: int | None = None
    entity_filters: list[str] = field(default_factory=list)
    search_focus: str = ""
    purpose: str = ""
    depends_on: str = ""
    category: str = ""
    amc: str = ""
    keyword: str = ""
    driver: str = ""
    target: str = ""
    theme: str = ""
    fund_entity_indexes: list[int] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlannedTool:
        tool = str(data.get("tool") or "").strip()
        tool = _TOOL_ALIASES.get(tool, tool)
        top_n = 5
        try:
            top_n = max(1, min(int(data.get("top_n") or 5), 25))
        except (TypeError, ValueError):
            top_n = 5
        wd = data.get("window_days")
        window_days = None
        if wd is not None:
            try:
                window_days = int(wd)
            except (TypeError, ValueError):
                window_days = None
        fe = data.get("entity_filters") or data.get("entities") or []
        filters = [str(x).strip() for x in fe if str(x).strip()][:12]
        fei = data.get("fund_entity_index")
        fund_entity_index = None
        if fei is not None:
            try:
                fund_entity_index = int(fei)
            except (TypeError, ValueError):
                fund_entity_index = None
        return cls(
            tool=tool,
            fund_entity_index=fund_entity_index,
            top_n=top_n,
            semantic_query=str(data.get("semantic_query") or "").strip(),
            sector_name=str(data.get("sector_name") or "").strip(),
            stock_name=str(data.get("stock_name") or "").strip(),
            window_days=window_days,
            entity_filters=filters,
            search_focus=str(data.get("search_focus") or data.get("focus") or "").strip(),
            purpose=str(data.get("purpose") or "").strip(),
            depends_on=str(data.get("depends_on") or "").strip(),
            category=str(data.get("category") or "").strip(),
            amc=str(data.get("amc") or "").strip(),
            keyword=str(data.get("keyword") or "").strip(),
            driver=str(data.get("driver") or "").strip(),
            target=str(data.get("target") or "").strip(),
            theme=str(data.get("theme") or "").strip(),
            fund_entity_indexes=_int_list(data.get("fund_entity_indexes")),
        )


@dataclass
class AskPlan:
    decline_entirely: bool = False
    decline_message: str = ""
    answer_parts: str = ""
    declined_parts: list[str] = field(default_factory=list)
    sentiment: Sentiment = "any"
    entities: list[EntityMention] = field(default_factory=list)
    tools: list[PlannedTool] = field(default_factory=list)
    affected_funds: AffectedFundsTiming = "none"
    affected_funds_sectors: list[str] = field(default_factory=list)
    affected_funds_top_n: int = 10
    question_reading: dict[str, Any] = field(default_factory=dict)
    relationships_to_check: list[dict[str, Any]] = field(default_factory=list)
    information_gaps: list[str] = field(default_factory=list)
    judge_note: str = ""
    raw_json: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AskPlan:
        sent = str(data.get("sentiment") or "any").strip().lower()
        if sent not in ("positive", "negative", "any"):
            sent = "any"
        af = str(data.get("affected_funds") or "none").strip().lower()
        if af not in ("none", "now", "after_news"):
            af = "none"
        entities: list[EntityMention] = []
        for item in data.get("entities") or []:
            if isinstance(item, dict):
                entities.append(EntityMention.from_dict(item))
        tools: list[PlannedTool] = []
        for item in data.get("tools") or []:
            if isinstance(item, dict):
                pt = PlannedTool.from_dict(item)
                if pt.tool in ALLOWED_PLANNER_TOOLS:
                    tools.append(pt)
        declined = [str(x).strip() for x in (data.get("declined_parts") or []) if str(x).strip()]
        sectors_af = [str(x).strip() for x in (data.get("affected_funds_sectors") or []) if str(x).strip()]
        reading = data.get("question_reading") if isinstance(data.get("question_reading"), dict) else {}
        relationships = [
            item for item in (data.get("relationships_to_check") or []) if isinstance(item, dict)
        ]
        gaps = [str(x).strip() for x in (data.get("information_gaps") or []) if str(x).strip()]
        if not declined and isinstance(reading, dict):
            declined = [str(x).strip() for x in (reading.get("declined_parts") or []) if str(x).strip()]
        if isinstance(reading, dict) and reading.get("sentiment"):
            sent = str(reading.get("sentiment") or sent).strip().lower()
            if sent not in ("positive", "negative", "any"):
                sent = "any"
        try:
            af_top = max(1, min(int(data.get("affected_funds_top_n") or 10), 25))
        except (TypeError, ValueError):
            af_top = 10
        answer_parts = str(data.get("answer_parts") or data.get("answerable_parts") or "").strip()
        if not answer_parts and isinstance(reading, dict):
            answer_parts = str(reading.get("intent") or "").strip()
        return cls(
            decline_entirely=bool(data.get("decline_entirely")),
            decline_message=str(data.get("decline_message") or "").strip(),
            answer_parts=answer_parts,
            declined_parts=declined,
            sentiment=sent,
            entities=entities,
            tools=tools,
            affected_funds=af,
            affected_funds_sectors=sectors_af,
            affected_funds_top_n=af_top,
            question_reading=dict(reading or {}),
            relationships_to_check=relationships,
            information_gaps=gaps,
            raw_json=data,
        )
