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


def clip_log_text(text: str, limit: int = 240) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def new_query_logger() -> QueryLogger:
    settings = get_settings()
    log_dir = settings.rag_query_log_path()
    query_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + secrets.token_hex(3)
    path = log_dir / f"{query_id}.log"
    return QueryLogger(query_id=query_id, log_path=path)


class QueryLogger:
    def __init__(self, query_id: str, log_path: Path) -> None:
        self.query_id = query_id
        self.log_path = log_path
        self.started_at = time.perf_counter()
        self.llm_provider = ""
        self.llm_calls = 0
        self.llm_input_tokens = 0
        self.llm_output_tokens = 0
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

    def write(self, message: str) -> None:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"{stamp} {message}\n"
        with self._file_lock:
            with self.log_path.open("a", encoding="utf-8") as handle:
                handle.write(line)

    def log_request(self, payload: dict[str, Any]) -> None:
        self.write("request " + _kv(payload))

    def log_parsed(self, parsed: Any) -> None:
        self.write(
            "parsed "
            + _kv(
                {
                    "question": clip_log_text(parsed.question, 500),
                    "window_label": parsed.window_label,
                    "published_from": parsed.published_from,
                    "published_to": parsed.published_to,
                    "stock_hint": parsed.stock_hint or "",
                    "entity_resolved": parsed.entity_resolved,
                    "entity_match_note": parsed.entity_match_note,
                }
            )
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
    ) -> None:
        if provider and not self.llm_provider:
            self.llm_provider = provider
        self.llm_calls += 1
        self.llm_input_tokens += max(0, input_tokens)
        self.llm_output_tokens += max(0, output_tokens)
        total_bit = f" total_tokens={total_tokens}" if total_tokens is not None else ""
        self.write(
            f"llm call provider={provider} "
            f"call_index={self.llm_calls} model={model} http_status={http_status} "
            f"input_tokens={input_tokens} output_tokens={output_tokens}{total_bit} "
            f"duration_sec={round(duration_sec, 3)} "
            f"cumulative_input_tokens={self.llm_input_tokens} "
            f"cumulative_output_tokens={self.llm_output_tokens}"
        )

    def record_deepseek(self, **kwargs: Any) -> None:
        """Backward-compatible alias for record_llm_call."""
        provider = str(kwargs.pop("provider", "deepseek"))
        self.record_llm_call(provider=provider, **kwargs)

    def log_error(self, stage: str, message: str) -> None:
        self.write(f"error stage={stage} message={clip_log_text(message, 500)}")

    def finish(
        self,
        *,
        outcome: str,
        article_count: int,
        insight_source: str = "",
    ) -> dict[str, Any]:
        total_seconds = round(time.perf_counter() - self.started_at, 3)
        source_bit = f" insight_source={insight_source}" if insight_source else ""
        provider_bit = f" llm_provider={self.llm_provider}" if self.llm_provider else ""
        self.write(
            "query finished "
            f"outcome={outcome} articles_returned={article_count}{source_bit}{provider_bit} "
            f"llm_calls={self.llm_calls} "
            f"llm_input_tokens={self.llm_input_tokens} "
            f"llm_output_tokens={self.llm_output_tokens} "
            f"total_seconds={total_seconds}"
        )
        return {
            "query_id": self.query_id,
            "log_file": str(self.log_path),
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
