---
name: observability-debugging
description: Diagnose production issues and instrument AI pipelines with structured logs, traces, latency spans, token/call counters, correlation IDs, and actionable error context. Use for slow requests, intermittent failures, poor answers, or hard-to-reproduce bugs.
---

# Observability and Debugging

## Objective
Make failures diagnosable with the smallest useful amount of safe telemetry. Tie user-visible answer quality and latency to the individual pipeline stages without logging secrets or sensitive investor data.

## Trigger when
- Investigating production latency, timeouts, provider errors, incorrect answers, retrieval misses, or intermittent failures.
- Adding metrics/tracing for FastAPI, LangGraph, Qdrant/OpenSearch, news ingestion, or model calls.
- There is insufficient evidence to identify the bottleneck or failure stage.

## Bounded workflow
1. **Reproduce and scope.** Identify endpoint, time window, request ID/correlation ID, query class, environment, and impact. Use sanitized examples. Do not dump all logs into context.
2. **Trace the request path.** Follow request → router/graph → tools/retrieval → LLM → response. Inspect relevant existing log/metric code and deployment setup first.
3. **Form a testable hypothesis.** Separate queueing, application CPU, network, database, provider, retries, and generation. Check timestamps and clock consistency.
4. **Instrument targeted spans.** Add structured events/spans around stages with duration, status, retry count, result count, model/provider identifier, token counts when available, and error category. Avoid high-cardinality labels such as raw query or user ID in metrics.
5. **Protect data.** Do not log raw prompts, article bodies, access tokens, API keys, full portfolio data, or personally identifying content by default. Redact or hash identifiers when possible and apply retention/access controls.
6. **Reproduce with focused tests.** Use a small sanitized request or mock. Avoid retrying production actions that may have side effects.
7. **Fix root cause.** Make the smallest code or configuration change. Do not merely suppress errors or lower log levels to hide symptoms.
8. **Verify and report.** Re-run the reproduction and compare relevant measurements. Include uncertainty if logs are incomplete.

## Suggested AI pipeline signals
- Request: request count, error rate, end-to-end duration, cancellation, status code.
- Routing/agent: selected query class, node duration, model/tool call count, loop/stop reason.
- Retrieval: backend, duration, candidate count, filtered count, empty-result rate, rerank duration, freshness distribution.
- LLM: provider/model identifier, queue time if available, time-to-first-token, generation duration, prompt/completion tokens, rate-limit/timeout counts.
- News ingestion: fetched, parsed, deduplicated, rejected, indexed, stale/error counts; publication time and ingestion time kept distinct.

## Token efficiency
- Search for existing telemetry and inspect one representative trace before adding new instrumentation.
- Prefer low-cardinality aggregate metrics and sampled traces over verbose per-chunk logging.
- Do not add a telemetry SDK without checking existing dependencies and deployment support.

## Required checks
- Correlation ID propagates across async/task boundaries where feasible.
- Logging works on success, error, timeout, and cancellation paths.
- Sensitive values are redacted; logs do not leak article/private investor payloads.
- Metrics labels remain bounded; tracing overhead is reasonable.
- Tests verify key fields and redaction behavior.

## Output format
1. Symptom, impact, and reproduction
2. Evidence/timeline and suspected stage
3. Root cause or ranked hypotheses
4. Instrumentation/fix applied
5. Before/after results or missing measurements
6. Follow-up alerts, dashboards, and residual risk
