"""Read-only insights API. The page only receives ok cards and safe statuses."""

from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any, Callable

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ai_insight.common.config import load_config
from ai_insight.common.schemas import Envelope, InsightBundle
from ai_insight.common.store import list_dates, load_best, load_best_detail, load_bundle
from ai_insight.holding_insights.config import MAX_STOCK_LIMIT
from ai_insight.holding_insights.job import HoldingJobBusy, get_holding_job_manager
from ai_insight.jobs import MODULES, JobBusy, JobManager

_SINGLE = ("market_driver_digest", "fii_dii_flow_narrative", "sector_leaderboard")
_BUNDLES = ("sector_index_insights", "additional_insights")
_manager: JobManager | None = None


class GenerateRequest(BaseModel):
    date: str | None = None
    insights: list[str] | None = None


class HoldingInsightsRunRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=99)


class PortfolioComposeRequest(BaseModel):
    crn: str = Field(min_length=3, max_length=64)
    date: str | None = None


def create_router(check_token: Callable[..., None]) -> APIRouter:
    router = APIRouter()

    @router.get("/api/insights/daily")
    def daily(
        date: str | None = None,
        authorization: str | None = Header(default=None),
        x_app_token: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        trading_date = date or _latest_date()
        if not trading_date:
            return {"date": None, "prev_date": None, "next_date": None, "generated_at": None, "insights": {}, "sector_performance": [], "additional": []}
        dates = _all_dates()
        preview = _preview_mode(x_admin_token)
        admin = _preview_mode(x_admin_token)
        insights = {name: _project_single(name, trading_date, preview=preview, admin=admin) for name in _SINGLE}
        sector_performance = _project_bundle("sector_index_insights", trading_date, preview=preview, admin=admin)
        additional = _project_bundle("additional_insights", trading_date, preview=preview, admin=admin) if load_config().show_additional else []
        body = {
            "date": trading_date,
            "prev_date": _neighbour(dates, trading_date, -1),
            "next_date": _neighbour(dates, trading_date, 1),
            "generated_at": _generated_at(insights),
            "insights": insights,
            "sector_performance": sector_performance,
            "additional": additional,
            "token_totals": _token_totals(insights, sector_performance, additional),
        }
        return JSONResponse(body, headers={"Cache-Control": "no-store"})

    @router.get("/api/insights/runs/{insight_id}/{trading_date}/{run_id}")
    def run_log(
        insight_id: str,
        trading_date: str,
        run_id: str,
        authorization: str | None = Header(default=None),
        x_app_token: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        _preview_mode(x_admin_token)  # admin or preview token required for paths
        folder = _run_dir(insight_id, trading_date, run_id)
        usage = _read_json(folder / "usage.json") or {}
        manifest = _read_json(folder / "manifest.json") or {}
        validation = _read_json(folder / "validation.json") or {}
        evidence = _read_json(folder / "evidence_meta.json")
        if evidence is None:
            evidence = _read_json(folder / "evidence_articles.json")
        admin = _preview_mode(x_admin_token)
        payload = {
            "manifest": manifest,
            "usage": usage,
            "validation": validation,
            "evidence": evidence,
            "decision_trace": (folder / "decision_trace.md").read_text(encoding="utf-8") if (folder / "decision_trace.md").is_file() else "",
        }
        if admin:
            payload["run_dir"] = str(folder)
        return payload

    @router.get("/api/insights/dates")
    def dates(authorization: str | None = Header(default=None), x_app_token: str | None = Header(default=None), x_admin_token: str | None = Header(default=None)) -> dict[str, list[str]]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        return {"dates": _all_dates()}

    @router.get("/api/insights/health")
    def health(authorization: str | None = Header(default=None), x_app_token: str | None = Header(default=None), x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        report = {}
        for name in (*_SINGLE, *_BUNDLES):
            days = list_dates(name, root=load_config().data_dir)
            envelope = load_best(name, days[-1], root=load_config().data_dir) if days else None
            report[name] = {"last_date": days[-1] if days else None, "last_status": envelope.status if envelope else None}
        return {"insights": report}

    @router.post("/api/insights/generate", status_code=202)
    def generate(body: GenerateRequest | None = None, authorization: str | None = Header(default=None), x_app_token: str | None = Header(default=None), x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        if os.environ.get("INSIGHTS_ALLOW_GENERATE", "true").lower() in {"0", "false", "no"}:
            raise HTTPException(status_code=403, detail="Generation is turned off")
        requested = body or GenerateRequest()
        if requested.insights and any(name not in MODULES for name in requested.insights):
            raise HTTPException(status_code=400, detail="Unknown insight")
        try:
            trading = date.fromisoformat(requested.date) if requested.date else None
            job = _jobs().start(trading, requested.insights)
        except JobBusy as exc:
            raise HTTPException(status_code=409, detail={"job_id": exc.job_id}) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Bad date") from exc
        return {"job_id": job.job_id, "status": job.status, "started_at": job.started_at}

    @router.get("/api/insights/jobs/latest")
    def job_latest(authorization: str | None = Header(default=None), x_app_token: str | None = Header(default=None), x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        job = _jobs().latest()
        if job is None:
            return {"job_id": None, "status": "idle"}
        return _job_payload(job)

    @router.get("/api/insights/jobs/{job_id}")
    def job_status(job_id: str, authorization: str | None = Header(default=None), x_app_token: str | None = Header(default=None), x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        try:
            job = _jobs().get(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown job") from exc
        return _job_payload(job)

    @router.get("/api/insights/{insight_id}/latest")
    def latest(insight_id: str, authorization: str | None = Header(default=None), x_app_token: str | None = Header(default=None), x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        if insight_id not in (*_SINGLE, *_BUNDLES):
            raise HTTPException(status_code=404, detail="Unknown insight")
        days = list_dates(insight_id, root=load_config().data_dir)
        if not days:
            raise HTTPException(status_code=404, detail="No insight for that id")
        if insight_id in _BUNDLES:
            return {"items": _project_bundle(insight_id, days[-1])}
        projected = _project_single(insight_id, days[-1])
        if projected is None:
            raise HTTPException(status_code=404, detail="No insight for that id")
        return projected

    @router.post("/api/holding-insights/run", status_code=202)
    def holding_insights_run(
        body: HoldingInsightsRunRequest | None = None,
        authorization: str | None = Header(default=None),
        x_app_token: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        req = body or HoldingInsightsRunRequest()
        if req.limit > MAX_STOCK_LIMIT:
            raise HTTPException(status_code=400, detail=f"limit must be <= {MAX_STOCK_LIMIT}")
        try:
            job = get_holding_job_manager().start(req.limit)
        except HoldingJobBusy as exc:
            raise HTTPException(status_code=409, detail={"job_id": exc.job_id}) from exc
        return {"job_id": job.job_id, "status": job.status, "started_at": job.started_at, "limit": req.limit}

    @router.get("/api/holding-insights/jobs/latest")
    def holding_insights_job_latest(
        authorization: str | None = Header(default=None),
        x_app_token: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        job = get_holding_job_manager().latest()
        if job is None:
            return {"job_id": None, "status": "idle"}
        return _holding_job_payload(job)

    @router.get("/api/holding-insights/jobs/{job_id}")
    def holding_insights_job_status(
        job_id: str,
        authorization: str | None = Header(default=None),
        x_app_token: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        try:
            job = get_holding_job_manager().get(job_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Unknown job") from exc
        return _holding_job_payload(job)

    @router.get("/api/holding-insights/logs/{job_id}/{stock_id}")
    def holding_insights_stock_log_json(
        job_id: str,
        stock_id: str,
        authorization: str | None = Header(default=None),
        x_app_token: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        from ai_insight.holding_insights.stock_log import load_stock_log

        doc = load_stock_log(job_id, stock_id.upper() if stock_id.islower() else stock_id)
        if doc is None:
            doc = load_stock_log(job_id, stock_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Log not found")
        return doc

    @router.get("/api/portfolio-insights/ready")
    def portfolio_insights_ready(
        date: str | None = None,
        authorization: str | None = Header(default=None),
        x_app_token: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        from ai_insight.portfolio_insights.catalog import readiness, resolve_trading_date

        trading_date = resolve_trading_date(date)
        if not trading_date:
            return {"trading_date": None, "ready": False, "missing": ["trading_date"], "details": {}}
        result = readiness(trading_date)
        return {
            "trading_date": result.trading_date,
            "ready": result.ready,
            "missing": result.missing,
            "details": result.details,
        }

    @router.post("/api/portfolio-insights/compose")
    def portfolio_insights_compose(
        body: PortfolioComposeRequest,
        authorization: str | None = Header(default=None),
        x_app_token: str | None = Header(default=None),
        x_admin_token: str | None = Header(default=None),
    ) -> dict[str, Any]:
        _guard(check_token, authorization, x_app_token, x_admin_token)
        from ai_insight.portfolio_insights.compose import compose_portfolio_insights

        return JSONResponse(
            compose_portfolio_insights(body.crn, body.date),
            headers={"Cache-Control": "no-store"},
        )

    return router


def _holding_job_payload(job) -> dict[str, Any]:
    result = job.result or {}
    path = get_holding_job_manager().root / f"{job.job_id}.json"
    error = None
    if path.is_file():
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
            error = meta.get("error")
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "job_id": job.job_id,
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "limit": job.limit,
        "progress": job.progress,
        "error": error,
        "insights": result.get("insights") or [],
        "insufficient": result.get("insufficient") or [],
        "counts": result.get("counts") or {},
        "generated_on": result.get("generated_on"),
        "usage_total": result.get("usage_total") or {},
    }


def public_projection(
    envelope: Envelope,
    *,
    preview: bool = False,
    admin: bool = False,
    stale: bool = False,
    stale_reason: str = "",
) -> dict[str, Any]:
    if not _visible_on_page(envelope, preview=preview):
        return {"insight_id": envelope.insight_id, "trading_date": envelope.trading_date, "status": envelope.status, "skip_reason": _safe_reason(envelope.skip_reason)}
    usage = {
        "calls": len(envelope.meta.llm_calls),
        "input_tokens": envelope.meta.usage.input_tokens,
        "output_tokens": envelope.meta.usage.output_tokens,
        "calls_detail": list(envelope.meta.llm_calls),
    }
    run_id = envelope.meta.run_id or ""
    out = {
        "insight_id": envelope.insight_id,
        "trading_date": envelope.trading_date,
        "as_of_ist": envelope.as_of_ist,
        "status": envelope.status,
        "prominence": envelope.prominence,
        "headline": envelope.headline,
        "body": envelope.body,
        "chips": [chip.model_dump() for chip in envelope.chips],
        "viz": envelope.viz.model_dump(),
        "sources": [source.model_dump() for source in envelope.sources],
        "run_mode": envelope.meta.run_mode,
        "usage": usage,
        "run_id": run_id,
        "log_url": f"/insights/log/{envelope.insight_id}/{envelope.trading_date}/{run_id}" if run_id else "",
        "stale": stale,
        "stale_reason": stale_reason if stale else "",
    }
    if admin and run_id:
        out["log_path"] = str(load_config().log_dir / envelope.trading_date / envelope.insight_id / run_id)
    return out


def _visible_on_page(envelope: Envelope, *, preview: bool = False, bundle_live: bool = False) -> bool:
    if envelope.status == "ok":
        return True
    if envelope.status == "degraded":
        if envelope.meta.run_mode == "live" or bundle_live:
            return True
        return preview
    return False


def _bundle_is_live(bundle: InsightBundle) -> bool:
    meta = bundle.meta
    if isinstance(meta, dict):
        return meta.get("run_mode") == "live"
    return False


def _project_single(name: str, trading_date: str, *, preview: bool = False, admin: bool = False) -> dict[str, Any] | None:
    detail = load_best_detail(name, trading_date, root=load_config().data_dir)
    if detail.envelope is None:
        return None
    return public_projection(
        detail.envelope,
        preview=preview,
        admin=admin,
        stale=detail.stale,
        stale_reason=detail.stale_reason,
    )


def _project_bundle(name: str, trading_date: str, *, preview: bool = False, admin: bool = False) -> list[dict[str, Any]]:
    bundle = load_bundle(name, trading_date, root=load_config().data_dir)
    live = load_bundle(name, trading_date, root=load_config().data_dir, live=True)
    chosen = _newer_bundle(bundle, live)
    if chosen is None:
        return []
    bundle_live = _bundle_is_live(chosen)
    return [
        public_projection(item, preview=preview, admin=admin)
        for item in chosen.items
        if _visible_on_page(item, preview=preview, bundle_live=bundle_live)
    ]


def _newer_bundle(left: InsightBundle | None, right: InsightBundle | None) -> InsightBundle | None:
    if left is None:
        return right
    if right is None:
        return left
    return right if right.as_of_ist >= left.as_of_ist else left


def _job_payload(job) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "status": job.status,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "trading_date": job.trading_date,
        "insights": job.insight_ids,
        "progress": job.progress,
        "results": job.results,
    }


def _preview_mode(x_admin_token: str | None) -> bool:
    expected = os.environ.get("INSIGHTS_ADMIN_TOKEN", "").strip()
    if expected and expected == (x_admin_token or "").strip():
        return True
    return os.environ.get("INSIGHTS_PREVIEW_DEGRADED", "false").lower() in {"1", "true", "yes", "on"}


def _guard(check_token, authorization, x_app_token, x_admin_token) -> None:
    check_token(authorization, x_app_token)
    if os.environ.get("INSIGHTS_PUBLIC", "true").lower() in {"0", "false", "no"}:
        expected = os.environ.get("INSIGHTS_ADMIN_TOKEN", "")
        if not expected or (x_admin_token or "") != expected:
            raise HTTPException(status_code=401, detail="Not available")


def _all_dates() -> list[str]:
    found: set[str] = set()
    root = load_config().data_dir
    for name in (*_SINGLE, *_BUNDLES):
        found.update(list_dates(name, root=root))
    return sorted(found)


def _latest_date() -> str | None:
    dates = _all_dates()
    return dates[-1] if dates else None


def _neighbour(dates: list[str], current: str, step: int) -> str | None:
    if current not in dates:
        return None
    index = dates.index(current) + step
    if index < 0 or index >= len(dates):
        return None
    return dates[index]


def _generated_at(insights: dict[str, Any]) -> str | None:
    stamps = [item.get("as_of_ist") for item in insights.values() if isinstance(item, dict) and item.get("as_of_ist")]
    return max(stamps) if stamps else None


def _token_totals(
    insights: dict[str, Any],
    sector_performance: list[dict[str, Any]],
    additional: list[dict[str, Any]],
) -> dict[str, Any]:
    sections: dict[str, dict[str, int]] = {}
    total_in = 0
    total_out = 0

    def add_section(key: str, usage: dict[str, Any] | None) -> None:
        nonlocal total_in, total_out
        if not usage:
            return
        inch = int(usage.get("input_tokens") or 0)
        outch = int(usage.get("output_tokens") or 0)
        if inch or outch or usage.get("calls"):
            sections[key] = {
                "input_tokens": inch,
                "output_tokens": outch,
                "calls": int(usage.get("calls") or len(usage.get("calls_detail") or [])),
            }
            total_in += inch
            total_out += outch

    for key, item in insights.items():
        if isinstance(item, dict):
            add_section(key, item.get("usage"))
    sector_in = 0
    sector_out = 0
    sector_calls = 0
    for item in sector_performance:
        usage = item.get("usage") if isinstance(item, dict) else None
        if not usage:
            continue
        sector_in += int(usage.get("input_tokens") or 0)
        sector_out += int(usage.get("output_tokens") or 0)
        sector_calls += int(usage.get("calls") or len(usage.get("calls_detail") or []))
    if sector_in or sector_out or sector_calls:
        sections["sector_index_insights"] = {"input_tokens": sector_in, "output_tokens": sector_out, "calls": sector_calls}
        total_in += sector_in
        total_out += sector_out
    extra_in = 0
    extra_out = 0
    extra_calls = 0
    for item in additional:
        usage = item.get("usage") if isinstance(item, dict) else None
        if not usage:
            continue
        extra_in += int(usage.get("input_tokens") or 0)
        extra_out += int(usage.get("output_tokens") or 0)
        extra_calls += int(usage.get("calls") or len(usage.get("calls_detail") or []))
    if extra_in or extra_out or extra_calls:
        sections["additional_insights"] = {"input_tokens": extra_in, "output_tokens": extra_out, "calls": extra_calls}
        total_in += extra_in
        total_out += extra_out
    return {"total_input_tokens": total_in, "total_output_tokens": total_out, "sections": sections}


def _safe_reason(reason: str | None) -> str | None:
    if not reason:
        return None
    if reason in {"not_a_trading_day", "market_closed"}:
        return "market_closed"
    if "not_published" in reason or reason.endswith("stale") or reason.endswith("unavailable"):
        return "not_available"
    return "not_available"


_ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RUN = re.compile(r"^[a-f0-9]{6}$")


def _run_dir(insight_id: str, trading_date: str, run_id: str) -> Path:
    if not _ID.match(insight_id) or not _DATE.match(trading_date) or not _RUN.match(run_id):
        raise HTTPException(status_code=400, detail="Bad run path")
    root = load_config().log_dir.resolve()
    folder = (root / trading_date / insight_id / run_id).resolve()
    if not str(folder).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Bad run path")
    if not folder.is_dir():
        raise HTTPException(status_code=404, detail="Run not found")
    return folder


def _read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _jobs() -> JobManager:
    global _manager
    if _manager is None:
        _manager = JobManager()
    return _manager


_ = Field
