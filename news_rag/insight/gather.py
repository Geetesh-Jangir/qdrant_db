"""Phase 2: gather evidence — spec-driven tool planner with a coverage ledger.

How a run works:
  1. The brief's `evidence_needs` (facets) are expanded with the facets that chosen tools
     `requires` (dependency closure).
  2. Each round, every pending facet is mapped to a tool (`pick_tool_for_facet`, honouring
     `applies(ctx)`); tools whose prerequisites are not satisfied yet wait for a later round.
  3. Per-fund tools (`fan_out_over="fund"`) run once per shortlisted fund. The shortlist comes
     from named funds in the brief and/or the exposure/screen tool result.
  4. A failed facet is retried with a different provider before it is marked unavailable.
  5. Every call is logged, and results are cached per (tool, fund) so two facets that map to
     the same tool do not call it twice.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

from news_rag.config import get_settings
from news_rag.insight.brief import QuestionBrief
from news_rag.insight.facets import canonical_facet
from news_rag.insight.registry import ToolSpec, ensure_registry, get_tool, pick_tool_for_facet

LedgerStatus = Literal["satisfied", "partial", "missing", "unavailable"]

MIN_ROUNDS = 5  # news -> exposure -> per-fund -> per-fund dependents -> slack


@dataclass
class LedgerEntry:
    facet: str
    status: LedgerStatus = "missing"
    reason: str = ""
    tool: str = ""
    implied: bool = False  # added by dependency closure, not asked for by the brief


@dataclass
class EvidenceItem:
    facet: str
    tool: str
    entity_key: str
    data: dict[str, Any]
    as_of: str = ""


@dataclass
class EvidenceSet:
    items: list[EvidenceItem] = field(default_factory=list)
    articles: list[dict[str, Any]] = field(default_factory=list)
    ledger: list[LedgerEntry] = field(default_factory=list)
    tool_runs: list[dict[str, Any]] = field(default_factory=list)

    def by_facet(self, facet: str) -> list[EvidenceItem]:
        target = canonical_facet(facet)
        return [i for i in self.items if canonical_facet(i.facet) == target]


@dataclass
class GatherContext:
    question: str
    brief: QuestionBrief
    date_from: str | None = None
    date_to: str | None = None
    min_impact: int | None = None
    source: str | None = None
    direction: str | None = None
    fan_out_cap: int = 8
    query_log: Any = None


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


def _base_ctx(gctx: GatherContext) -> dict[str, Any]:
    b = gctx.brief
    sector = b.primary_sector()
    driver_text = " ".join(d.replace("_", " ") for d in b.drivers[:2])
    direction = gctx.direction if gctx.direction in ("positive", "negative") else (b.direction or "any")
    commodity = ""
    if "gold" in gctx.question.lower() or "silver" in gctx.question.lower():
        commodity = "gold silver price"
    return {
        "question": gctx.question,
        "sector_name": sector,
        "sector_keys": list(b.sector_keys),
        "subject": sector or (b.drivers[0] if b.drivers else "") or (b.funds[0] if b.funds else ""),
        "semantic_query": sector or driver_text or commodity or gctx.question[:200],
        "drivers": list(b.drivers),
        "driver_direction": b.driver_direction,
        "fund_names": list(b.funds),
        "stock_name": b.stocks[0] if b.stocks else "",
        "window_days": b.window_days,
        "return_window": b.return_window(),
        "date_from": gctx.date_from,
        "date_to": gctx.date_to,
        "min_impact": gctx.min_impact,
        "source": gctx.source,
        "direction": direction,
        "top_n": gctx.fan_out_cap,
        "layer": "sector_news",
    }


def _seed_named_funds(brief: QuestionBrief) -> list[dict[str, Any]]:
    """Funds the user named are the shortlist from the start (no exposure tool needed)."""
    if not brief.funds:
        return []
    from news_rag.fund_search import get_fund_index

    idx = get_fund_index()
    out: list[dict[str, Any]] = []
    for name in brief.funds[:4]:
        detail, _amb, _close = idx.lookup_extracted_fund(name=name)
        if detail and detail.get("isin"):
            out.append(
                {
                    "isin": str(detail["isin"]),
                    "fund_name": str(detail.get("fund_short_name") or detail.get("fund_name") or name),
                    "named": True,
                }
            )
    return out


# ---------------------------------------------------------------------------
# Tool execution helpers
# ---------------------------------------------------------------------------


def _run_tool(name: str, ctx: dict[str, Any]) -> dict[str, Any]:
    ensure_registry()
    spec = get_tool(name)
    if not spec or not spec.run:
        return {"ok": False, "error": f"unknown_tool:{name}"}
    started = time.perf_counter()
    try:
        out = spec.run(ctx)
        elapsed = (time.perf_counter() - started) * 1000
        if not isinstance(out, dict):
            return {"ok": False, "error": "tool_returned_non_dict"}
        if "ok" not in out:
            out = {"ok": True, "data": out, "elapsed_ms": elapsed}
        else:
            out.setdefault("elapsed_ms", elapsed)
        return out
    except Exception as exc:  # noqa: BLE001 - tool errors become ledger reasons
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def _extract_funds_from_result(data: dict[str, Any]) -> list[dict[str, Any]]:
    rankings = data.get("rankings") or []
    if not rankings and isinstance(data.get("data"), dict):
        rankings = data["data"].get("rankings") or []
    if not rankings:
        rankings = data.get("funds") or []
    out: list[dict[str, Any]] = []
    for row in rankings:
        if not isinstance(row, dict):
            continue
        isin = str(row.get("isin") or "").strip()
        name = str(row.get("fund_name") or row.get("name") or "").strip()
        if isin or name:
            out.append({**row, "isin": isin, "fund_name": name})
    return out


def _collect_articles(tool_result: dict[str, Any]) -> list[dict[str, Any]]:
    arts: list[dict[str, Any]] = []
    data = tool_result.get("data") if isinstance(tool_result.get("data"), dict) else tool_result
    if not isinstance(data, dict):
        return arts
    for key in ("articles", "rows", "items"):
        block = data.get(key)
        if isinstance(block, list):
            for a in block:
                if isinstance(a, dict) and (a.get("title") or a.get("url") or a.get("snippet")):
                    arts.append(a)
    return arts


def _article_key(a: dict[str, Any]) -> str:
    return str(a.get("url") or a.get("title") or id(a)).strip().lower()


def _update_ledger(
    ledger: dict[str, LedgerEntry], facet: str, status: LedgerStatus, reason: str = "", tool: str = ""
) -> None:
    entry = ledger.get(facet) or LedgerEntry(facet=facet)
    entry.status = status
    entry.reason = reason if (reason or status == "satisfied") else entry.reason
    if tool:
        entry.tool = tool
    ledger[facet] = entry


def _prewarm_tool_modules() -> None:
    """Import tool adapters (and what they lazily import) before the thread pool starts."""
    ensure_registry()
    from news_rag.insight import tool_runners as _  # noqa: F401
    from news_rag.tools import run_layered_news, run_sector_funds  # noqa: F401


def _close_dependencies(
    facets: list[str], ctx: dict[str, Any], ledger: dict[str, LedgerEntry]
) -> None:
    """Add facets that the chosen tools need first (e.g. driver_affected_funds needs news)."""
    queue = list(facets)
    seen = set(queue)
    while queue:
        facet = queue.pop(0)
        spec = pick_tool_for_facet(facet, ctx)
        if not spec:
            continue
        for dep in sorted(spec.requires):
            if dep not in seen:
                seen.add(dep)
                queue.append(dep)
                if dep not in ledger:
                    ledger[dep] = LedgerEntry(facet=dep, status="missing", implied=True)


def _requires_met(spec: ToolSpec, ledger: dict[str, LedgerEntry]) -> tuple[bool, bool]:
    """(ready, blocked_forever)."""
    for dep in spec.requires:
        entry = ledger.get(dep)
        if entry is None:
            return False, True
        if entry.status == "unavailable":
            return False, True
        if entry.status != "satisfied":
            return False, False
    return True, False


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def gather_evidence(gctx: GatherContext, *, max_rounds: int | None = None) -> EvidenceSet:
    settings = get_settings()
    rounds = max(max_rounds or int(settings.ask_agent_max_rounds), MIN_ROUNDS)
    _prewarm_tool_modules()

    evidence = EvidenceSet()
    ctx = _base_ctx(gctx)
    shortlist = _seed_named_funds(gctx.brief)
    ledger_map: dict[str, LedgerEntry] = {
        f: LedgerEntry(facet=f, status="missing") for f in gctx.brief.evidence_needs
    }
    ctx["_articles"] = evidence.articles
    ctx["_funds"] = shortlist
    ctx["_composition"] = {}
    _close_dependencies(list(ledger_map), ctx, ledger_map)

    tried: dict[str, set[str]] = {f: set() for f in ledger_map}
    cache: dict[tuple[str, str], dict[str, Any]] = {}
    seen_articles: set[str] = set()

    def _log(msg: str, **fields: Any) -> None:
        if gctx.query_log is not None:
            gctx.query_log.note(msg, **fields)

    for round_i in range(rounds):
        pending = [f for f, e in ledger_map.items() if e.status in ("missing", "partial")]
        if not pending:
            break

        ctx["_articles"] = evidence.articles
        ctx["_funds"] = shortlist

        jobs: list[tuple[str, dict[str, Any], str, str]] = []  # (tool, ctx, facet, isin)
        for facet in pending:
            spec = pick_tool_for_facet(facet, ctx, exclude=tried[facet])
            if spec is None:
                reason = "all_providers_failed" if tried[facet] else "no_applicable_tool"
                _update_ledger(ledger_map, facet, "unavailable", reason)
                continue
            ready, blocked = _requires_met(spec, ledger_map)
            if blocked:
                _update_ledger(ledger_map, facet, "unavailable", f"dependency_unavailable:{spec.name}", spec.name)
                continue
            if not ready:
                continue  # wait for a later round
            if spec.fan_out_over == "fund":
                if not shortlist:
                    still_possible = any(
                        e.status in ("missing", "partial")
                        for f, e in ledger_map.items()
                        if f in ("exposure_link", "fund_screen")
                    )
                    if not still_possible:
                        _update_ledger(ledger_map, facet, "unavailable", "no_fund_shortlist", spec.name)
                    continue
                cap = spec.fan_out_cap or gctx.fan_out_cap
                for fund in shortlist[:cap]:
                    jobs.append(
                        (
                            spec.name,
                            {**ctx, "isin": fund.get("isin"), "fund_name": fund.get("fund_name")},
                            facet,
                            str(fund.get("isin") or ""),
                        )
                    )
            else:
                jobs.append((spec.name, ctx, facet, ""))

        if not jobs:
            # Nothing runnable: whatever is still waiting can never be satisfied.
            for facet in pending:
                e = ledger_map[facet]
                if e.status == "missing":
                    _update_ledger(ledger_map, facet, "unavailable", "prerequisite_never_met")
            break

        # Run each distinct (tool, isin) once, in parallel; reuse cached results across facets.
        to_run: dict[tuple[str, str], dict[str, Any]] = {}
        for name, jctx, _facet, isin in jobs:
            key = (name, isin)
            if key not in cache and key not in to_run:
                to_run[key] = jctx
        if to_run:
            with ThreadPoolExecutor(max_workers=6) as pool:
                futs = {pool.submit(_run_tool, k[0], c): k for k, c in to_run.items()}
                for fut in as_completed(futs):
                    key = futs[fut]
                    try:
                        cache[key] = fut.result()
                    except Exception as exc:  # noqa: BLE001
                        cache[key] = {"ok": False, "error": str(exc)}
                    res = cache[key]
                    if gctx.query_log is not None:
                        gctx.query_log.log_tool_invocation(
                            tool=key[0],
                            facet=",".join(sorted({j[2] for j in jobs if (j[0], j[3]) == key})),
                            ok=bool(res.get("ok")),
                            elapsed_ms=float(res.get("elapsed_ms") or 0) or None,
                            error="" if res.get("ok") else str(res.get("error") or "tool_failed"),
                            detail=(key[1] or str(ctx.get("sector_name") or ctx.get("subject") or ""))[:80],
                        )

        # Fold results into evidence, facet by facet.
        by_facet: dict[str, list[tuple[str, str, dict[str, Any]]]] = {}
        for name, _jctx, facet, isin in jobs:
            by_facet.setdefault(facet, []).append((name, isin, cache[(name, isin)]))

        for facet, results in by_facet.items():
            good = [(n, i, r) for n, i, r in results if r.get("ok")]
            tool_name = results[0][0]
            tried[facet].add(tool_name)
            evidence.tool_runs.append(
                {"tool": tool_name, "facet": facet, "ok": bool(good), "round": round_i, "runs": len(results)}
            )
            if not good:
                # Try the tool's declared fallbacks (same ctx), then another provider next round.
                spec = get_tool(tool_name)
                recovered = False
                for fb in (spec.fallbacks if spec else []):
                    if fb in tried[facet]:
                        continue
                    tried[facet].add(fb)
                    fb_spec = get_tool(fb)
                    if fb_spec and fb_spec.applies and not fb_spec.applies(ctx):
                        continue
                    key = (fb, "")
                    if key not in cache:
                        cache[key] = _run_tool(fb, ctx)
                        if gctx.query_log is not None:
                            gctx.query_log.log_tool_invocation(
                                tool=fb,
                                facet=facet,
                                ok=bool(cache[key].get("ok")),
                                elapsed_ms=float(cache[key].get("elapsed_ms") or 0) or None,
                                error="" if cache[key].get("ok") else str(cache[key].get("error") or ""),
                                detail=f"fallback_for:{tool_name}",
                            )
                    if cache[key].get("ok"):
                        good = [(fb, "", cache[key])]
                        tool_name = fb
                        recovered = True
                        break
                if not recovered:
                    err = str(results[0][2].get("error") or "tool_failed")
                    _update_ledger(ledger_map, facet, "partial", err, tool_name)
                    continue

            for name, isin, res in good:
                data = res.get("data") if isinstance(res.get("data"), dict) else res
                if not isinstance(data, dict):
                    data = {"raw": data}
                evidence.items.append(
                    EvidenceItem(
                        facet=facet,
                        tool=name,
                        entity_key=isin or str(ctx.get("subject") or ""),
                        data=data,
                    )
                )
                for art in _collect_articles(res):
                    k = _article_key(art)
                    if k not in seen_articles:
                        seen_articles.add(k)
                        evidence.articles.append(art)
                if name == "fund_composition" and isin:
                    ctx["_composition"][isin.upper()] = data
                if facet == "sector_impact_direction":
                    ctx["_sector_picks"] = data.get("sector_picks") or []
                if facet in ("exposure_link", "fund_screen"):
                    if any(f.get("named") for f in shortlist):
                        pass  # keep user-named schemes; do not dilute with sector screens
                    else:
                        existing = {f.get("isin") for f in shortlist}
                        for row in _extract_funds_from_result(data):
                            if row.get("isin") and row["isin"] not in existing:
                                shortlist.append(row)
                                existing.add(row["isin"])
            reason = f"{len(good)}/{len(results)} runs ok" if len(results) > 1 else ""
            _update_ledger(ledger_map, facet, "satisfied", reason, tool_name)

    # Anything still unresolved at the end is unavailable (with the last known reason).
    for e in ledger_map.values():
        if e.status in ("missing", "partial"):
            e.status = "unavailable"
            e.reason = e.reason or "not_reached"

    evidence.ledger = list(ledger_map.values())
    if gctx.query_log is not None:
        gctx.query_log.log_gather_ledger(
            [
                {"facet": e.facet, "status": e.status, "tool": e.tool, "reason": e.reason}
                for e in evidence.ledger
            ],
            articles=len(evidence.articles),
            tool_runs=len(evidence.tool_runs),
        )
    return evidence
