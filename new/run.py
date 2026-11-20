"""Orchestrate equity-fund week insights for a CRN."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from new.compose_llm import compose_fund_narrative
from new.fund_context import build_fund_facts, nav_1w_for_isin
from new.stock_explain import attach_stock_whys
from new.portfolio_equity import FundRow, load_equity_holdings


def _prefetch_nav(funds: list[FundRow]) -> dict[str, float | None]:
    nav: dict[str, float | None] = {}
    with ThreadPoolExecutor(max_workers=min(6, max(1, len(funds)))) as pool:
        futs = {pool.submit(nav_1w_for_isin, f.isin): f.isin for f in funds}
        for fut in as_completed(futs):
            isin = futs[fut]
            try:
                nav[isin] = fut.result()
            except Exception:
                nav[isin] = None
    return nav


def _process_one(
    fund: FundRow,
    all_funds: list[FundRow],
    nav_by_isin: dict[str, float | None],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    facts = build_fund_facts(
        fund,
        all_funds,
        nav_by_isin,
        fetch_news=not dry_run,
        dry_run=dry_run,
    )
    payload = facts.to_dict()
    if not dry_run and payload.get("stock_news"):
        before = len(payload["stock_news"])
        payload["stock_news"] = attach_stock_whys(payload["stock_news"], dry_run=dry_run)
        dropped = before - len(payload["stock_news"])
        payload.setdefault("limits", list(payload.get("limits") or []))
        if dropped:
            payload["limits"].append(f"stocks_omitted_no_news:{dropped}")
    narrative = compose_fund_narrative(payload, dry_run=dry_run)
    return {
        "facts": facts.to_dict(),
        "narrative": narrative,
        "status": "ok",
    }


def run_equity_fund_week(
    crn: str,
    *,
    top_n: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    try:
        funds, meta = load_equity_holdings(crn, top_n=top_n)
    except ValueError as exc:
        code = str(exc)
        if code == "bad_crn":
            return {"status": "bad_crn", "message": "Enter a valid CRN.", "funds": []}
        if code == "portfolio_not_configured":
            return {
                "status": "failed",
                "message": "Portfolio auth not configured (RUPEESTOP_AUTH_TOKEN or fixture).",
                "funds": [],
            }
        return {"status": "failed", "message": code.replace("upstream:", ""), "funds": []}

    if not funds:
        return {
            "status": "ok",
            "message": "No equity funds in this portfolio.",
            "meta": meta,
            "funds": [],
        }

    nav_by_isin = _prefetch_nav(funds)
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(3, len(funds))) as pool:
        futs = [
            pool.submit(_process_one, fund, funds, nav_by_isin, dry_run=dry_run) for fund in funds
        ]
        for fut in as_completed(futs):
            try:
                results.append(fut.result())
            except Exception as exc:
                results.append({"status": "failed", "error": str(exc)[:200]})

    results.sort(key=lambda r: -(r.get("facts") or {}).get("portfolio_pct", 0))
    return {
        "status": "ok",
        "meta": meta,
        "dry_run": dry_run,
        "fund_count": len(results),
        "funds": results,
    }