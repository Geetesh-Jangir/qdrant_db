---
name: minimal-diff-review
description: >-
  Reviews the current Git diff for correctness, interfaces, callers, error
  handling, tests, accidental changes, and unnecessary abstractions. Use when
  the user asks for a code review, a diff review, or a check of uncommitted
  changes.
---

# Minimal Diff Review

Review the current Git diff first. Check correctness, changed interfaces, affected callers, error handling, tests, accidental changes and unnecessary abstractions. Inspect surrounding code only when needed to validate a finding. Do not modify files during review unless explicitly asked to fix an issue. Report findings by severity, with file and line references, and distinguish confirmed defects from possible risks.

## Steps

1. Read `git diff` (staged and unstaged). Review only those hunks.
2. For each hunk, check correctness, changed interfaces, affected callers, error handling, tests, accidental edits, and unnecessary abstractions.
3. Open surrounding code only to confirm or reject a finding. Do not tour unrelated files.
4. Do not edit files unless the user explicitly asks to fix an issue.

## Report

```markdown
## Findings

### Critical
- `path:line` — Confirmed: what is wrong.

### Should fix
- `path:line` — Confirmed or Possible: what is wrong, and what would confirm it.

### Notes
- `path:line` — Possible: a risk that is not a proven defect.

## Tests
What the diff covers, or the missing case.

No findings — say so if the diff has none.
```
