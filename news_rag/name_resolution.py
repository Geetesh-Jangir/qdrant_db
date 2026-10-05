"""Resolve planner entity mentions against the fund catalog."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

from news_rag.ask_plan import AskPlan, EntityMention
from news_rag.fund_match import fold_fund_spelling
from news_rag.fund_search import lookup_extracted_fund

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger


@dataclass
class ResolvedScheme:
    entity: EntityMention
    detail: dict[str, Any] | None = None
    ambiguous: bool = False
    close_matches: list[str] = field(default_factory=list)
    match_method: str = ""
    canonical_name: str = ""


@dataclass
class ResolvedNames:
    schemes: list[ResolvedScheme] = field(default_factory=list)
    holdings: list[str] = field(default_factory=list)
    sectors: list[str] = field(default_factory=list)
    amc_only: list[str] = field(default_factory=list)
    primary_scheme: dict[str, Any] | None = None
    ambiguous: bool = False
    close_matches: list[str] = field(default_factory=list)

    def scheme_detail(self, index: int | None) -> dict[str, Any] | None:
        if index is None:
            return self.primary_scheme
        if 0 <= index < len(self.schemes):
            return self.schemes[index].detail
        return self.primary_scheme


def _lookup_phrase(phrase: str) -> tuple[dict[str, Any] | None, bool, list[str], str]:
    folded = fold_fund_spelling(phrase)
    if folded.upper().startswith("INF"):
        detail, amb, close = lookup_extracted_fund(isin=folded.upper())
    else:
        detail, amb, close = lookup_extracted_fund(name=folded)
    method = "catalog"
    return detail, amb, close, method


def resolve_plan_names(plan: AskPlan, *, query_log: QueryLogger | None = None) -> ResolvedNames:
    out = ResolvedNames()
    scheme_entities = [e for e in plan.entities if e.role == "fund_scheme"]
    if not scheme_entities:
        for tool in plan.tools:
            if tool.tool.startswith("fund_") and tool.fund_entity_index is not None:
                pass
    for ent in plan.entities:
        if ent.role == "holding":
            name = ent.cleaned_phrase or ent.raw
            if name:
                out.holdings.append(name)
        elif ent.role == "sector":
            name = ent.cleaned_phrase or ent.raw
            if name:
                out.sectors.append(name)
        elif ent.role == "amc":
            name = ent.cleaned_phrase or ent.raw
            if name:
                out.amc_only.append(name)

    for ent in scheme_entities:
        phrase = ent.cleaned_phrase or ent.raw
        if not phrase:
            continue
        detail, amb, close, method = _lookup_phrase(phrase)
        canonical = ""
        if detail and not amb:
            canonical = str(detail.get("fund_short_name") or detail.get("fund_name") or "")
        rs = ResolvedScheme(
            entity=ent,
            detail=detail if not amb else None,
            ambiguous=amb,
            close_matches=close,
            match_method=method,
            canonical_name=canonical,
        )
        out.schemes.append(rs)
        if query_log is not None:
            query_log.log_stage(
                "name_resolve",
                raw=ent.raw,
                role=ent.role,
                phrase=phrase,
                canonical=canonical,
                ambiguous=amb,
                close=close[:5],
                method=method,
            )
        if amb:
            out.ambiguous = True
            out.close_matches = close
        elif detail and not out.primary_scheme:
            out.primary_scheme = detail

    if not out.schemes and plan.tools:
        for tool in plan.tools:
            if tool.tool.startswith("fund_") and tool.fund_entity_index is None:
                for ent in plan.entities:
                    if ent.role == "fund_scheme":
                        phrase = ent.cleaned_phrase or ent.raw
                        if phrase:
                            detail, amb, close, method = _lookup_phrase(phrase)
                            if detail and not amb and not out.primary_scheme:
                                out.primary_scheme = detail
                            break

    return out
