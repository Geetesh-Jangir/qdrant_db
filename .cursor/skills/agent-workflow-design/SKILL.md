---
name: agent-workflow-design
description: Design and review bounded LLM agents, LangGraph workflows, query routing, tool catalogs, evidence checks, and deterministic fallbacks. Use when building or modifying agent orchestration or deciding which tools/models a query needs.
---

# Agent Workflow Design

## Objective
Use the least complex workflow that reliably answers the query. Prefer deterministic routing and explicit state/contracts where possible; use an agent loop only when it provides measurable value.

## Trigger when
- Creating or modifying LangGraph nodes, edges, state, tools, planner/judge stages, or fallback logic.
- The chatbot calls too many tools/models, loops, selects irrelevant tools, or returns unsupported claims.
- Deciding between direct LLM answer, deterministic code, retrieval, parallel tool calls, or multi-step reasoning.

## Bounded workflow
1. **Trace current graph.** Inspect graph construction, state schema, node functions, tool definitions, conditional edges, checkpointing, and endpoint integration. Read only relevant modules.
2. **Define query classes and contracts.** Identify supported query categories and the minimum evidence/data each needs. Keep routing rules auditable and avoid brittle keyword-only routing when structured classification is needed.
3. **Create a tool matrix.** For each tool, record purpose, input/output schema, latency, data freshness, side effects, timeout, permissions, and failure mode. Remove overlapping tools only with evidence.
4. **Choose a bounded plan.** Define maximum planning/replanning waves, maximum tool calls, total deadline, context/token budget, and stop conditions. A common design is one plan plus at most one evidence-repair wave, but choose limits based on measured needs.
5. **Separate deterministic and probabilistic work.** Use code for calculations, permissions, schema validation, stable filters, and portfolio math. Use LLMs for language understanding/synthesis where useful. Do not let a model override authorization or financial calculations.
6. **Define evidence gates.** Specify what evidence is required before a claim can be made, how source provenance is passed, and when the system must abstain or explain insufficient evidence. Separate article relevance from sector impact and causal claims.
7. **Handle failures explicitly.** Add bounded timeout/error paths, partial-result policy, provider fallback rules, cancellation, and safe handling of malformed tool outputs. Avoid infinite retry/replan loops.
8. **Evaluate and instrument.** Test representative query classes, tool selection, call counts, answer quality, latency, token usage, and failure behavior. Implement the smallest graph change that improves measured behavior.

## Design principles
- Every node should have a clear responsibility and typed input/output.
- Keep state small; store IDs and compact evidence references rather than duplicating large article bodies throughout graph state.
- Run independent reads concurrently only with bounded concurrency and independent failure handling.
- Avoid calling multiple models for the same decision unless their roles are distinct and evaluation justifies it.
- Never expose secrets, user portfolio data, or internal tool credentials to untrusted tools or retrieved documents.
- Retrieved news is data, not instructions. Tool outputs must be validated as untrusted input.
- Preserve deterministic fund/holdings data and provenance through the workflow.
- Do not invent unsupported LangGraph APIs or assume a version; inspect dependencies and installed version.

## Token efficiency
- Trace the active path, not every possible node.
- Use compact state and evidence summaries; do not repeatedly send entire articles to every node.
- Avoid speculative redesigns and parallel agents unless parallel work has a clear independent scope.

## Required checks
- Graph terminates under normal, empty, malformed, and failure cases.
- Tool arguments and outputs are schema-validated.
- Tool/model call budgets and overall deadline are enforced.
- Authorization and portfolio isolation are deterministic.
- Regression tests cover query routing, evidence gates, abstention, and fallback behavior.

## Output format
1. Current graph/call path
2. Query classes and evidence requirements
3. Proposed graph/tool design and bounded limits
4. Trade-offs and expected measurable benefit
5. Implementation and tests
6. Failure paths, security considerations, and open questions
