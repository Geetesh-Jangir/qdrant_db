"""Prose checks. Numbers, direction, and causes have to be backed by the envelope."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ai_insight.common.config import load_config
from ai_insight.common.narrative import repetition_score
from ai_insight.common.schemas import Envelope, numeric_leaves

_BANNED = ("should buy", "will rise", "guaranteed", "target price")
_UP = {"rose", "bought", "up"}
_DOWN = {"fell", "sold", "down"}
_CAUSE = re.compile(r"\b(?:because|after|amid|as|on|due to)\b", re.I)
_CLUSTER = re.compile(r"\bc\d+\b")
_ORDINAL = re.compile(r"\b(\d+)(?:st|nd|rd|th)\b", re.I)
_DATE = re.compile(
    r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b",
    re.I,
)
_INDEX = re.compile(r"\b(?:nifty\s*50|bank\s*nifty|sensex)\b", re.I)
_NUMBER = re.compile(
    r"(?P<sign>[+-])?\s*(?:₹|rs\.?\s*)?(?P<num>\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?P<suffix>\s*%|\s*[kK])?",
    re.I,
)
_RS = re.compile(r"\bRs\.", re.I)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ValidationResult:
    ok: bool
    checks: list[CheckResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def validate_insight(envelope: Envelope, evidence_text: str = "") -> ValidationResult:
    text = f"{envelope.headline}\n{envelope.body}"
    checks = [
        _headline(envelope.headline),
        _body(envelope.body),
        _numbers(text, envelope, evidence_text),
        _direction(envelope.body, envelope),
        _clusters(text, envelope),
        _sources(envelope),
        _banned(text),
        _hedge(envelope.body),
        _move_size(envelope),
        _repetition(envelope),
    ]
    errors = [f"{check.name}: {check.detail}" for check in checks if not check.passed]
    return ValidationResult(ok=not errors, checks=checks, errors=errors)


def _headline(headline: str) -> CheckResult:
    count = len(headline.split())
    return CheckResult("headline_len", count <= 12, f"{count} words")


def _body(body: str) -> CheckResult:
    cfg = load_config()
    sentence_count = len(_sentences(body))
    word_count = len(body.split())
    ok = sentence_count <= cfg.body_max_sentences and word_count <= cfg.body_max_words
    return CheckResult("body_len", ok, f"{sentence_count} sentences, {word_count} words")


def _numbers(text: str, envelope: Envelope, evidence_text: str = "") -> CheckResult:
    allowed = _allowed_numbers(envelope, evidence_text)
    missing: list[str] = []
    for raw, value, tol in _claims(text):
        if not any(abs(abs(number) - value) <= tol for number in allowed):
            missing.append(raw)
    if missing:
        return CheckResult("numbers", False, "not in facts or chips: " + ", ".join(missing))
    return CheckResult("numbers", True, f"{len(_claims(text))} numbers checked")


def _direction(body: str, envelope: Envelope) -> CheckResult:
    signed = [number for _path, number in numeric_leaves(envelope.facts)]
    signed.extend(_signed_from_text(_blob(envelope)))
    for sentence in _sentences(body):
        words = set(re.findall(r"[a-z]+", sentence.lower()))
        want = 1 if words & _UP else -1 if words & _DOWN else 0
        if words & _UP and words & _DOWN:
            return CheckResult("direction", False, "sentence uses both up and down words")
        if want == 0:
            continue
        for _raw, value, tol in _claims(sentence):
            matches = [number for number in signed if abs(abs(number) - value) <= tol]
            if matches and not any((number > 0) == (want > 0) and number != 0 for number in matches):
                return CheckResult("direction", False, f"{value:g} disagrees with the direction word")
    return CheckResult("direction", True, "")


def _clusters(text: str, envelope: Envelope) -> CheckResult:
    cited = set(_CLUSTER.findall(text))
    known = set(envelope.meta.cluster_ids)
    missing = sorted(cited - known)
    if missing:
        return CheckResult("cluster_ids", False, "unknown " + ", ".join(missing))
    return CheckResult("cluster_ids", True, f"{len(cited)} cited")


def _sources(envelope: Envelope) -> CheckResult:
    count = len(envelope.sources)
    states_cause = bool(_CAUSE.search(envelope.body))
    if count > 3:
        return CheckResult("sources", False, f"{count} sources")
    if states_cause and not 1 <= count <= 3:
        return CheckResult("sources", False, "body states a cause but has no source")
    return CheckResult("sources", True, f"{count} sources")


def _hedge(body: str) -> CheckResult:
    """A hard 'because' needs a hedge. 'after' alone is allowed."""
    if not re.search(r"\bbecause\b", body or "", re.I):
        return CheckResult("hedge", True, "")
    if re.search(r"\b(?:appears|linked|coincides|tied|suggests|points to)\b", body or "", re.I):
        return CheckResult("hedge", True, "")
    return CheckResult("hedge", False, "because is not hedged")


def _move_size(envelope: Envelope) -> CheckResult:
    raw = envelope.facts.get("nifty_change_pct")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return CheckResult("move_size", True, "")
    text = f"{envelope.headline} {envelope.body}".lower()
    magnitude = abs(float(raw))
    if "sharply" in text and magnitude <= 1:
        return CheckResult("move_size", False, "sharply does not match the move")
    if ("range-bound" in text or "range bound" in text) and magnitude >= 0.25:
        return CheckResult("move_size", False, "range-bound does not match the move")
    if "edged" in text and not (0.25 <= magnitude <= 1):
        return CheckResult("move_size", False, "edged does not match the move")
    return CheckResult("move_size", True, "")


def _repetition(envelope: Envelope) -> CheckResult:
    beats = envelope.facts.get("narrative_beats")
    if not isinstance(beats, dict):
        return CheckResult("repetition", True, "")
    score = repetition_score(beats)
    ok = score < 0.55
    return CheckResult("repetition", ok, f"overlap {score:.2f}")


def _banned(text: str) -> CheckResult:
    lowered = text.lower()
    found = [phrase for phrase in _BANNED if phrase in lowered]
    if found:
        return CheckResult("banned", False, ", ".join(found))
    return CheckResult("banned", True, "")


def _sentences(body: str) -> list[str]:
    shielded = _RS.sub("Rs<dot>", body or "")
    shielded = re.sub(r"(\d)\.(\d)", r"\1<dot>\2", shielded)
    parts = re.split(r"[.!?]+", shielded)
    return [part.replace("<dot>", ".").strip() for part in parts if part.strip()]


def _claims(text: str) -> list[tuple[str, float, float]]:
    cleaned = _INDEX.sub(" ", _DATE.sub(" ", text or ""))
    masked = _ORDINAL.sub(" ", cleaned)
    found: list[tuple[str, float, float]] = []
    for match in _NUMBER.finditer(masked):
        raw_num = match.group("num")
        suffix = (match.group("suffix") or "").strip().lower()
        number = float(raw_num.replace(",", ""))
        if suffix == "k":
            decimals = len(raw_num.split(".")[1]) if "." in raw_num else 0
            number *= 1000
            precision = (10 ** -decimals) * 1000 if decimals else 1000
        elif suffix == "%":
            decimals = len(raw_num.split(".")[1]) if "." in raw_num else 0
            precision = 10 ** -decimals if decimals else 1
        else:
            decimals = len(raw_num.split(".")[1]) if "." in raw_num else 0
            precision = 10 ** -decimals if decimals else 1
        found.append((match.group(0).strip(), number, precision / 2))
    for match in _ORDINAL.finditer(cleaned):
        found.append((match.group(0), float(match.group(1)), 0.5))
    return found


def _allowed_numbers(envelope: Envelope, evidence_text: str = "") -> list[float]:
    numbers = [value for _path, value in numeric_leaves(envelope.facts)]
    numbers.extend(_signed_from_text(_blob(envelope)))
    numbers.extend(_signed_from_text(evidence_text))
    for chip in envelope.chips:
        numbers.extend(value for _raw, value, _tol in _claims(f"{chip.label} {chip.value}"))
    return numbers


def _blob(envelope: Envelope) -> str:
    chunks: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, str):
            chunks.append(value)
        elif isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(envelope.facts)
    return "\n".join(chunks)


def _signed_from_text(text: str) -> list[float]:
    signed: list[float] = []
    for match in _NUMBER.finditer(text or ""):
        raw_num = match.group("num")
        suffix = (match.group("suffix") or "").strip().lower()
        number = float(raw_num.replace(",", ""))
        if suffix == "k":
            number *= 1000
        sign = -1 if match.group("sign") == "-" else 1
        signed.append(sign * number)
    return signed
