"""Structured query plan types for the ask engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

AnswerStyle = Literal[
    "one_metric",
    "short_list",
    "short_table",
    "news_brief",
    "exposure_note",
    "multi_block",
    "refusal",
    "clarification",
    "performance_summary",
]

ALLOWED_TOOLS = frozenset(
    {
        "fund_nav",
        "fund_holdings",
        "fund_sectors",
        "sector_funds",
        "news_search",
        "metals_spot",
        "stock_snapshot",
        "concept",
    }
)

SearchMode = Literal["event_only", "entities_only", "event_plus_entities"]


@dataclass
class DataNeed:
    tool: str
    fund_raw: str = ""
    fund_ref: str = ""
    scope: str = ""
    top_n: int = 5
    stock_name: str = ""
    sector_name: str = ""
    semantic_query: str = ""
    depends_on_portfolio: bool = False
    window_days: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataNeed:
        tool = str(data.get("tool") or "").strip()
        top_n_raw = data.get("top_n")
        top_n = 5
        if top_n_raw is not None:
            try:
                top_n = max(1, min(int(top_n_raw), 25))
            except (TypeError, ValueError):
                top_n = 5
        wd = data.get("window_days")
        window_days = None
        if wd is not None:
            try:
                window_days = int(wd)
            except (TypeError, ValueError):
                window_days = None
        return cls(
            tool=tool,
            fund_raw=str(data.get("fund_raw") or "").strip(),
            fund_ref=str(data.get("fund_ref") or "").strip(),
            scope=str(data.get("scope") or "").strip(),
            top_n=top_n,
            stock_name=str(data.get("stock_name") or "").strip(),
            sector_name=str(data.get("sector_name") or "").strip(),
            semantic_query=str(data.get("semantic_query") or "").strip(),
            depends_on_portfolio=bool(data.get("depends_on_portfolio")),
            window_days=window_days,
        )


@dataclass
class SubQuery:
    id: str
    text: str
    answer_style: AnswerStyle
    needs_reasoning: bool
    data_needs: list[DataNeed] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubQuery:
        style = str(data.get("answer_style") or "short_list").strip()
        if style not in (
            "one_metric",
            "short_list",
            "short_table",
            "news_brief",
            "exposure_note",
            "multi_block",
            "refusal",
            "clarification",
            "performance_summary",
        ):
            style = "short_list"
        needs_raw = data.get("data_needs") or []
        needs: list[DataNeed] = []
        if isinstance(needs_raw, list):
            for item in needs_raw:
                if isinstance(item, dict):
                    need = DataNeed.from_dict(item)
                    if need.tool in ALLOWED_TOOLS:
                        needs.append(need)
        return cls(
            id=str(data.get("id") or "Q1").strip() or "Q1",
            text=str(data.get("text") or "").strip(),
            answer_style=style,
            needs_reasoning=bool(data.get("needs_reasoning")),
            data_needs=needs,
        )


@dataclass
class ScopeRefinement:
    news_entities: list[str] = field(default_factory=list)
    news_topics: list[str] = field(default_factory=list)
    search_mode: SearchMode = "event_only"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScopeRefinement:
        mode = str(data.get("search_mode") or "event_only").strip()
        if mode not in ("event_only", "entities_only", "event_plus_entities"):
            mode = "event_only"
        ent = data.get("news_entities") or []
        topics = data.get("news_topics") or []
        entities = [str(x).strip() for x in ent if str(x).strip()][:8]
        topic_list = [str(x).strip() for x in topics if str(x).strip()][:5]
        return cls(news_entities=entities, news_topics=topic_list, search_mode=mode)


@dataclass
class QueryPlan:
    sub_queries: list[SubQuery] = field(default_factory=list)
    raw_json: dict[str, Any] = field(default_factory=dict)
    source: str = "llm"

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, source: str = "llm") -> QueryPlan:
        raw = data.get("sub_queries") or []
        subs: list[SubQuery] = []
        if isinstance(raw, list):
            for i, item in enumerate(raw[:4]):
                if isinstance(item, dict):
                    sq = SubQuery.from_dict(item)
                    if not sq.id:
                        sq.id = f"Q{i + 1}"
                    subs.append(sq)
        return cls(sub_queries=subs, raw_json=data, source=source)
