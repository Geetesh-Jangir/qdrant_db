"""LLM ask planner types — single plan per user question."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Sentiment = Literal["positive", "negative", "any"]
EntityRole = Literal["fund_scheme", "amc", "holding", "sector"]
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
    }
)

# Aliases normalized at parse time
_TOOL_ALIASES = {
    "fund_holdings": "fund_top_stocks",
    "fund_sectors": "fund_top_sectors",
}


@dataclass
class EntityMention:
    raw: str
    role: EntityRole
    cleaned_phrase: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntityMention:
        role = str(data.get("role") or "fund_scheme").strip()
        if role not in ("fund_scheme", "amc", "holding", "sector"):
            role = "fund_scheme"
        return cls(
            raw=str(data.get("raw") or "").strip(),
            role=role,
            cleaned_phrase=str(data.get("cleaned_phrase") or data.get("cleaned") or "").strip(),
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
        try:
            af_top = max(1, min(int(data.get("affected_funds_top_n") or 10), 25))
        except (TypeError, ValueError):
            af_top = 10
        return cls(
            decline_entirely=bool(data.get("decline_entirely")),
            decline_message=str(data.get("decline_message") or "").strip(),
            answer_parts=str(data.get("answer_parts") or data.get("answerable_parts") or "").strip(),
            declined_parts=declined,
            sentiment=sent,
            entities=entities,
            tools=tools,
            affected_funds=af,
            affected_funds_sectors=sectors_af,
            affected_funds_top_n=af_top,
            raw_json=data,
        )
