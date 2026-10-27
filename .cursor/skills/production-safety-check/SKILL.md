---
name: production-safety-check
description: >-
  Reviews changed Python/FastAPI code in this financial-news application for
  validation, auth, secrets, query safety, timeouts, retries, sensitive logs,
  cleanup, failure handling, and deterministic financial calculations. Use when
  the user asks for a production safety check, a security review of a diff, or
  a pre-release check of changed API or fund-calculation code.
---

# Production Safety Check

Review only the changed code and its necessary dependencies. Check input validation, API compatibility, authentication and authorization, secrets, database query safety, timeouts, retries, logging of sensitive data, resource cleanup and failure handling. Check financial calculations for deterministic correctness where relevant. Do not expose secrets or change files during review unless explicitly asked. Report concrete findings, severity and recommended fixes.

## Steps

1. Read the current diff. Open a dependency only when a changed line calls it and the finding depends on that call.
2. Check each changed path for:
   - input validation and API compatibility
   - authentication and authorization
   - secrets in code, config, logs, or responses
   - database query safety
   - timeouts, retries, resource cleanup, and failure handling
   - logging of sensitive data
   - financial calculations: same inputs must produce the same result, with no silent rounding or unit change
3. Do not print secret values. Refer to the file and line, and say what kind of secret is present.
4. Do not edit files unless the user explicitly asks for a fix.

## Report

```markdown
## Findings

### Critical
- `path:line` — Confirmed: what is unsafe. Fix: the smallest change.

### Should fix
- `path:line` — Confirmed or Possible: what is unsafe. Fix: the smallest change.

### Notes
- `path:line` — Possible: a risk that is not a proven defect.

No findings — say so if the diff has none.
```
