---
name: ai-security-review
description: Review AI applications for prompt injection, unsafe tool execution, data leakage, authorization gaps, secret exposure, insecure retrieval, and LLM-specific failure modes. Use before deploying agent, RAG, portfolio-data, or external-content changes.
---

# AI Security Review

## Objective
Identify exploitable or high-impact security risks in a FastAPI financial-information chatbot. Treat user input, news articles, retrieved chunks, model output, and tool output as untrusted unless validated.

## Trigger when
- Adding tools, agents, external scraping, document ingestion, retrieval, model providers, or portfolio-aware features.
- Changing auth, user/portfolio filters, logs, caching, secrets, or API permissions.
- Reviewing a release or investigating suspicious output/tool behavior.

## Bounded workflow
1. **Map the trust boundaries.** Inspect only the relevant endpoint, tool registry, retrieval filters, data access, prompt assembly, settings, logging, and tests. Identify untrusted inputs and privileged operations.
2. **Check authorization first.** Verify access is enforced in backend code and database filters, not merely in prompts. Ensure portfolio/user identifiers cannot be supplied to access another user's records.
3. **Inspect prompt-injection paths.** Treat retrieved news and user documents as data, not instructions. Check whether external text can alter tool selection, reveal system prompts/secrets, or trigger unauthorized actions.
4. **Review tool capabilities.** Use least privilege, strict input schemas, allowlisted operations, bounded arguments, timeouts, and explicit confirmation for consequential side effects. Avoid arbitrary shell, SQL, filesystem, or URL access driven by model output.
5. **Validate model and provider output.** Parse structured outputs, reject invalid tool arguments, limit response size, and handle refusal/error states. Do not rely on the LLM to enforce authorization or financial calculations.
6. **Check data exposure.** Review logs, traces, prompts, caches, error messages, vector payloads, backups, and test fixtures for credentials, portfolio data, or personal data. Verify cache keys isolate users and portfolio versions.
7. **Threat-test safely.** Add tests for prompt injection, cross-user access, malformed arguments, malicious URLs/articles, secret exfiltration attempts, oversized payloads, and upstream failures. Use local mocks; do not attack production systems.
8. **Prioritize and remediate.** Report severity, exploit path, evidence, fix, and regression test. Do not make broad security claims without examining the relevant code.

## Financial-domain safeguards
- Separate educational/informational explanations from personalized investment recommendations according to product policy and applicable requirements.
- Do not fabricate NAV, performance, holdings, market prices, or source citations.
- Preserve evidence provenance and uncertainty. A retrieved article alone does not prove causation or justify a trade recommendation.
- Prevent cross-user retrieval, caching, logging, and tracing of investor-specific context.

## Token/context efficiency
- Focus on changed files and direct trust boundaries first.
- Avoid printing secrets or raw sensitive payloads in findings; redact evidence.
- Do not add security libraries or infrastructure without identifying a specific risk and compatibility need.

## Required checks
- Authorization and user/portfolio isolation tests.
- Prompt-injection and untrusted-content handling tests.
- Tool schema/allowlist, timeout, payload-size, and error handling.
- Secret scanning/config review and safe logging/cache behavior.
- Severity-ranked findings with evidence; state what was not checked.

## Output format
1. Scope and trust boundaries reviewed
2. Findings ranked Critical/High/Medium/Low with evidence and impact
3. Exploit preconditions and affected components
4. Minimal remediation and regression tests
5. Residual risks and areas not reviewed
