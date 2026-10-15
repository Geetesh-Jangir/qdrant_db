"""Run the plan in two layers: data tools, then news for the names those tools returned.

check() is code only. Thin news is retried once with a wider window. The composer
receives whatever came back plus a coverage note for the gaps.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from news_rag.insight.news_fanout import NewsTarget, grouped_news, search_targets
from news_rag.insight.plan import Plan
from news_rag.insight.registry import ensure_registry, get_tool


def _base_context(plan: Plan, question: str, funds: list[str], sector_keys: list[str]) -> dict[str, Any]:
    return {
        "question": question,
        "fund_names": list(funds),
        "sector_name": sector_keys[0] if sector_keys else (plan.sectors[0] if plan.sectors else ""),
        "sector_keys": list(sector_keys),
        "stock_name": plan.stocks[0] if plan.stocks else "",
        "drivers": [d["id"] for d in plan.drivers],
        "driver_direction": next((d.get("direction") or "" for d in plan.drivers if d.get("direction")), ""),
        "window_days": plan.window_days,
        "return_window": "1M" if plan.window_days >= 21 else "1W",
        "direction": plan.direction if plan.direction in ("positive", "negative") else "any",
        "top_n": 8,
    }


def run_layer1(
    plan: Plan,
    question: str,
    funds: list[str],
    sector_keys: list[str],
    *,
    query_log: Any = None,
) -> list[dict[str, Any]]:
    """Every planned data tool, in parallel. Per-fund tools run once per resolved fund."""
    ensure_registry()
    base = _base_context(plan, question, funds, sector_keys)
    jobs: list[tuple[str, dict[str, Any], str]] = []
    for call in plan.layer1:
        spec = get_tool(call["tool"])
        if spec is None or not spec.run:
            continue
        args = dict(call.get("args") or {})
        per_fund = spec.fan_out_over == "fund" or spec.name in {
            "fund_snapshot", "fund_portfolio", "fund_attribution", "fund_return_series",
        }
        if per_fund and funds:
            for name in funds:
                ctx = {**base, **args, "fund_name": name, "fund_names": [name]}
                jobs.append((spec.name, ctx, name))
        else:
            jobs.append((spec.name, {**base, **args}, ""))

    def _one(name: str, ctx: dict[str, Any], fund: str) -> dict[str, Any]:
        spec = get_tool(name)
        started = time.perf_counter()
        try:
            out = spec.run(ctx) if spec and spec.run else {"ok": False, "error": "no_runner"}
        except Exception as exc:  # noqa: BLE001
            out = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        if not isinstance(out, dict):
            out = {"ok": False, "error": "non_dict"}
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        data = out.get("data") if isinstance(out.get("data"), dict) else {}
        row = {
            "tool": name,
            "fund": fund,
            "ok": bool(out.get("ok")),
            "error": "" if out.get("ok") else str(out.get("error") or "failed"),
            "elapsed_ms": elapsed,
            "data": data,
            "args": {k: ctx[k] for k in ("top_n_holdings", "top_n_sectors", "find", "windows", "window_days", "index", "series") if k in ctx},
        }
        if query_log is not None:
            query_log.log_tool_invocation(
                tool=name,
                facet="layer1",
                ok=row["ok"],
                elapsed_ms=elapsed,
                error=row["error"],
                detail=(fund or str(row["args"]))[:80],
            )
        return row

    if not jobs:
        return []
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(8, len(jobs))) as pool:
        futures = [pool.submit(_one, name, ctx, fund) for name, ctx, fund in jobs]
        for fut in as_completed(futures):
            results.append(fut.result())
    return results


def _retry_failed(plan: Plan, results: list[dict[str, Any]], question: str, funds: list[str], sector_keys: list[str]) -> list[dict[str, Any]]:
    """One fallback attempt for a required tool that failed and declares a fallback."""
    failed = {row["tool"] for row in results if not row["ok"]}
    required = {call["tool"] for call in plan.layer1 if call.get("required", True)}
    extra: list[dict[str, Any]] = []
    for name in failed & required:
        spec = get_tool(name)
        for fb in spec.fallbacks if spec else []:
            if fb in {row["tool"] for row in results}:
                continue
            stand_in = Plan(layer1=[{"tool": fb, "args": {}, "required": True, "why": "fallback"}], window_days=plan.window_days, direction=plan.direction, stocks=plan.stocks, sectors=plan.sectors, drivers=plan.drivers)
            extra.extend(run_layer1(stand_in, question, funds, sector_keys))
            break
    return results + extra


def _names_from(results: list[dict[str, Any]], key: str, limit: int) -> list[str]:
    names: list[str] = []
    if key == "holdings":
        for row in results:
            data = row.get("data") or {}
            for item in list(data.get("detractors") or []) + list(data.get("contributors") or []):
                name = str(item.get("name") or "").strip() if isinstance(item, dict) else ""
                if name and name not in names:
                    names.append(name)
                if len(names) >= limit:
                    return names
        if names:
            return names
    for row in results:
        if not row.get("ok"):
            continue
        data = row.get("data") or {}
        rows = data.get(key) or []
        for item in rows:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("sector") or "").strip()
            else:
                name = str(item).strip()
            if name and name not in names:
                names.append(name)
            if len(names) >= limit:
                return names
    return names


def _macro_topics(results: list[dict[str, Any]], plan: Plan) -> list[str]:
    from news_rag.fund_portfolio_news import _macro_queries_for_sectors

    sectors = [{"sector": name} for name in _names_from(results, "sectors", 6)]
    topics = [label for _query, label in _macro_queries_for_sectors(sectors)]
    for driver in plan.drivers:
        label = driver["id"].replace("_", " ")
        if label not in topics:
            topics.append(label)
    return topics[:4] or ["India macro markets crude rupee RBI"]


def expand_targets(plan: Plan, results: list[dict[str, Any]]) -> list[NewsTarget]:
    """Turn layer2_news scopes into one search target per entity."""
    targets: list[NewsTarget] = []
    for scope in plan.layer2_news:
        kind = scope["scope"]
        limit = int(scope["top_n"])
        window = int(scope["window_days"])
        direction = None if scope["direction"] == "any" else scope["direction"]
        per = int(scope["articles_per_entity"])
        chars = int(scope["chars_per_article"])
        required = bool(scope["required"])
        if scope["source"] == "list" and scope["topics"]:
            entities = [(topic, f"{topic} India market news") for topic in scope["topics"][:limit]]
        elif kind == "holdings":
            entities = [(name, f"{name} India stock news earnings results") for name in _names_from(results, "holdings", limit)]
        elif kind == "sectors":
            entities = [(name, f"{name} India sector news") for name in _names_from(results, "sectors", limit)]
        elif kind == "macro":
            entities = [(topic, f"{topic} India macro news") for topic in _macro_topics(results, plan)[:limit]]
        elif kind == "stock":
            entities = [(name, f"{name} India share price news") for name in (plan.stocks or scope["topics"])[:limit]]
        elif kind == "sector":
            names = scope["topics"] or plan.sectors or _names_from(results, "sectors", limit)
            entities = [(name, f"{name} India sector outlook news") for name in names[:limit]]
        elif kind == "market":
            from news_rag.insight.market_news import market_scope_entities

            entities = market_scope_entities(
                source_kind=str(scope["source"]),
                topics=list(scope.get("topics") or []),
                top_n=limit,
            )
        else:
            entities = []
        for entity, query in entities:
            targets.append(
                NewsTarget(
                    scope=kind, entity=entity, query=query, window_days=window,
                    direction=direction, limit=per, chars=chars, required=required,
                )
            )
    return targets


def widen_thin(targets: list[NewsTarget]) -> list[NewsTarget]:
    """Targets that were required and came back empty, searched once more up to 180 days."""
    retry: list[NewsTarget] = []
    for target in targets:
        if target.required and not target.articles and target.window_days < 180:
            wider = NewsTarget(
                scope=target.scope,
                entity=target.entity,
                query=target.query,
                window_days=min(180, max(target.window_days * 3, target.window_days + 30)),
                direction=target.direction,
                limit=target.limit,
                chars=target.chars,
                required=target.required,
            )
            retry.append(wider)
    if retry:
        search_targets(retry)
    by_key = {(t.scope, t.entity): t for t in retry}
    widened: list[str] = []
    for target in targets:
        fresh = by_key.get((target.scope, target.entity))
        if fresh and fresh.articles:
            target.articles = fresh.articles
            target.window_days = fresh.window_days
            widened.append(target.entity)
    return widened


def coverage_report(plan: Plan, results: list[dict[str, Any]], targets: list[NewsTarget], widened: list[str]) -> dict[str, Any]:
    present = sorted({row["tool"] for row in results if row.get("ok")})
    missing_tools = sorted({call["tool"] for call in plan.layer1 if call.get("required", True)} - set(present))
    thin = [f"{t.scope}: {t.entity}" for t in targets if not t.articles]
    return {
        "present_tools": present,
        "missing_tools": missing_tools,
        "news_without_articles": thin,
        "widened": widened,
        "not_supported": list(plan.asks_not_supported),
    }


def execute_layers(
    plan: Plan,
    question: str,
    funds: list[str],
    sector_keys: list[str],
    *,
    query_log: Any = None,
) -> dict[str, Any]:
    """layer1, expand, layer2, one widen, coverage. Returns the pack the composer reads."""
    results = run_layer1(plan, question, funds, sector_keys, query_log=query_log)
    results = _retry_failed(plan, results, question, funds, sector_keys)
    targets = expand_targets(plan, results)
    search_targets(targets)
    widened = widen_thin(targets)
    report = coverage_report(plan, results, targets, widened)
    return {"results": results, "news": grouped_news(targets), "coverage": report, "targets": targets}
