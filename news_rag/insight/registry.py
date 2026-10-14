"""Tool registry: provides / requires / fan-out / fallbacks — single dispatch source.

Every tool carries the guidance the planner needs to call it well: what it returns,
when to use it, when NOT to use it, its arguments, and the prerequisites it needs.
`registry_prompt_block()` renders all of that for the brief LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from news_rag.insight.facets import EVIDENCE_FACETS, canonical_facet

ToolRunner = Callable[..., dict[str, Any]]
Applies = Callable[[dict[str, Any]], bool]


@dataclass
class ToolSpec:
    name: str
    provides: frozenset[str]
    requires: frozenset[str] = frozenset()
    fan_out_over: str = ""  # "fund" — run once per shortlisted fund
    fan_out_cap: int = 0  # 0 = use the global insight_fan_out_cap
    cost: int = 1
    description: str = ""
    when_to_use: str = ""
    avoid_when: str = ""
    args: tuple[tuple[str, str], ...] = ()  # (ctx key, meaning)
    limits: str = ""
    fallbacks: list[str] = field(default_factory=list)
    applies: Applies | None = None  # context gate: only eligible when this returns True
    run: ToolRunner | None = None


_REGISTRY: dict[str, ToolSpec] = {}


# When several tools can satisfy a facet, the first eligible one in this list is used.
FACET_TOOL_PREFERENCE: dict[str, list[str]] = {
    "news_drivers": ["fund_portfolio_news", "macro_news_enhanced", "layered_news", "sector_news_signal", "market_pulse"],
    "entity_state_over_time": ["layered_news", "index_series", "market_pulse"],
    "benchmark": ["index_series"],
    "exposure_link": ["driver_affected_funds", "sector_funds", "screen_funds"],
    "fund_screen": ["screen_funds"],
    "fund_composition": ["fund_composition"],
    "return_series": ["fund_return_series", "fund_nav"],
    "fund_facts_nav": ["fund_nav"],
    "fund_facts_holdings": ["fund_composition"],
    "market_overview": ["market_pulse", "layered_news"],
    "peer_rank": ["sector_funds", "screen_funds"],
    "forward_view": ["layered_news", "market_pulse"],
    "sector_impact_direction": ["affected_sectors"],
    "relationship_trace": ["trace_relationships"],
    "macro_driver_map": ["macro_sector_impact"],
    "fund_vs_index": ["sector_alignment"],
    "holding_drivers": ["fund_portfolio_news", "holding_news"],
    "stock_holders": ["stock_holders"],
    "peer_compare": ["compare_funds"],
    "commodity_spot": ["metals_spot"],
    "stock_price": ["stock_snapshot"],
    "sector_holdings": ["sector_holdings"],
}


def register(spec: ToolSpec) -> None:
    for facet in spec.provides | spec.requires:
        if facet not in EVIDENCE_FACETS:
            raise ValueError(f"Unknown facet {facet} on tool {spec.name}")
    _REGISTRY[spec.name] = spec


def get_tool(name: str) -> ToolSpec | None:
    return _REGISTRY.get(name)


def all_tools() -> list[ToolSpec]:
    return list(_REGISTRY.values())


def tools_providing(facet: str) -> list[ToolSpec]:
    canon = canonical_facet(facet)
    return [
        t for t in _REGISTRY.values()
        if facet in t.provides or canon in {canonical_facet(p) for p in t.provides}
    ]


def _eligible(spec: ToolSpec, ctx: dict[str, Any] | None) -> bool:
    if spec.applies is None or ctx is None:
        return True
    try:
        return bool(spec.applies(ctx))
    except Exception:
        return False


def pick_tool_for_facet(
    facet: str,
    ctx: dict[str, Any] | None = None,
    exclude: set[str] | frozenset[str] | tuple[str, ...] = (),
) -> ToolSpec | None:
    """Choose one tool for a facet: preference order, gated by `applies(ctx)`, then cost.

    `exclude` lets gather retry a facet with a different provider after a failure.
    Tools whose `applies` gate is False are never returned when a ctx is given.
    """
    skip = set(exclude)
    providers = [p for p in tools_providing(facet) if p.name not in skip]
    if not providers:
        return None
    by_name = {p.name: p for p in providers}
    for name in FACET_TOOL_PREFERENCE.get(facet, []):
        spec = by_name.get(name)
        if spec and _eligible(spec, ctx):
            return spec
    eligible = [p for p in providers if _eligible(p, ctx)]
    if not eligible:
        return None
    return sorted(eligible, key=lambda t: (t.cost, t.name))[0]


def facet_to_tool_names() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {f: [] for f in EVIDENCE_FACETS}
    for spec in _REGISTRY.values():
        for f in spec.provides:
            out.setdefault(f, []).append(spec.name)
    return out


def registry_prompt_block() -> str:
    """Planner-facing tool catalog. The planner never names tools — it names facets."""
    lines = [
        "FACETS you may list in evidence_needs (gather maps each facet to the best tool):",
        ", ".join(sorted(EVIDENCE_FACETS)),
        "",
        "TOOL CATALOG (tool: facets it fills):",
    ]
    for spec in sorted(_REGISTRY.values(), key=lambda s: s.name):
        provides = ", ".join(sorted(spec.provides))
        lines.append(f"- {spec.name}: fills [{provides}]")
        if spec.description:
            lines.append(f"    returns: {spec.description.strip()}")
        if spec.when_to_use:
            lines.append(f"    use when: {spec.when_to_use.strip()}")
        if spec.avoid_when:
            lines.append(f"    do NOT use when: {spec.avoid_when.strip()}")
        if spec.args:
            lines.append("    args: " + "; ".join(f"{k} = {v}" for k, v in spec.args))
        if spec.requires:
            lines.append(f"    needs first: {', '.join(sorted(spec.requires))}")
        if spec.fan_out_over:
            lines.append("    runs once per shortlisted fund")
        if spec.limits:
            lines.append(f"    limits: {spec.limits.strip()}")
    return "\n".join(lines)


def _lazy_register() -> None:
    if _REGISTRY:
        return
    from news_rag.insight.tool_runners import build_default_registry

    build_default_registry()


def ensure_registry() -> None:
    _lazy_register()
