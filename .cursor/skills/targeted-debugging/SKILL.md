---
name: targeted-debugging
description: >-
  Diagnoses one specific bug by tracing its call path, applying the smallest
  fix, and running a focused regression test. Use when debugging a failure,
  an error, a wrong result, or a broken behavior.
---

# Targeted Debugging

Diagnose one specific bug by inspecting the error, tracing the relevant call path, identifying the root cause, making the smallest fix and running a focused regression test. Do not refactor unrelated code, reread unrelated files, or repeat failed approaches without new evidence. Never claim a test passed unless it was executed successfully. Return root cause, changed files, test results and remaining uncertainty.

## Steps

1. State the one bug. Ignore adjacent issues.
2. Read the error, failing assertion, or wrong output. Search for the symbol it names before opening a file.
3. Trace only the call path that produces that result: entry, the function that fails, and the data it uses.
4. Name the root cause in one sentence. If two causes remain, inspect the one observation that would separate them.
5. Change only the lines required to fix that cause.
6. Run the narrowest test that covers the bug. If it fails, use the new output to choose a different check. Do not rerun the same approach.

## Report

```markdown
## Root cause
One sentence: what failed, and why.

## Changed files
- `path` — what changed

## Test results
- `command` — pass or fail, with the assertion or error if it failed
- Not run — name any check that was not executed

## Remaining uncertainty
What is still unverified, or "none" if the focused test covers the bug.
```
