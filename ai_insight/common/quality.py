"""Draft, verify, optional revise, optional re-verify, then the code validator."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from ai_insight.common.evidence import EvidenceArticle, format_evidence_block
from ai_insight.common.runner import DryRunHalt, RunContext
from ai_insight.common.schemas import Envelope
from ai_insight.common.prose_guard import scrub_refusal_prose
from ai_insight.common.validate import ValidationResult, validate_insight

VERIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": True,
    "required": ["supported", "unsupported_claims", "too_long", "unclear_phrases", "revised"],
    "properties": {
        "supported": {"type": "boolean"},
        "unsupported_claims": {"type": "array", "items": {"type": "string"}},
        "too_long": {"type": "boolean"},
        "unclear_phrases": {"type": "array", "items": {"type": "string"}},
        "revised": {"type": "object"},
    },
}


@dataclass
class LoopSpec:
    system_draft: str
    system_verify: str
    system_revise: str
    user_draft: str
    draft_schema: dict[str, Any]
    compose: Callable[[dict[str, Any]], Envelope]
    max_tokens: int = 900
    verify_schema: dict[str, Any] = field(default_factory=lambda: VERIFY_SCHEMA)


@dataclass
class LoopResult:
    envelope: Envelope
    status: str
    draft: dict[str, Any] | None = None
    verdict: dict[str, Any] | None = None
    revised: dict[str, Any] | None = None
    problems: list[str] = field(default_factory=list)


def run_quality_loop(
    ctx: RunContext,
    *,
    spec: LoopSpec,
    facts: dict[str, Any],
    evidence: list[EvidenceArticle],
) -> LoopResult:
    """DryRunHalt propagates from the first model call so the runner can print the prompt."""
    evidence_text = format_evidence_block(evidence)
    draft = _data(ctx.llm(spec.system_draft, spec.user_draft, spec.draft_schema, spec.max_tokens, kind="draft"))
    final = draft
    revised = None
    verdict: dict[str, Any] | None = None
    problems: list[str] = []
    if ctx.config.llm_verify:
        verdict = _data(
            ctx.llm(
                spec.system_verify,
                _verify_user(spec.user_draft, draft, facts),
                spec.verify_schema,
                spec.max_tokens,
                kind="verify",
            )
        )
        problems = _problems(verdict)
        if problems:
            revised = _data(
                ctx.llm(
                    spec.system_revise,
                    _verify_user(spec.user_draft, draft, facts) + "\n\nVERIFIER\n" + _dump(verdict),
                    spec.draft_schema,
                    spec.max_tokens,
                    kind="revise",
                )
            )
            final = revised
            if ctx.config.reverify:
                verdict = _data(
                    ctx.llm(
                        spec.system_verify,
                        _verify_user(spec.user_draft, revised, facts),
                        spec.verify_schema,
                        spec.max_tokens,
                        kind="verify",
                    )
                )
                problems = _problems(verdict)
    envelope = spec.compose(final)
    if envelope.body:
        envelope.body = scrub_refusal_prose(envelope.body)
    if problems:
        envelope.status = "degraded"
        envelope.meta.validation = {"ok": False, "errors": problems, "verdict": verdict}
        return LoopResult(envelope, "degraded", draft, verdict, revised, problems)
    if envelope.status == "ok":
        result = validate_insight(envelope, evidence_text)
        envelope.meta.validation = _validation_payload(result)
        if not result.ok:
            envelope.status = "degraded"
            return LoopResult(envelope, "degraded", draft, verdict, revised, list(result.errors))
    return LoopResult(envelope, envelope.status, draft, verdict, revised, [])


def _problems(verdict: dict[str, Any]) -> list[str]:
    found: list[str] = []
    if not verdict.get("supported", False):
        found.append("not supported")
    if verdict.get("too_long"):
        found.append("too long")
    phrases = verdict.get("unclear_phrases") or []
    if phrases:
        found.append("unclear: " + "; ".join(str(item) for item in phrases))
    claims = verdict.get("unsupported_claims") or []
    if claims and verdict.get("supported") is False:
        found.extend(str(item) for item in claims)
    return found


def _verify_user(user: str, draft: dict[str, Any], facts: dict[str, Any]) -> str:
    return user + "\n\nDRAFT\n" + _dump(draft) + "\n\nFACTS\n" + _dump(facts)


def _data(result: Any) -> dict[str, Any]:
    data = result.data if hasattr(result, "data") else result
    if not isinstance(data, dict):
        raise ValueError("model reply was not an object")
    return data


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _validation_payload(result: ValidationResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "errors": list(result.errors),
        "checks": [{"name": check.name, "passed": check.passed, "detail": check.detail} for check in result.checks],
    }


# Imported so callers and tests can catch the same halt the runner uses.
_ = DryRunHalt
