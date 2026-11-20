"""Orchestrate equity-fund week insights for a CRN or single ISIN."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from new.compose_llm import compose_fund_narrative
from new.fund_by_isin import load_equity_fund_by_isin
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
    omit_portfolio_pct: bool = False,
) -> dict[str, Any]:
    facts = build_fund_facts(
        fund,
        all_funds,
        nav_by_isin,
        fetch_news=not dry_run,
        dry_run=dry_run,
    )
    payload = facts.to_dict()
    if omit_portfolio_pct:
        payload.pop("portfolio_pct", None)
    if not dry_run and payload.get("stock_news"):
        before = len(payload["stock_news"])
        fund_ctx = {
            "fund_name": payload.get("scheme_name"),
            "fund_nav_1w_pct": payload.get("nav_1w_pct"),
        }
        for block in payload["stock_news"]:
            block.update(fund_ctx)
        payload["stock_news"] = attach_stock_whys(payload["stock_news"], dry_run=dry_run)
        dropped = before - len(payload["stock_news"])
        payload.setdefault("limits", list(payload.get("limits") or []))
        if dropped:
            payload["limits"].append(f"stocks_omitted_no_news:{dropped}")
    narrative = compose_fund_narrative(payload, dry_run=dry_run, omit_portfolio_pct=omit_portfolio_pct)
    return {
        "facts": payload,
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
        "meta": {**meta, "mode": "crn"},
        "dry_run": dry_run,
        "fund_count": len(results),
        "funds": results,
    }


def run_equity_fund_week_by_isin(
    isin: str,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    try:
        fund, meta = load_equity_fund_by_isin(isin)
    except ValueError as exc:
        code = str(exc)
        if code == "bad_isin":
            return {"status": "bad_isin", "message": "Enter a valid fund ISIN (INF…).", "funds": []}
        if code == "fund_not_found":
            return {"status": "fund_not_found", "message": "No fund found for this ISIN.", "funds": []}
        if code.startswith("not_equity:"):
            stype = code.split(":", 1)[-1]
            return {
                "status": "not_equity",
                "message": f"Only equity schemes are supported (this fund is {stype}).",
                "funds": [],
            }
        return {"status": "failed", "message": code, "funds": []}

    nav_by_isin = _prefetch_nav([fund])
    try:
        result = _process_one(
            fund,
            [fund],
            nav_by_isin,
            dry_run=dry_run,
            omit_portfolio_pct=True,
        )
    except Exception as exc:
        return {"status": "failed", "message": str(exc)[:200], "funds": []}

    return {
        "status": "ok",
        "meta": meta,
        "dry_run": dry_run,
        "fund_count": 1,
        "funds": [result],
    }