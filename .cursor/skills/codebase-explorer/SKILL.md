---
name: codebase-explorer
description: >-
  Maps only the files, entry points, callers, dependencies, data models, and
  tests relevant to a task. Use when exploring this codebase, tracing a flow,
  locating an implementation, or before changing unfamiliar code.
---

# Codebase Explorer

Find only files relevant to the requested task.

Trace the relevant entry point, callers, dependencies, data models and tests.

Use targeted search before opening large files.

Return a concise architecture map with file paths and relevant symbols.

Never dump entire files or explore unrelated modules without justification.

Recommend the next smallest useful investigation step.

## Search order

1. Search symbols, routes, and test names that match the task. Do not open a file until a search hit shows it matters.
2. Open only the matching line ranges. Stop when the entry point, its callers, its dependencies, the data models, and the tests are named.
3. Skip a module that does not appear in that chain. Name it only to say why it is out of scope.

## Architecture map

```markdown
## Architecture map
- Entry: `path` — `symbol`
- Callers: `path` — `symbol`
- Dependencies: `path` — `symbol`
- Data models: `path` — `symbol`
- Tests: `path` — `test_symbol`

## Next step
One smallest follow-up: the single file or symbol to open next, and why.
```
