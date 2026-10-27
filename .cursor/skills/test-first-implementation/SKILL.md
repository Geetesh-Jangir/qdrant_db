---
name: test-first-implementation
description: >-
  Defines acceptance criteria, inspects existing tests and interfaces, then
  implements the smallest change with focused tests. Use when adding a feature,
  fixing a bug, or changing behavior that should be covered by tests.
---

# Test-First Implementation

Define acceptance criteria and inspect existing tests and interfaces before coding. For bug fixes, write a regression test that reproduces the failure when practical. For features, add focused tests for expected behavior and important edge cases. Implement the smallest complete change, run targeted tests, and report actual results. Avoid unrelated refactoring and unnecessary dependencies.

## Steps

1. Write the acceptance criteria: the observable result, and the edge cases that matter.
2. Search existing tests and the public interface the change must fit. Reuse that style. Do not open unrelated modules.
3. Bug fix: add a regression test that fails on the current code when practical, then make the smallest change that makes it pass.
4. Feature: add focused tests for the expected behavior and the important edge cases, then implement only what those tests require.
5. Run those tests. Do not claim a pass unless the command finished successfully.
6. Skip a new dependency or a refactor that the acceptance criteria do not need.

## Report

```markdown
## Acceptance criteria
- Expected result
- Edge cases covered

## Tests
- `path` — `test_symbol` — what it checks

## Changed files
- `path` — what changed

## Test results
- `command` — pass or fail, with the assertion or error if it failed
- Not run — name any check that was not executed
```
