"""Phase 2: Gather evidence with coverage ledger and fan-out."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Literal, TYPE_CHECKING

if TYPE_CHECKING:
    from news_rag.query_log import QueryLogger

from news_rag.config import get_settings
from news_rag.insight.brief import QuestionBrief
from news_rag.insight.registry import ensure_registry, get_tool, pick_tool_for_facet

LedgerStatus = Literal["satisfied", "partial", "missing", "unavailable"]


@dataclass
class LedgerEntry:
    facet: str
    status: LedgerStatus = "missing"
    reason: str = ""
    tool: str = ""


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
        return [i for i in self.items if i.facet == facet]


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


def _base_ctx(gctx: GatherContext) -> dict[str, Any]:
    b = gctx.brief
    sector = b.primary_sector()
    return {
        "question": gctx.question,
        "sector_name": sector,
        "subject": sector,
        "semantic_query": sector or gctx.question[:200],
        "window_days": b.window_days,
        "return_window": f"{max(1, b.window_days // 30)}m",
        "date_from": gctx.date_from,
        "date_to": gctx.date_to,
        "min_impact": gctx.min_impact,
        "source": gctx.source,
        "direction": gctx.direction,
        "top_n": gctx.fan_out_cap,
        "layer": "sector_news",
    }


def _run_tool(name: str, ctx: dict[str, Any]) -> dict[str, Any]:
    ensure_registry()
    spec = get_tool(name)
    if not spec or not spec.run:
        return {"ok": False, "error": f"unknown_tool:{name}"}
    started = time.perf_counter()
    try:
        out = spec.run(ctx)
        elapsed = (time.perf_counter() - started) * 1000
        if isinstance(out, dict) and "ok" not in out:
            out = {"ok": True, "data": out, "elapsed_ms": elapsed}
        elif isinstance(out, dict):
            out.setdefault("elapsed_ms", elapsed)
        return out
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _extract_funds_from_sector_result(data: dict[str, Any]) -> list[dict[str, Any]]:
    rankings = data.get("rankings") or []
    if not rankings and isinstance(data.get("data"), dict):
        rankings = data["data"].get("rankings") or []
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
                if isinstance(a, dict):
                    arts.append(a)
    return arts


def _update_ledger(ledger: dict[str, LedgerEntry], facet: str, status: LedgerStatus, reason: str = "", tool: str = "") -> None:
    entry = ledger.get(facet) or LedgerEntry(facet=facet)
    entry.status = status
    if status == "satisfied":
        entry.reason = reason
    elif reason:
        entry.reason = reason
    if tool:
        entry.tool = tool
    ledger[facet] = entry


def _prewarm_tool_modules() -> None:
    """Import tool adapters before ThreadPoolExecutor (avoids import deadlocks)."""
    ensure_registry()
    from news_rag.insight import tool_runners as _  # noqa: F401
    from news_rag.tools import run_layered_news, run_sector_funds  # noqa: F401


def gather_evidence(gctx: GatherContext, *, max_rounds: int | None = None) -> EvidenceSet:
    settings = get_settings()
    rounds = max_rounds or int(settings.ask_agent_max_rounds)
    _prewarm_tool_modules()
    evidence = EvidenceSet()
    ledger_map: dict[str, LedgerEntry] = {
        f: LedgerEntry(facet=f, status="missing") for f in gctx.brief.evidence_needs
    }
    ctx = _base_ctx(gctx)
    shortlisted_funds: list[dict[str, Any]] = []

    for round_i in range(rounds):
        pending = [f for f, e in ledger_map.items() if e.status in ("missing", "partial")]
        if not pending:
            break

        jobs: list[tuple[str, dict[str, Any], str]] = []

        for facet in pending:
            if facet in ("fund_composition", "return_series"):
                if shortlisted_funds:
                    spec_name = "fund_composition" if facet == "fund_composition" else "fund_return_series"
                    for fund in shortlisted_funds[: gctx.fan_out_cap]:
                        fctx = {
                            **ctx,
                            "isin": fund.get("isin"),
                            "fund_name": fund.get("fund_name"),
                        }
                        jobs.append((spec_name, fctx, facet))
                continue
            tool = pick_tool_for_facet(facet)
            if not tool:
                _update_ledger(ledger_map, facet, "unavailable", "no_tool_registered")
                continue
            jobs.append((tool.name, ctx, facet))

        if not jobs:
            break

        results: list[tuple[str, str, dict[str, Any]]] = []
        with ThreadPoolExecutor(max_workers=6) as pool:
            futs = {
                pool.submit(_run_tool, name, jctx): (name, facet)
                for name, jctx, facet in jobs
            }
            for fut in as_completed(futs):
                name, facet = futs[fut]
                try:
                    results.append((name, facet, fut.result()))
                except Exception as exc:
                    results.append((name, facet, {"ok": False, "error": str(exc)}))

        for name, facet, res in results:
            evidence.tool_runs.append({"tool": name, "facet": facet, "ok": res.get("ok"), "round": round_i})
            if gctx.query_log is not None:
                gctx.query_log.log_tool_invocation(
                    tool=name,
                    facet=facet,
                    ok=bool(res.get("ok")),
                    elapsed_ms=float(res.get("elapsed_ms") or 0) or None,
                    error=str(res.get("error") or "") if not res.get("ok") else "",
                    detail=str(ctx.get("isin") or ctx.get("sector_name") or "")[:80],
                )
            if not res.get("ok"):
                spec = get_tool(name)
                if spec and spec.fallbacks:
                    for fb in spec.fallbacks:
                        fb_res = _run_tool(fb, ctx)
                        if fb_res.get("ok"):
                            res = fb_res
                            name = fb
                            break
                if not res.get("ok"):
                    _update_ledger(
                        ledger_map,
                        facet,
                        "partial" if round_i < rounds - 1 else "unavailable",
                        str(res.get("error") or "tool_failed"),
                        name,
                    )
                    continue

            data = res.get("data") if isinstance(res.get("data"), dict) else res
            evidence.items.append(
                EvidenceItem(facet=facet, tool=name, entity_key=str(ctx.get("isin") or ctx.get("subject") or ""), data=data if isinstance(data, dict) else {"raw": data})
            )
            evidence.articles.extend(_collect_articles(res))
            _update_ledger(ledger_map, facet, "satisfied", tool=name)

            if facet == "exposure_link" and isinstance(data, dict):
                shortlisted_funds = _extract_funds_from_sector_result(data)

        # Fan-out facets may need second pass after exposure_link
        if "exposure_link" in [f for f, e in ledger_map.items() if e.status == "satisfied"] and shortlisted_funds:
            for facet in ("fund_composition", "return_series"):
                if facet not in gctx.brief.evidence_needs:
                    continue
                if ledger_map.get(facet) and ledger_map[facet].status == "satisfied":
                    continue
                got = 0
                for fund in shortlisted_funds[: gctx.fan_out_cap]:
                    spec_name = "fund_composition" if facet == "fund_composition" else "fund_return_series"
                    fctx = {**ctx, "isin": fund.get("isin"), "fund_name": fund.get("fund_name")}
                    res = _run_tool(spec_name, fctx)
                    if res.get("ok"):
                        got += 1
                        data = res.get("data") if isinstance(res.get("data"), dict) else res
                        evidence.items.append(
                            EvidenceItem(
                                facet=facet,
                                tool=spec_name,
                                entity_key=str(fund.get("isin") or fund.get("fund_name")),
                                data=data if isinstance(data, dict) else {},
                            )
                        )
                need = min(3, len(shortlisted_funds)) if shortlisted_funds else 1
                if got >= need:
                    _update_ledger(ledger_map, facet, "satisfied", tool=spec_name)
                elif got > 0:
                    _update_ledger(ledger_map, facet, "partial", f"fan_out_partial:{got}/{need}", tool=spec_name)
                elif round_i == rounds - 1:
                    _update_ledger(ledger_map, facet, "unavailable", "fan_out_empty")

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
