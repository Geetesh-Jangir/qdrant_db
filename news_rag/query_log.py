"""One log file per /api/ask query: filters, Qdrant hits, insight LLM token usage."""

from __future__ import annotations

import json
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from news_rag.config import get_settings


# Human-readable purpose for each LLM `stage=` passed to call_json_llm / call_insight_llm.
LLM_STAGE_CATALOG: dict[str, dict[str, str]] = {
    "brief": {
        "pipeline": "insight_v2",
        "phase": "1_brief",
        "purpose": "Decompose the user question into sub-asks, subjects, window, and evidence_needs (facets).",
        "output": "JSON: goal, sub_asks, evidence_needs, success_criteria",
    },
    "news_reader": {
        "pipeline": "insight_v2",
        "phase": "2b_news_reader",
        "purpose": "Read the cleaned article bodies and extract cited claims, the overall sector tone, and which sectors the news helps or hurts.",
        "output": "JSON: tone, tone_reason, claims[{text, sentiment, article}], sectors_positive, sectors_negative, themes",
    },
    "affected_sectors": {
        "pipeline": "insight_v2",
        "phase": "2_gather",
        "purpose": "Pick which sectors the retrieved news helps or hurts (used for driver-led questions).",
        "output": "JSON: sectors[{name, direction, reason}]",
    },
    "interpret": {
        "pipeline": "insight_v2",
        "phase": "4_interpret",
        "purpose": "Write the answer: headline, sector read tied to the cited news, one line per fund linking news to its exposure, and a closing line. Numbers come from findings only.",
        "output": "JSON: headline, sector_read, fund_lines{isin: text}, closing_summary",
    },
    "judge": {
        "pipeline": "insight_v2",
        "phase": "5_judge",
        "purpose": "Score draft answer quality (grounded, on-topic, no advice) for telemetry — does not block the user response.",
        "output": "JSON: answers_query, grounded, on_topic, no_advice, no_extra, pass",
    },
    "agent": {
        "pipeline": "legacy",
        "phase": "agent",
        "purpose": "Legacy ask agent tool-planning round (not used in insight_v2 default path).",
        "output": "JSON: tools / status",
    },
    "composer": {
        "pipeline": "legacy",
        "phase": "compose",
        "purpose": "Legacy final answer composer.",
        "output": "JSON: headline, narrative, bullets",
    },
    "router": {
        "pipeline": "legacy",
        "phase": "router",
        "purpose": "Legacy query router / intent classification.",
        "output": "JSON: intent, entities",
    },
    "contract_planner": {
        "pipeline": "legacy",
        "phase": "contract",
        "purpose": "Legacy answer contract planner.",
        "output": "JSON: plan",
    },
    "insight": {
        "pipeline": "fund_brief",
        "phase": "compose",
        "purpose": "Generate fund brief insight prose from retrieved articles.",
        "output": "JSON or text insight",
    },
    "json": {
        "pipeline": "any",
        "phase": "llm",
        "purpose": "Structured JSON LLM call (stage not labeled).",
        "output": "JSON",
    },
}


def clip_log_text(text: str, limit: int = 240) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def new_query_logger(*, kind: str = "ask") -> QueryLogger:
    settings = get_settings()
    log_dir = settings.rag_query_log_path()
    query_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + secrets.token_hex(3)
    prefix = "fund_brief_" if kind == "fund_brief" else "ask_"
    path = log_dir / f"{prefix}{query_id}.log"
    logger = QueryLogger(query_id=query_id, log_path=path, kind=kind or "ask")
    logger.write(f"kind={kind or 'ask'}")
    return logger


def new_fund_brief_logger() -> QueryLogger:
    return new_query_logger(kind="fund_brief")


