"""Run one insight: trading day, validation, save, one summary line."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable

from ai_insight.common.config import CommonConfig, load_config
from ai_insight.common.run_log import RunLog
from ai_insight.common.schemas import Envelope, InsightBundle, Meta, UsageMeta
from ai_insight.common.store import save
from ai_insight.common.time_ist import fmt_ist, ist_now, session_window, to_ist
from ai_insight.common.trading_calendar import is_trading_day
from ai_insight.common.validate import validate_insight

BuildFn = Callable[["RunContext"], Envelope]
BundleBuildFn = Callable[["RunContext"], InsightBundle]


class DryRunHalt(BaseException):
    """Stops a dry run before the model is called. Not an Exception, so insight handlers leave it alone."""


@dataclass
class RunContext:
    insight_id: str
    trading_date: date
    window: tuple[str, str]
    dry_run: bool
    config: CommonConfig
    log: RunLog
    llm: Callable[..., Any]
    prompts: list[dict[str, Any]] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    usages: list[Any] = field(default_factory=list)
    artifacts: Any = None
    live: bool = False
    market_phase: str = ""
    llm_label: str = ""

    def scope(self, label: str) -> "RunContext":
        self.llm_label = label
        return self

    def emit_facts(self, facts: dict[str, Any]) -> None:
        self.facts = facts
        self.log.line("FACTS", _short(facts))

    def add_usage(self, usage: Any) -> None:
        self.usages.append(usage)


@dataclass
class RunOutcome:
    status: str
    exit_code: int
    duration_sec: float
    tokens: int
    source_count: int
    log_path: str
    envelope: Envelope | None = None


def run_insight(
    insight_id: str,
    build_fn: BuildFn,
    trading_date: date,
    force: bool = False,
    dry_run: bool = False,
    *,
    verbose: bool = False,
    config: CommonConfig | None = None,
    now: datetime | None = None,
    live: bool = False,
) -> RunOutcome:
    cfg = config or load_config()
    started = time.perf_counter()
    run_id = uuid.uuid4().hex[:6]
    log = RunLog(
        insight_id=insight_id,
        trading_date=trading_date.isoformat(),
        run_id=run_id,
        log_dir=cfg.log_dir,
        verbose=verbose,
    )
    from ai_insight.common.logging import RunArtifacts

    artifacts = RunArtifacts(insight_id, trading_date.isoformat(), run_id, cfg.log_dir, cfg.log_retention_days)
    log.line("TRACE_DIR", str(artifacts.dir))
    job_id = os.environ.get("INSIGHTS_JOB_ID", "").strip()
    artifacts.write_manifest({"job_id": job_id, "live": live, "dry_run": dry_run})
    log.line(
        "RUN START",
        f"insight={insight_id} date={trading_date.isoformat()} run_id={run_id} "
        f"force={force} dry_run={dry_run} live={live} job_id={job_id or '-'}",
    )
    window = session_window(trading_date, now=now if live or now else None, config=cfg)
    phase = _market_phase(now)
    log.line("WINDOW", f"{fmt_ist(_parse(window[0]))} -> {fmt_ist(_parse(window[1]))}  UTC {window[0]} -> {window[1]}")
    warning = _freshness_warning(window, cfg, artifacts)
    ingest_warning = os.environ.get("INSIGHTS_INGEST_WARNING", "").strip()
    if ingest_warning:
        warning = (warning + "; " if warning else "") + ingest_warning
    artifacts.write_json("window.json", {"window_utc": list(window), "live": live, "market_phase": phase, "freshness_warning": warning})
    trading = is_trading_day(trading_date, holidays_path=cfg.holidays_path)
    log.step(1, 3, "CALENDAR", f"trading_day={trading}")
    saved = ""
    envelope: Envelope | None = None
    status = "failed"
    try:
        if not trading:
            status = "skipped"
            envelope = _shell(insight_id, trading_date, "skipped", skip_reason="not_a_trading_day", window=window, run_id=run_id, config=cfg, now=now)
            log.warning(f"{trading_date.isoformat()} is not an NSE trading day, so nothing was written for investors")
            if not dry_run:
                saved = str(save(envelope, root=cfg.data_dir, live=live))
            return _finish(log, status, 0, started, envelope, saved, artifacts)
        ctx = RunContext(
            insight_id=insight_id,
            trading_date=trading_date,
            window=window,
            dry_run=dry_run,
            config=cfg,
            log=log,
            llm=lambda *args, **kwargs: None,
            artifacts=artifacts,
            live=live,
            market_phase=phase,
        )
        ctx.llm = _bound_llm(ctx)
        try:
            envelope = build_fn(ctx)
            status = envelope.status
        except DryRunHalt:
            _print_dry_run(ctx)
            log.prompt(_prompt_text(ctx))
            log.warning("dry run: facts and prompts printed, model not called, nothing saved")
            return _finish(log, "skipped", 0, started, None, "", artifacts)
        except Exception as exc:
            envelope = _failed(insight_id, trading_date, exc, window, run_id, cfg, now)
            status = "failed"
            artifacts.error(f"{type(exc).__name__}: {exc}", step="build", inputs_summary=traceback.format_exc()[-2000:])
            if not dry_run:
                saved = str(save(envelope, root=cfg.data_dir, live=live))
            log.warning("the job raised an error and was saved as failed")
            return _finish(log, status, 1, started, envelope, saved, artifacts)
        if envelope.status == "ok":
            envelope, status = _validate_with_one_retry(ctx, build_fn, envelope, log)
        _stamp(envelope, window, run_id, cfg, ctx)
        if warning and envelope.status == "ok":
            envelope.status = "degraded"
            status = "degraded"
            envelope.meta.freshness_warning = warning
            log.warning(f"freshness: {warning}")
        elif warning:
            envelope.meta.freshness_warning = warning
        envelope.meta.run_mode = "live" if live else "scheduled"
        envelope.meta.market_phase = phase or ""
        if status in {"failed", "degraded"} or verbose or dry_run:
            log.prompt(_prompt_text(ctx))
        if dry_run:
            _print_dry_run(ctx)
            log.warning("dry run: nothing saved")
            return _finish(log, status if status != "failed" else "skipped", 0, started, envelope, "", artifacts)
        saved = str(save(envelope, root=cfg.data_dir, live=live))
        code = 1 if status == "failed" else 0
        return _finish(log, status, code, started, envelope, saved, artifacts)
    except Exception as exc:
        log.warning(f"runner failed: {type(exc).__name__}: {exc}")
        return _finish(log, "failed", 1, started, envelope, saved, artifacts)
    finally:
        artifacts.close()


def cli_main(insight_id: str, build_fn: BuildFn, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"insight {insight_id}")
    parser.add_argument("--date", default="", help="Trading date YYYY-MM-DD. Default: today in IST.")
    parser.add_argument("--force", action="store_true", help="Kept for scripts; every run rebuilds the file.")
    parser.add_argument("--dry-run", action="store_true", help="Print facts and prompts. Do not call the model or save.")
    parser.add_argument("--verbose", action="store_true", help="Keep the full prompt next to the log.")
    parser.add_argument("--live", action="store_true", help="Window ends now. Saved beside the nightly file.")
    args = parser.parse_args(argv)
    trading_date = date.fromisoformat(args.date) if args.date else (resolve_live_date() if args.live else ist_now().date())
    outcome = run_insight(
        insight_id,
        build_fn,
        trading_date,
        force=args.force or args.live,
        dry_run=args.dry_run,
        verbose=args.verbose,
        live=args.live,
    )
    print(
        f"{outcome.status} exit={outcome.exit_code} duration={outcome.duration_sec:.1f}s "
        f"tokens={outcome.tokens} sources={outcome.source_count}"
    )
    return outcome.exit_code


def run_bundle_insight(
    insight_id: str,
    build_fn: BundleBuildFn,
    trading_date: date,
    force: bool = False,
    dry_run: bool = False,
    *,
    verbose: bool = False,
    config: CommonConfig | None = None,
    now: datetime | None = None,
    live: bool = False,
) -> RunOutcome:
    cfg = config or load_config()
    started = time.perf_counter()
    run_id = uuid.uuid4().hex[:6]
    log = RunLog(
        insight_id=insight_id,
        trading_date=trading_date.isoformat(),
        run_id=run_id,
        log_dir=cfg.log_dir,
        verbose=verbose,
    )
    from ai_insight.common.logging import RunArtifacts

    artifacts = RunArtifacts(insight_id, trading_date.isoformat(), run_id, cfg.log_dir, cfg.log_retention_days)
    log.line("TRACE_DIR", str(artifacts.dir))
    job_id = os.environ.get("INSIGHTS_JOB_ID", "").strip()
    artifacts.write_manifest({"job_id": job_id, "live": live, "dry_run": dry_run})
    log.line(
        "RUN START",
        f"insight={insight_id} date={trading_date.isoformat()} run_id={run_id} "
        f"force={force} dry_run={dry_run} live={live} job_id={job_id or '-'}",
    )
    window = session_window(trading_date, now=now if live or now else None, config=cfg)
    phase = _market_phase(now)
    log.line("WINDOW", f"{fmt_ist(_parse(window[0]))} -> {fmt_ist(_parse(window[1]))}  UTC {window[0]} -> {window[1]}")
    warning = _freshness_warning(window, cfg, artifacts)
    ingest_warning = os.environ.get("INSIGHTS_INGEST_WARNING", "").strip()
    if ingest_warning:
        warning = (warning + "; " if warning else "") + ingest_warning
    artifacts.write_json("window.json", {"window_utc": list(window), "live": live, "market_phase": phase, "freshness_warning": warning})
    trading = is_trading_day(trading_date, holidays_path=cfg.holidays_path)
    log.step(1, 3, "CALENDAR", f"trading_day={trading}")
    saved = ""
    bundle: InsightBundle | None = None
    status = "failed"
    try:
        if not trading:
            status = "skipped"
            log.warning(f"{trading_date.isoformat()} is not an NSE trading day, so nothing was written for investors")
            return _finish_bundle(log, status, 0, started, None, "", artifacts)
        ctx = RunContext(
            insight_id=insight_id,
            trading_date=trading_date,
            window=window,
            dry_run=dry_run,
            config=cfg,
            log=log,
            llm=lambda *args, **kwargs: None,
            artifacts=artifacts,
            live=live,
            market_phase=phase,
        )
        ctx.llm = _bound_llm(ctx)
        bundle = build_fn(ctx)
        status = bundle.status
        if warning:
            log.warning(f"freshness: {warning}")
        for item in bundle.items:
            _stamp(item, window, run_id, cfg, ctx)
            item.meta.run_mode = "live" if live else "scheduled"
        if ctx.artifacts is not None:
            ctx.artifacts.write_json("bundle.json", bundle.model_dump(mode="json"))
        if not dry_run:
            from ai_insight.common.store import save_bundle

            saved = str(save_bundle(bundle, root=cfg.data_dir, live=live))
        code = 1 if status == "failed" else 0
        return _finish_bundle(log, status, code, started, bundle, saved, artifacts, ctx=ctx)
    except Exception as exc:
        log.warning(f"runner failed: {type(exc).__name__}: {exc}")
        artifacts.error(f"{type(exc).__name__}: {exc}", step="build", inputs_summary=traceback.format_exc()[-2000:])
        ctx_ref = locals().get("ctx")
        return _finish_bundle(log, "failed", 1, started, bundle, saved, artifacts, ctx=ctx_ref if isinstance(ctx_ref, RunContext) else None)
    finally:
        artifacts.close()


def bundle_cli_main(insight_id: str, build_fn: BundleBuildFn, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"insight bundle {insight_id}")
    parser.add_argument("--date", default="", help="Trading date YYYY-MM-DD. Default: today in IST.")
    parser.add_argument("--force", action="store_true", help="Kept for scripts; every run rebuilds the bundle.")
    parser.add_argument("--dry-run", action="store_true", help="Build without calling the model or saving.")
    parser.add_argument("--verbose", action="store_true", help="Keep the full prompt next to the log.")
    parser.add_argument("--live", action="store_true", help="Window ends now. Saved beside the nightly file.")
    parser.add_argument("--only", default="", help="Optional filter passed by some bundle insights.")
    args = parser.parse_args(argv)
    trading_date = date.fromisoformat(args.date) if args.date else (resolve_live_date() if args.live else ist_now().date())
    outcome = run_bundle_insight(
        insight_id,
        build_fn,
        trading_date,
        force=args.force or args.live,
        dry_run=args.dry_run,
        verbose=args.verbose,
        live=args.live,
    )
    print(
        f"{outcome.status} exit={outcome.exit_code} duration={outcome.duration_sec:.1f}s "
        f"tokens={outcome.tokens} sources={outcome.source_count}"
    )
    return outcome.exit_code


def _finish_bundle(
    log: RunLog,
    status: str,
    code: int,
    started: float,
    bundle: InsightBundle | None,
    saved: str,
    artifacts: Any = None,
    *,
    ctx: RunContext | None = None,
) -> RunOutcome:
    duration = time.perf_counter() - started
    tokens = 0
    tokens_in = 0
    tokens_out = 0
    sources = 0
    items = 0
    skipped: list[str] = []
    llm_calls = 0
    if ctx is not None:
        tokens_in = sum(int(getattr(item, "input_tokens", 0) or 0) for item in ctx.usages)
        tokens_out = sum(int(getattr(item, "output_tokens", 0) or 0) for item in ctx.usages)
        tokens = tokens_in + tokens_out
        llm_calls = len(getattr(ctx, "llm_summaries", []) or [])
    if bundle is not None:
        items = len(bundle.items)
        skipped = list((bundle.meta or {}).get("skipped_sectors") or [])
        for item in bundle.items:
            sources += len(item.sources)
        if ctx is not None and isinstance(bundle.meta, dict):
            bundle.meta["usage"] = {
                "input_tokens": tokens_in,
                "output_tokens": tokens_out,
                "calls": llm_calls,
            }
            bundle.meta["llm_calls"] = list(getattr(ctx, "llm_summaries", []) or [])
        if artifacts is not None:
            artifacts.write_json("envelope.json", bundle.model_dump(mode="json"))
            artifacts.decision(f"items={items} skipped_indexes={len(skipped)}")
            if skipped:
                artifacts.write_json("skipped_indexes.json", skipped)
    log.line("RESULT", f"status={status} duration={duration:.1f}s items={items} tokens={tokens} sources={sources} skipped={len(skipped)}")
    log.summary(status=status, duration_sec=duration, tokens=tokens, source_count=sources, saved_path=saved)
    if artifacts is not None:
        artifacts.finalize(
            {
                "status": status,
                "duration_sec": round(duration, 3),
                "duration_ms": round(duration * 1000, 1),
                "llm_calls": llm_calls,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "sources": sources,
                "validation": None,
                "freshness": "",
                "items": items,
                "skipped_indexes": len(skipped),
            }
        )
    _write_job_progress(_run_id_from_bundle(bundle, artifacts), artifacts, status)
    return RunOutcome(status, code, duration, tokens, sources, str(log.path), None)


def _run_id_from_bundle(bundle: InsightBundle | None, artifacts: Any) -> str:
    if bundle is not None and bundle.items:
        rid = bundle.items[0].meta.run_id
        if rid:
            return rid
    return str(getattr(artifacts, "run_id", "") or "")


def _bound_llm(ctx: RunContext) -> Callable[..., Any]:
    def call(system: str, user: str, json_schema: dict[str, Any], max_tokens: int = 500, kind: str = "draft") -> Any:
        ctx.prompts.append({"system": system, "user": user, "schema": json_schema, "max_tokens": max_tokens, "kind": kind})
        if ctx.dry_run:
            raise DryRunHalt()
        from ai_insight.common.llm import generate_json

        started_call = time.perf_counter()
        label = ctx.llm_label or kind
        try:
            result = generate_json(
                system,
                user,
                json_schema,
                max_tokens=max_tokens,
                config=ctx.config,
                kind=kind,
            )
        except Exception as exc:
            if ctx.artifacts is not None:
                ctx.artifacts.llm_call(
                    kind,
                    {"system": system, "user": user},
                    None,
                    None,
                    (time.perf_counter() - started_call) * 1000,
                    0,
                    error=f"{type(exc).__name__}: {exc}",
                    label=label,
                    section=ctx.insight_id,
                    log_full_prompt=ctx.config.log_full_prompts,
                )
            raise
        ctx.add_usage(result.usage)
        if ctx.artifacts is not None:
            ctx.artifacts.llm_call(
                kind,
                result.request,
                {"raw_text": result.raw_text, "data": result.data},
                result.usage,
                (time.perf_counter() - started_call) * 1000,
                result.usage.retries,
                label=label,
                section=ctx.insight_id,
                log_full_prompt=ctx.config.log_full_prompts,
            )
        envelope_calls = getattr(ctx, "llm_summaries", None)
        if envelope_calls is None:
            ctx.llm_summaries = []  # type: ignore[attr-defined]
        ctx.llm_summaries.append(  # type: ignore[attr-defined]
            {
                "kind": kind,
                "label": label,
                "model": result.usage.model,
                "input_tokens": result.usage.input_tokens,
                "output_tokens": result.usage.output_tokens,
                "tokens": result.usage.input_tokens + result.usage.output_tokens,
            }
        )
        return result

    return call


def _validate_with_one_retry(
    ctx: RunContext,
    build_fn: BuildFn,
    envelope: Envelope,
    log: RunLog,
) -> tuple[Envelope, str]:
    result = validate_insight(envelope)
    _log_checks(log, result, attempt=1)
    if result.ok:
        envelope.meta.validation = _validation_payload(result)
        return envelope, "ok"
    log.warning("prose check failed; building once more")
    second = build_fn(ctx)
    if second.status != "ok":
        return second, second.status
    result = validate_insight(second)
    _log_checks(log, result, attempt=2)
    second.meta.validation = _validation_payload(result)
    if result.ok:
        return second, "ok"
    second.status = "degraded"
    log.warning("prose check failed twice; saved as degraded and hidden from investors")
    return second, "degraded"


def _log_checks(log: RunLog, result: Any, *, attempt: int) -> None:
    parts = [f"{'PASS' if check.passed else 'FAIL'} {check.name} {check.detail}".strip() for check in result.checks]
    log.step(3, 3, "VALIDATION", f"attempt={attempt} " + " | ".join(parts))


def _validation_payload(result: Any) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "errors": list(result.errors),
        "checks": [{"name": check.name, "passed": check.passed, "detail": check.detail} for check in result.checks],
    }


def _stamp(envelope: Envelope, window: tuple[str, str], run_id: str, config: CommonConfig, ctx: RunContext) -> None:
    envelope.meta.run_id = run_id
    envelope.meta.window_utc = [window[0], window[1]]
    if not envelope.meta.model:
        envelope.meta.model = config.llm_model
    envelope.meta.llm_calls = list(getattr(ctx, "llm_summaries", []) or [])
    envelope.meta.usage = UsageMeta(
        input_tokens=sum(int(getattr(item, "input_tokens", 0) or 0) for item in ctx.usages),
        output_tokens=sum(int(getattr(item, "output_tokens", 0) or 0) for item in ctx.usages),
        cached_tokens=sum(int(getattr(item, "cached_tokens", 0) or 0) for item in ctx.usages),
        attempts=sum(int(getattr(item, "attempts", 0) or 0) for item in ctx.usages),
    )


def _shell(
    insight_id: str,
    trading_date: date,
    status: str,
    *,
    skip_reason: str | None,
    window: tuple[str, str],
    run_id: str,
    config: CommonConfig,
    now: datetime | None,
    headline: str = "",
    body: str = "",
    facts: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
) -> Envelope:
    return Envelope(
        insight_id=insight_id,
        trading_date=trading_date.isoformat(),
        as_of_ist=to_ist(now).isoformat() if now else ist_now().isoformat(),
        status=status,  # type: ignore[arg-type]
        skip_reason=skip_reason,
        headline=headline,
        body=body,
        facts=facts or {},
        meta=Meta(
            model=config.llm_model,
            window_utc=[window[0], window[1]],
            run_id=run_id,
            validation=validation or {},
        ),
    )


def _failed(
    insight_id: str,
    trading_date: date,
    exc: BaseException,
    window: tuple[str, str],
    run_id: str,
    config: CommonConfig,
    now: datetime | None,
) -> Envelope:
    lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    summary = "\n".join("".join(lines).strip().splitlines()[-15:])
    return _shell(
        insight_id,
        trading_date,
        "failed",
        skip_reason=None,
        window=window,
        run_id=run_id,
        config=config,
        now=now,
        facts={"error": f"{type(exc).__name__}: {exc}"},
        validation={"traceback": summary},
    )


def _finish(
    log: RunLog,
    status: str,
    code: int,
    started: float,
    envelope: Envelope | None,
    saved: str,
    artifacts: Any = None,
) -> RunOutcome:
    duration = time.perf_counter() - started
    tokens = 0
    sources = 0
    tokens_in = 0
    tokens_out = 0
    if envelope is not None:
        tokens_in = envelope.meta.usage.input_tokens
        tokens_out = envelope.meta.usage.output_tokens
        tokens = tokens_in + tokens_out
        sources = len(envelope.sources)
        artifacts_dir = getattr(artifacts, "dir", None)
        if artifacts_dir is not None:
            artifacts.write_json("envelope.json", envelope.model_dump(mode="json"))
            artifacts.write_json("validation.json", envelope.meta.validation)
    log.line("RESULT", f"status={status} duration={duration:.1f}s tokens={tokens} sources={sources}")
    log.summary(status=status, duration_sec=duration, tokens=tokens, source_count=sources, saved_path=saved)
    if artifacts is not None:
        artifacts.finalize(
            {
                "status": status,
                "duration_sec": round(duration, 3),
                "duration_ms": round(duration * 1000, 1),
                "llm_calls": len(getattr(envelope, "meta", None).llm_calls) if envelope else 0,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "sources": sources,
                "validation": (envelope.meta.validation.get("ok") if envelope else None),
                "freshness": (envelope.meta.freshness_warning if envelope else ""),
            }
        )
    _write_job_progress(envelope.meta.run_id if envelope else "", artifacts, status)
    return RunOutcome(status, code, duration, tokens, sources, str(log.path), envelope)


def _write_job_progress(run_id: str, artifacts: Any, status: str) -> None:
    job_id = os.environ.get("INSIGHTS_JOB_ID", "").strip()
    if not job_id or artifacts is None:
        return
    run_dir = str(getattr(artifacts, "dir", "") or "")
    insight_id = str(getattr(artifacts, "insight_id", "") or "")
    if not insight_id:
        return
    path = load_config().data_dir / "jobs" / job_id / f"{insight_id}.json"
    tokens = 0
    usage_file = Path(run_dir) / "usage.json" if run_dir else None
    if usage_file is not None and usage_file.is_file():
        try:
            usage = json.loads(usage_file.read_text(encoding="utf-8"))
            tokens = int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)
        except (OSError, json.JSONDecodeError, TypeError):
            tokens = 0
    payload = {
        "status": "done" if status in {"ok", "degraded", "skipped"} else "failed",
        "step": status,
        "run_id": run_id,
        "run_dir": run_dir,
        "tokens": tokens,
    }
    if run_dir:
        manifest = Path(run_dir) / "manifest.json"
        if manifest.is_file():
            payload["log_path"] = run_dir
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, path)


def _print_dry_run(ctx: RunContext) -> None:
    import json

    print("FACTS")
    print(json.dumps(ctx.facts, ensure_ascii=False, indent=2, default=str))
    print("PROMPTS")
    print(_prompt_text(ctx))


def _prompt_text(ctx: RunContext) -> str:
    if not ctx.prompts:
        return "(no prompt recorded)"
    chunks = []
    for index, prompt in enumerate(ctx.prompts, start=1):
        chunks.append(f"--- prompt {index} ---\nSYSTEM\n{prompt.get('system', '')}\nUSER\n{prompt.get('user', '')}")
    return "\n".join(chunks)


def _freshness_warning(window: tuple[str, str], config: CommonConfig, artifacts: Any) -> str:
    enabled = config.check_freshness
    if enabled is None:
        enabled = "pytest" not in sys.modules
    if not enabled:
        return ""
    try:
        from ai_insight.common.freshness import is_stale, newest_scraped_at

        newest = newest_scraped_at(window, config=config)
        stale = is_stale(window, config=config)
    except Exception as exc:
        artifacts.warning(f"freshness check failed: {type(exc).__name__}: {exc}", step="freshness")
        return ""
    artifacts.write_json("window_freshness.json", {"newest_scraped_at": None if newest is None else newest.isoformat(), "stale": stale})
    if stale:
        return f"newest scraped_at in the window is older than {config.max_ingest_age_hours:g}h or missing"
    return ""


def _market_phase(now: datetime | None) -> str:
    clock = ist_now(now)
    minutes = clock.hour * 60 + clock.minute
    if 9 * 60 + 15 <= minutes < 15 * 60 + 30:
        return "open"
    return "closed"


def resolve_live_date(now: datetime | None = None, holidays_path=None) -> date:
    """Today once the cash market is open; otherwise the previous trading day."""
    from ai_insight.common.trading_calendar import is_trading_day, prev_trading_day

    clock = ist_now(now)
    day = clock.date()
    opened = clock.hour > 9 or (clock.hour == 9 and clock.minute >= 15)
    if is_trading_day(day, holidays_path=holidays_path) and opened:
        return day
    return prev_trading_day(day, holidays_path=holidays_path)


def _parse(value: str) -> datetime:
    from news_pipeline.textutil import parse_time

    parsed = parse_time(value)
    if parsed is None:
        raise ValueError(value)
    return parsed


def _short(facts: dict[str, Any]) -> str:
    import json

    text = json.dumps(facts, ensure_ascii=False, default=str)
    return text if len(text) <= 500 else text[:500] + "..."
