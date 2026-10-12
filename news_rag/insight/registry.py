"""Tool registry: provides / requires / fan-out / fallbacks — single dispatch source."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from news_rag.insight.facets import EVIDENCE_FACETS

ToolRunner = Callable[..., dict[str, Any]]


@dataclass
class ToolSpec:
    name: str
    provides: frozenset[str]
    requires: frozenset[str] = frozenset()
    fan_out_over: str = ""  # e.g. "fund" — run once per item in prior step output
    cost: int = 1
    limits: str = ""
    description: str = ""
    when_to_use: str = ""
    fallbacks: list[str] = field(default_factory=list)
    run: ToolRunner | None = None


# When several tools satisfy the same facet, gather picks the first listed here.
FACET_TOOL_PREFERENCE: dict[str, list[str]] = {
    "news_drivers": ["layered_news", "sector_news_signal", "market_pulse"],
    "entity_state_over_time": ["layered_news", "index_series", "market_pulse"],
    "benchmark": ["index_series"],
    "exposure_link": ["sector_funds"],
    "fund_composition": ["fund_composition"],
    "return_series": ["fund_return_series", "fund_nav"],
    "fund_facts_nav": ["fund_nav"],
    "fund_facts_holdings": ["fund_composition"],
    "market_overview": ["market_pulse", "layered_news"],
    "peer_rank": ["sector_funds"],
    "forward_view": ["layered_news", "market_pulse"],
}


_REGISTRY: dict[str, ToolSpec] = {}


def register(spec: ToolSpec) -> None:
    for facet in spec.provides:
        if facet not in EVIDENCE_FACETS:
            raise ValueError(f"Unknown facet {facet} on tool {spec.name}")
    _REGISTRY[spec.name] = spec


def get_tool(name: str) -> ToolSpec | None:
    return _REGISTRY.get(name)


def all_tools() -> list[ToolSpec]:
    return list(_REGISTRY.values())


def tools_providing(facet: str) -> list[ToolSpec]:
    return [t for t in _REGISTRY.values() if facet in t.provides]


def pick_tool_for_facet(facet: str) -> ToolSpec | None:
    """Choose one tool for a facet using FACET_TOOL_PREFERENCE, then cost."""
    providers = tools_providing(facet)
    if not providers:
        return None
    by_name = {p.name: p for p in providers}
    for name in FACET_TOOL_PREFERENCE.get(facet, []):
        if name in by_name:
            return by_name[name]
    return sorted(providers, key=lambda t: (t.cost, t.name))[0]


def facet_to_tool_names() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {f: [] for f in EVIDENCE_FACETS}
    for spec in _REGISTRY.values():
        for f in spec.provides:
            out.setdefault(f, []).append(spec.name)
    return out


def registry_prompt_block() -> str:
    lines = [
        "Evidence facets (gather runs tools to fill these — use ONLY facet ids in evidence_needs):",
        "entity_state_over_time, news_drivers, exposure_link, fund_composition, return_series, "
        "benchmark, forward_view, fund_facts_nav, fund_facts_holdings, market_overview, peer_rank.",
        "",
        "Facet → preferred tool:",
    ]
    for facet, names in sorted(FACET_TOOL_PREFERENCE.items()):
        lines.append(f"  {facet}: {', '.join(names)}")
    lines.append("")
    lines.append("Registered tools:")
    for spec in sorted(_REGISTRY.values(), key=lambda s: s.name):
        provides = ", ".join(sorted(spec.provides))
        req = ", ".join(sorted(spec.requires)) if spec.requires else "none"
        desc = (spec.description or spec.name).strip()
        when = (spec.when_to_use or "").strip()
        lines.append(f"- {spec.name}: [{provides}]")
        lines.append(f"    {desc}")
        if when:
            lines.append(f"    Use when: {when}")
        if spec.requires:
            lines.append(f"    Requires facets satisfied first: {req}")
        if spec.fan_out_over:
            lines.append(f"    Fan-out: once per fund from exposure_link (cap applies).")
        if spec.limits:
            lines.append(f"    Limits: {spec.limits}")
    return "\n".join(lines)


def _lazy_register() -> None:
    if _REGISTRY:
        return
    from news_rag.insight.tool_runners import build_default_registry

    build_default_registry()


def ensure_registry() -> None:
    _lazy_register()
