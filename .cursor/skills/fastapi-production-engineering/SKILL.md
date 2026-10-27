---
name: fastapi-production-engineering
description: Implement and review production FastAPI services for AI applications, including async correctness, Pydantic contracts, dependency injection, timeouts, streaming, error handling, and backend reliability. Use for API endpoints or service-layer changes.
---

# FastAPI Production Engineering

## Objective
Make API changes safe, predictable, observable, and compatible with the existing service architecture.

## Trigger when
- Adding or changing FastAPI routes, request/response schemas, dependencies, middleware, background tasks, streaming, or service integration.
- Debugging latency, blocking event loops, connection churn, validation errors, timeouts, or production exceptions.

## Bounded workflow
1. **Trace the endpoint.** Inspect router, request/response models, dependencies, service calls, middleware, tests, and callers. Avoid opening unrelated modules.
2. **Preserve contracts.** Check status codes, response shape, validation, authentication/authorization, error format, and API compatibility. Identify breaking changes before editing.
3. **Check async behavior.** Determine whether each dependency is blocking or async. Avoid blocking network/disk/CPU work on the event loop. Use appropriate thread offloading for blocking I/O and a bounded worker/process strategy for CPU-heavy work where justified.
4. **Bound resource use.** Add explicit timeouts, connection reuse, bounded concurrency, request-size limits, and cancellation behavior appropriate to the operation. Do not create a new HTTP/database client for every request if the existing lifecycle supports reuse.
5. **Validate inputs and outputs.** Use the repository's Pydantic version and conventions. Validate tool/model outputs and external payloads; handle missing fields and provider schema drift.
6. **Handle errors intentionally.** Distinguish client errors, not-found/empty results, upstream timeouts, rate limits, and internal errors. Avoid leaking prompts, credentials, stack traces, or sensitive investor data to clients.
7. **Test.** Add route/service tests for success, invalid input, authorization, empty results, upstream failure, timeout, and response contract. Mock external providers in unit tests; use integration tests where appropriate.
8. **Review deployment impact.** Check settings/env vars, lifespan hooks, worker behavior, health/readiness checks, migrations, and rollout requirements if affected.

## Requirements for AI endpoints
- Bound LLM/tool calls with deadlines and validated arguments.
- Do not trust generated JSON until parsed and validated against the expected schema.
- Preserve citations/provenance and distinguish partial results from complete answers.
- Avoid caching user-specific results across users or portfolio versions.
- Ensure streaming response behavior matches client expectations and cleans up on cancellation.
- Do not move financial calculations into the LLM when deterministic code is available.

## Token/context efficiency
- Read the endpoint and directly called services first.
- Prefer a targeted diff and existing project patterns over architectural rewrites.
- Do not add libraries when standard project dependencies already solve the problem.

## Required checks
- Targeted tests and lint/type checks if configured.
- API schema and response compatibility.
- Timeout, cancellation, concurrency, authorization, and sensitive-error handling.
- No hardcoded credentials; configuration validated at startup.
- State exactly which checks ran and which did not.

## Output format
1. Endpoint and contract impact
2. Relevant files and current behavior
3. Change and rationale
4. Tests/checks and results
5. Operational/deployment risks
