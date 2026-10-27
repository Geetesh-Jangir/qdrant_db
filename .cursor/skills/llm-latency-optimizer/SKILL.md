---
name: llm-latency-optimizer
description: Diagnose and reduce end-to-end latency, time-to-first-token, model calls, retrieval calls, and token usage in LLM/RAG/agent services. Use when responses are slow, expensive, or make redundant tool/model calls.
---

# LLM Latency Optimizer

## Objective
Reduce measured latency and cost while preserving answer quality, grounding, correctness, and safety for the mutual-fund intelligence chatbot.

## Trigger when
- End-to-end responses exceed the product target (for example, around 10 seconds).
- A workflow makes multiple LLM, Qdrant, OpenSearch, or external-news calls.
- Prompt size, time-to-first-token, total tokens, concurrency, or throughput is problematic.
- Considering caching, parallelism, model selection, batching, streaming, or precomputation.

## Bounded workflow
1. **Trace one real path.** Find the request handler and relevant orchestration code. Do not begin with broad refactoring.
2. **Measure before changing.** Locate existing traces/logs/metrics. Break latency into request parsing, routing/planning, retrieval, reranking, LLM queue/TTFT/generation, external I/O, and serialization. Record p50/p95, call counts, prompt/output tokens, and failures if available.
3. **Classify the bottleneck.** Separate serial dependency chains from independent I/O, model generation from retrieval, cold-start effects from steady-state, and slow tail requests from typical requests.
4. **Create a call graph.** List each model/tool/database call, why it exists, whether its result is used, whether calls depend on earlier results, and its timeout/retry behavior.
5. **Choose one low-risk optimization.** Examples: remove duplicate work, bound prompt/context, parallelize independent I/O, use deterministic routing for simple cases, reuse clients/connections, cache stable data with explicit invalidation, or precompute reusable news/fund summaries.
6. **Preserve quality.** Define a regression set and compare answer quality, evidence coverage, tool selection, and token use. Do not remove an evidence check solely to lower latency.
7. **Implement and test.** Respect async boundaries, provider limits, rate limits, ordering requirements, cancellation, and error isolation. Keep concurrency bounded with semaphores or equivalent controls where appropriate.
8. **Re-measure.** Compare equivalent workloads and report sample size, p50/p95, TTFT, calls, tokens, error rate, and quality. If instrumentation is absent, implement targeted instrumentation or state that impact is unverified.

## Rules of optimization
- Parallelize only calls that are truly independent and safe to run concurrently.
- Avoid unbounded `gather`, fan-out, retries, recursive planning, or agent loops.
- Set per-call and end-to-end deadlines; retries must be bounded and respect `Retry-After` when available.
- Avoid caching personalized portfolio answers without a correct user/portfolio/version key and privacy review.
- Cache only when staleness is acceptable; specify TTL and invalidation behavior.
- Consider streaming only if the client and response contract support it; distinguish TTFT from completion latency.
- Prefer smaller context and better retrieval over blindly switching to a smaller model.
- Do not claim a speedup without comparable measurements. Token savings can be offset by extra agents, tools, and hooks.

## Token-efficient context use
- Inspect the hot path and relevant timing logs only.
- Ask for a short plan with no more than a few candidate optimizations; test the highest-confidence one first.
- Do not load full logs, all prompts, or the whole repository unless evidence requires it.

## Required checks
- Quality/regression evaluation, p50/p95 timing, call count, token count, and error rate where measurable.
- Timeout/cancellation behavior, rate-limit handling, cache isolation/invalidation, and bounded concurrency.
- No lost citations, omitted required evidence, or cross-user cache leakage.
- Confirm tests actually executed and distinguish local benchmark results from production observations.

## Output format
1. Latency budget and call graph
2. Measured bottleneck(s) and confidence
3. Ranked optimizations with trade-offs
4. Minimal implemented change
5. Before/after latency, token, call-count, quality, and error metrics
6. Unmeasured effects and rollback plan
