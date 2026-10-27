---
name: llm-evaluation-testing
description: Build repeatable evaluations and regression tests for LLM answers, RAG retrieval, tool routing, sector impact classification, groundedness, latency, and token budgets. Use when changing prompts, models, tools, retrieval, or agent workflows.
---

# LLM Evaluation and Testing

## Objective
Make AI behavior measurable and reproducible. Separate deterministic software correctness from probabilistic answer quality.

## Trigger when
- Changing a model, system prompt, tool schema, router, retrieval pipeline, reranker, or output format.
- Investigating hallucinations, missed news, wrong sector mapping, bad citations, or inconsistent answers.
- Introducing caching, parallelism, model fallback, or a new agent step.

## Bounded workflow
1. **Identify the behavior contract.** Inspect the existing endpoint, prompt, response schema, tests, and callers. Capture the intended behavior and what must not change.
2. **Build a small stratified dataset.** Include common queries, multi-hop fund/news questions, ambiguous entities, stale/no news, conflicting sources, empty retrieval, malformed provider responses, and adversarial article text. Use synthetic or approved data; exclude secrets and personal investor data.
3. **Write deterministic tests first.** Test routing rules, schema validation, math, filters, tool arguments, permissions, timeout behavior, and citation structure without requiring a live LLM where possible.
4. **Define model-based rubrics.** Evaluate relevance, factual support, citation correctness, completeness, calibrated uncertainty, sector mapping, causal reasoning, and whether the response distinguishes correlation from causation. Do not use a judge model as unquestioned ground truth.
5. **Set baselines and thresholds.** Record model/version, prompt version, retrieval/index version, temperature/decoding settings, dataset version, and run date. Use human-reviewed labels for a representative subset.
6. **Run a controlled comparison.** Change one main variable at a time. Compare against baseline with the same cases and settings; account for stochastic variance where relevant.
7. **Inspect failures.** Group by root cause: retrieval miss, wrong metadata, router/tool selection, prompt ambiguity, unsupported inference, formatting, or provider failure. Add regression cases for confirmed bugs.
8. **Report limits.** Show sample size, aggregate and per-category results, representative failures, confidence/variance when meaningful, and tests not run. Avoid claiming statistically meaningful improvement from tiny samples.

## Mutual-fund/news evaluation cases
- Fund performance explanation for 1 week, 1 month, and 1 year with the correct period and evidence.
- News relevance versus actual causal/sector impact as separate judgments.
- Correct mapping of article → company/commodity/macro factor → sector → fund holdings, with evidence for each link.
- Contradictory news, stale stories, duplicate syndications, market-wide news, and no relevant evidence.
- Correct abstention when holdings or reliable sources are missing.
- Avoid fabricated NAV movements, prices, dates, holdings, or citations.
- Distinguish factual financial analysis from personalized investment advice; preserve required product safeguards.

## Efficiency requirements
- Start with a small smoke suite, then a broader fixed suite for material changes.
- Cache evaluation inputs/results only with explicit version keys; never let cached results mask prompt or model changes.
- Prefer deterministic mocks for unit tests and a bounded number of live model calls for integration tests.
- Keep raw investor data and sensitive provider payloads out of test fixtures unless approved and sanitized.

## Required checks
- Unit tests for deterministic behavior and schema contracts.
- Regression suite for relevant prompts/retrieval/tool changes.
- Grounding/citation checks and unsupported-claim checks.
- Latency, token, and tool-call budgets when performance is in scope.
- Reproducibility metadata and clear reporting of skipped tests/provider outages.

## Output format
1. Behavior under test and baseline
2. Dataset and rubric
3. Results by metric/category
4. Representative failures and root causes
5. Regressions added and tests run
6. Limitations, release threshold, and recommended next experiment