class QueryLogger:
    def __init__(self, query_id: str, log_path: Path, *, kind: str = "ask") -> None:
        self.query_id = query_id
        self.log_path = log_path
        self.kind = kind
        self.started_at = time.perf_counter()
        self.llm_provider = ""
        self.llm_calls = 0
        self.llm_input_tokens = 0
        self.llm_output_tokens = 0
        self._summary: dict[str, Any] = {"query_id": query_id, "kind": kind, "events": []}
        self._llm_journal: list[dict[str, Any]] = []
        self._pipeline_stages: list[dict[str, Any]] = []
        self._file_lock = threading.Lock()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if log_path.exists():
            stem = log_path.stem
            suffix = log_path.suffix
            counter = 1
            while log_path.exists():
                log_path = log_path.with_name(f"{stem}_{counter}{suffix}")
                counter += 1
        self.log_path = log_path
        log_path.write_text("", encoding="utf-8")
        self.write(f"query started query_id={query_id} log_file={log_path}")
        self.write(
            "LOG_LEGEND "
            "PIPELINE=insight_v2 stages | "
            "LLM_START=what the model is asked to do | LLM_HTTP=per-call tokens/latency | "
            "LLM_DONE=parse outcome + step tokens | LLM_TOKENS_TOTAL=run totals | "
            "BRIEF/GATHER/COMPUTE/INTERPRET/VERIFY=deterministic stages | TOOL=registry adapter"
        )

    def write(self, message: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"{stamp} {message}\n"
        with self._file_lock:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line)

    def note(self, event: str, **fields: Any) -> None:
        """Append a structured event to the JSON sidecar written at finish()."""
        payload: dict[str, Any] = {"t": datetime.now(timezone.utc).isoformat(), "event": event}
        payload.update(fields)
        self._summary.setdefault("events", []).append(payload)

    def log_request(self, payload: dict[str, Any]) -> None:
        self.write("request " + _kv(payload))

    def log_stage(self, stage: str, **fields: Any) -> None:
        self.write(stage.upper() + " " + _kv(fields))
        safe = {k: v for k, v in fields.items() if k != "event"}
        self.note(stage, **safe)

    def log_pipeline(self, phase: str, event: str, **fields: Any) -> None:
        """Insight v2 (and shared) pipeline milestones: start | done | skip | retry."""
        line = f"PIPELINE phase={phase} event={event}"
        if fields:
            line += " " + _kv(fields)
        self.write(line)
        entry = {"phase": phase, "event": event, **fields}
        self._pipeline_stages.append(entry)
        self.note("pipeline", phase=phase, step_event=event, **fields)

    def llm_stage_info(self, stage: str | None) -> dict[str, str]:
        key = (stage or "json").strip() or "json"
        return LLM_STAGE_CATALOG.get(key, LLM_STAGE_CATALOG["json"])

    def log_llm_start(
        self,
        *,
        stage: str | None,
        provider: str,
        model: str,
        max_tokens: int,
        system_chars: int,
        user_chars: int,
        repair: bool = False,
    ) -> int:
        """Log intent before an LLM HTTP call; returns call_index (upcoming)."""
        info = self.llm_stage_info(stage)
        call_index = self.llm_calls + 1
        repair_bit = " repair=true" if repair else ""
        self.write(
            f"LLM_START call_index={call_index} stage={stage or 'json'}{repair_bit} "
            f"provider={provider} model={model} max_tokens={max_tokens} "
            f"system_chars={system_chars} user_chars={user_chars} "
            f"purpose={json.dumps(info.get('purpose', ''), ensure_ascii=False)} "
            f"expected_output={info.get('output', '')}"
        )
        self.note(
            "llm_start",
            call_index=call_index,
            stage=stage or "json",
            provider=provider,
            model=model,
            purpose=info.get("purpose"),
            pipeline_phase=info.get("phase"),
        )
        return call_index

    def log_llm_result(
        self,
        *,
        stage: str | None,
        call_index: int,
        finish_reason: str,
        truncated: bool,
        repaired: bool,
        parsed_summary: str = "",
        raw_preview: str = "",
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> None:
        info = self.llm_stage_info(stage)
        token_bit = ""
        if input_tokens is not None or output_tokens is not None:
            tot = total_tokens
            if tot is None and input_tokens is not None and output_tokens is not None:
                tot = input_tokens + output_tokens
            token_bit = (
                f" input_tokens={input_tokens or 0} output_tokens={output_tokens or 0} "
                f"step_total_tokens={tot if tot is not None else ''} "
                f"cumulative_input_tokens={self.llm_input_tokens} "
                f"cumulative_output_tokens={self.llm_output_tokens}"
            )
        self.write(
            f"LLM_DONE call_index={call_index} stage={stage or 'json'} "
            f"pipeline_phase={info.get('phase', '')} "
            f"finish={finish_reason or 'unknown'} truncated={truncated} repaired={repaired}{token_bit} "
            f"parsed_summary={clip_log_text(parsed_summary, 400)}"
        )
        if raw_preview and truncated:
            self.write(f"LLM_TRUNCATED_PREVIEW call_index={call_index} text={clip_log_text(raw_preview, 300)}")
        self.note(
            "llm_done",
            call_index=call_index,
            stage=stage or "json",
            truncated=truncated,
            parsed_summary=clip_log_text(parsed_summary, 200),
        )

    def log_brief(self, *, source: str, brief_summary: dict[str, Any]) -> None:
        self.write("BRIEF " + _kv(brief_summary))
        self.note("brief", source=source, summary=brief_summary)

    def log_gather_ledger(self, ledger: list[dict[str, Any]], *, articles: int, tool_runs: int) -> None:
        self.write(f"GATHER articles={articles} tool_runs={tool_runs}")
        for row in ledger:
            self.write(
                "GATHER facet "
                + _kv(
                    {
                        "facet": row.get("facet"),
                        "status": row.get("status"),
                        "tool": row.get("tool"),
                        "reason": clip_log_text(str(row.get("reason") or ""), 120),
                    }
                )
            )
        self.note("gather", articles=articles, ledger=ledger)

    def log_tool_invocation(
        self,
        *,
        tool: str,
        facet: str = "",
        ok: bool,
        elapsed_ms: float | None = None,
        error: str = "",
        detail: str = "",
    ) -> None:
        self.write(
            "TOOL "
            + _kv(
                {
                    "name": tool,
                    "facet": facet,
                    "ok": ok,
                    "elapsed_ms": round(elapsed_ms, 2) if elapsed_ms is not None else None,
                    "error": error or None,
                    "detail": clip_log_text(detail, 200) if detail else None,
                }
            )
        )
        self.note("tool", tool=tool, facet=facet, ok=ok, error=error or None)

    def log_news_read(self, read: dict[str, Any]) -> None:
        """What the news reader concluded: tone, claims (with their source articles), sector calls."""
        claims = read.get("claims") or []
        self.write(
            "NEWS_READ "
            + _kv(
                {
                    "mode": read.get("mode"),
                    "tone": read.get("tone"),
                    "articles_read": read.get("articles_read"),
                    "claims": len(claims),
                    "dropped_claims": read.get("dropped_claims"),
                    "sectors_positive": [s.get("name") for s in read.get("sectors_positive") or []],
                    "sectors_negative": [s.get("name") for s in read.get("sectors_negative") or []],
                    "tone_reason": clip_log_text(str(read.get("tone_reason") or ""), 220),
                }
            )
        )
        for i, c in enumerate(claims, 1):
            self.write(
                f"  CLAIM {i} [{c.get('sentiment')}] art#{c.get('article')} "
                f"{clip_log_text(str(c.get('text') or ''), 200)} | src={clip_log_text(str(c.get('title') or ''), 70)}"
            )
        self.note("news_read", **{k: v for k, v in read.items() if k != "event"})

    def log_compute(self, **fields: Any) -> None:
        self.write("COMPUTE " + _kv(fields))
        self.note("compute", **fields)

    def log_interpret(self, **fields: Any) -> None:
        self.write("INTERPRET " + _kv(fields))
        self.note("interpret", **fields)

    def log_verify(self, **fields: Any) -> None:
        self.write("VERIFY " + _kv(fields))
        self.note("verify", **fields)

    def log_parsed(self, parsed: Any) -> None:
        fund = parsed.fund_resolved or {}
        router = getattr(parsed, "router_result", None)
        fields: dict[str, Any] = {
            "question": clip_log_text(parsed.question, 500),
            "intent": getattr(parsed, "intent", ""),
            "window_label": parsed.window_label,
            "published_from": parsed.published_from,
            "published_to": parsed.published_to,
            "stock_hint": parsed.stock_hint or "",
            "entity_resolved": parsed.entity_resolved,
            "entity_match_note": parsed.entity_match_note,
            "sub_questions": getattr(parsed, "sub_questions", []) or [],
            "fund_ambiguous": bool(getattr(parsed, "fund_ambiguous", False)),
            "close_funds": getattr(parsed, "close_funds", []) or [],
        }
        if fund:
            fields["fund_isin"] = fund.get("isin") or ""
            fields["fund_name"] = fund.get("fund_short_name") or fund.get("fund_name") or ""
        if router is not None:
            fields["router_fund_isin"] = getattr(getattr(router, "fund", None), "isin", "") or ""
            fields["router_fund_name"] = getattr(getattr(router, "fund", None), "name", "") or ""
            fields["router_companies"] = getattr(router, "companies", []) or []
            fields["router_event_focus"] = getattr(router, "event_focus", "") or ""
            fields["router_window_days"] = getattr(router, "window_days", None)
            fields["router_asked"] = getattr(router, "asked", []) or []
        self.write("parsed " + _kv(fields))
        self.note("parsed", intent=fields.get("intent"), entities=fields.get("entity_resolved"))

    def log_fund_lookup(
        self,
        *,
        extracted_isin: str,
        extracted_name: str,
        resolved: bool,
        ambiguous: bool,
        close_matches: list[str] | None = None,
        fund_isin: str = "",
        fund_name: str = "",
    ) -> None:
        self.write(
            "fund_lookup "
            + _kv(
                {
                    "extracted_isin": extracted_isin or "",
                    "extracted_name": extracted_name or "",
                    "resolved": resolved,
                    "ambiguous": ambiguous,
                    "close_matches": close_matches or [],
                    "fund_isin": fund_isin,
                    "fund_name": fund_name,
                }
            )
        )
        self.note(
            "fund_lookup",
            extracted_isin=extracted_isin,
            extracted_name=extracted_name,
            resolved=resolved,
            ambiguous=ambiguous,
            fund_isin=fund_isin,
        )

    def log_article_filter(
        self,
        *,
        retrieved_count: int,
        use_articles: list[int],
        kept_count: int,
    ) -> None:
        self.write(
            f"contract_article_filter retrieved={retrieved_count} "
            f"use_articles={use_articles} kept_for_writer={kept_count}"
        )
        self.note(
            "contract_article_filter",
            retrieved=retrieved_count,
            use_articles=use_articles,
            kept=kept_count,
        )

    def log_filters(self, spec: dict[str, Any], *, post_filters: dict[str, Any]) -> None:
        self.write("qdrant_filter_json " + json.dumps(spec, ensure_ascii=False, sort_keys=True))
        self.write("post_filters_json " + json.dumps(post_filters, ensure_ascii=False, sort_keys=True))

    def log_filters_applied(self, lines: list[str]) -> None:
        self.write("retrieval_filters_applied count=" + str(len(lines)))
        for index, line in enumerate(lines, start=1):
            self.write(f"retrieval_filter {index}={line}")

    def log_insight_output(
        self,
        *,
        insight_source: str,
        char_count: int,
        preview: str,
    ) -> None:
        self.write(
            f"insight_output source={insight_source} chars={char_count} "
            f"preview={clip_log_text(preview, 500)}"
        )

    def log_step(self, name: str, seconds: float, **extra: Any) -> None:
        bits = [f"step name={name} seconds={round(seconds, 3)}"]
        for key, value in extra.items():
            bits.append(f"{key}={value}")
        self.write(" ".join(bits))

    def log_articles_block(self, label: str, rows: list[dict], *, snippet_limit: int = 800) -> None:
        self.write(f"{label} count={len(rows)}")
        for index, row in enumerate(rows, start=1):
            snippet = clip_log_text(row.get("scraped_text") or row.get("snippet") or "", snippet_limit)
            self.write(
                f"{label} hit rank={index} "
                + _kv(
                    {
                        "url": row.get("url"),
                        "title": clip_log_text(str(row.get("title") or ""), 160),
                        "source": row.get("source"),
                        "published_at": row.get("published_at"),
                        "score": row.get("score", row.get("_vector_score")),
                        "max_impact": row.get("max_impact"),
                        "max_relevance": row.get("max_relevance"),
                        "direction": row.get("direction"),
                        "event_type": row.get("event_type"),
                        "entity_names": row.get("entity_names"),
                        "snippet": snippet,
                    }
                )
            )

    def record_llm_call(
        self,
        *,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int | None,
        duration_sec: float,
        http_status: int,
        stage: str | None = None,
    ) -> None:
        if provider and not self.llm_provider:
            self.llm_provider = provider
        self.llm_calls += 1
        self.llm_input_tokens += max(0, input_tokens)
        self.llm_output_tokens += max(0, output_tokens)
        total_bit = f" total_tokens={total_tokens}" if total_tokens is not None else ""
        stage_bit = f" stage={stage}" if stage else ""
        self.write(
            f"LLM_HTTP provider={provider}{stage_bit} "
            f"call_index={self.llm_calls} model={model} http_status={http_status} "
            f"input_tokens={input_tokens} output_tokens={output_tokens}{total_bit} "
            f"duration_sec={round(duration_sec, 3)} "
            f"cumulative_input_tokens={self.llm_input_tokens} "
            f"cumulative_output_tokens={self.llm_output_tokens}"
        )
        self._llm_journal.append(
            {
                "call_index": self.llm_calls,
                "stage": stage or "json",
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "duration_sec": round(duration_sec, 3),
                "http_status": http_status,
            }
        )

    def record_deepseek(self, **kwargs: Any) -> None:
        """Backward-compatible alias for record_llm_call."""
        provider = str(kwargs.pop("provider", "deepseek"))
        self.record_llm_call(provider=provider, **kwargs)

    def log_error(self, stage: str, message: str) -> None:
        self.write(f"error stage={stage} message={clip_log_text(message, 500)}")

    def finish_from_ask_result(self, result: dict[str, Any], *, question: str = "") -> dict[str, Any]:
        """Write insight preview + JSON sidecar (same as POST /api/ask)."""
        article_count = len(result.get("sources") or [])
        outcome = str(result.get("outcome") or "ok")
        if result.get("refused"):
            outcome = "refused"
        if result.get("pipeline_errors") and outcome == "ok":
            outcome = "partial"
        insight = str(result.get("insight") or "")
        self.log_insight_output(
            insight_source=str(result.get("insight_source") or "insight_v2"),
            char_count=len(insight),
            preview=str(result.get("insight_summary") or insight)[:500],
        )
        extra: dict[str, Any] = {
            "intent": result.get("intent"),
            "sub_queries": result.get("sub_queries"),
            "output_score": result.get("output_score"),
            "pipeline_errors": result.get("pipeline_errors"),
            "research_summary": {
                "evidence_needs": (result.get("research") or {}).get("evidence_needs"),
                "ledger": (result.get("research") or {}).get("ledger"),
                "verify_gaps": (result.get("research") or {}).get("verify_gaps"),
            },
        }
        q = (question or "").strip()
        if q:
            extra["question"] = q
        return self.finish(
            outcome=outcome,
            article_count=article_count,
            insight_source=str(result.get("insight_source") or ""),
            extra=extra,
        )

    def finish(
        self,
        *,
        outcome: str,
        article_count: int,
        insight_source: str = "",
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        total_seconds = round(time.perf_counter() - self.started_at, 3)
        source_bit = f" insight_source={insight_source}" if insight_source else ""
        provider_bit = f" llm_provider={self.llm_provider}" if self.llm_provider else ""
        json_path: Path | None = self.log_path.with_suffix(".json")
        self._summary.update(
            {
                "outcome": outcome,
                "articles_retrieved": article_count,
                "insight_source": insight_source,
                "llm_provider": self.llm_provider,
                "llm_calls": self.llm_calls,
                "llm_call_journal": self._llm_journal,
                "llm_input_tokens": self.llm_input_tokens,
                "llm_output_tokens": self.llm_output_tokens,
                "llm_total_tokens": self.llm_input_tokens + self.llm_output_tokens,
                "pipeline_stages": self._pipeline_stages,
                "total_seconds": total_seconds,
                "log_file": str(self.log_path),
            }
        )
        if extra:
            self._summary.update(extra)
        try:
            json_path.write_text(json.dumps(self._summary, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            json_path = None
        combined_tokens = self.llm_input_tokens + self.llm_output_tokens
        self.write(
            f"LLM_TOKENS_TOTAL llm_calls={self.llm_calls} "
            f"total_input_tokens={self.llm_input_tokens} "
            f"total_output_tokens={self.llm_output_tokens} "
            f"total_tokens={combined_tokens}"
        )
        self.write(
            "query finished "
            f"outcome={outcome} articles_returned={article_count}{source_bit}{provider_bit} "
            f"llm_calls={self.llm_calls} "
            f"llm_input_tokens={self.llm_input_tokens} "
            f"llm_output_tokens={self.llm_output_tokens} "
            f"llm_total_tokens={combined_tokens} "
            f"total_seconds={total_seconds}"
        )
        if json_path is not None:
            self.write(f"summary_json file={json_path}")
        return {
            "query_id": self.query_id,
            "log_file": str(self.log_path),
            "summary_json": str(json_path) if json_path else "",
            "llm_provider": self.llm_provider,
            "llm_calls": self.llm_calls,
            "llm_input_tokens": self.llm_input_tokens,
            "llm_output_tokens": self.llm_output_tokens,
            "total_seconds": total_seconds,
            # Deprecated aliases (same values as llm_* above).
            "deepseek_calls": self.llm_calls,
            "deepseek_input_tokens": self.llm_input_tokens,
            "deepseek_output_tokens": self.llm_output_tokens,
        }


def attach_query_log_meta(result: dict[str, Any], meta: dict[str, Any]) -> None:
    result["query_log_id"] = meta["query_id"]
    result["query_log_file"] = meta["log_file"]
    result["query_summary_json"] = meta.get("summary_json") or ""
    result["llm_provider"] = meta.get("llm_provider") or ""
    result["llm_calls"] = meta["llm_calls"]
    result["llm_input_tokens"] = meta["llm_input_tokens"]
    result["llm_output_tokens"] = meta["llm_output_tokens"]
    result["deepseek_calls"] = meta["deepseek_calls"]
    result["deepseek_input_tokens"] = meta["deepseek_input_tokens"]
    result["deepseek_output_tokens"] = meta["deepseek_output_tokens"]


def _kv(fields: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in fields.items():
        if isinstance(value, (list, dict)):
            parts.append(f"{key}={json.dumps(value, ensure_ascii=False)}")
        elif value is None:
            parts.append(f"{key}=")
        else:
            text = str(value)
            if " " in text or "=" in text:
                text = json.dumps(text, ensure_ascii=False)
            parts.append(f"{key}={text}")
    return " ".join(parts)
