#!/usr/bin/env python3
"""Patch investor guide docx with factual corrections."""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

DOCX = Path(__file__).resolve().parents[1] / "docs" / "SUM_CHATBOT_Ask_a_Question_Investor_Guide.docx"

REPLACEMENTS: list[tuple[str, str]] = [
    (
        "What is the 1-year return of HDFC Large Cap Fund?",
        "What is the 1-year return of Parag Parikh Flexi Cap Fund?",
    ),
    (
        "What are the 1-year and 3-year returns of HDFC Large Cap Fund?",
        "What are the 1-year and 3-year returns of Parag Parikh Flexi Cap Fund?",
    ),
    (
        "Simple questions: often around 8 seconds.",
        "Simple factual questions: server deadlines start at about 8 seconds, but end-to-end answers are often about 15–20 seconds because planning and data fetches run first.",
    ),
    (
        "asks you to load/sign in to your portfolio first.",
        "asks you to sign in to your portfolio first (for example: “Please sign in to see your own portfolio…”).",
    ),
    (
        "Personal portfolio figures cannot be supplied until it is loaded.",
        "Personal portfolio figures cannot be supplied until you are signed in.",
    ),
    (
        "Compare two named funds",
        "Compare two named funds (nicknames may map to the closest official scheme names)",
    ),
    (
        "Keep in mind: a comparison needs at least two fund names that the system can identify.",
        "Keep in mind: a comparison needs at least two fund names the system can identify; informal names (for example “SBI Bluechip”) may be mapped to the nearest official scheme.",
    ),
    (
        "Why did Bandhan Large Cap fall over the last month?",
        "Why did Bandhan Large Cap move over the last month?",
    ),
    (
        "What are the RupeeStop rating and risk label for Kotak Emerging Equity?",
        "What are the RupeeStop rating and risk label for Kotak Emerging Equity Fund?",
    ),
]

EXTRA_NOTE = (
    "Name resolution: use the full official scheme name when you can. "
    "Informal names may map to the nearest catalogue scheme."
)


def _merge_text_runs(xml: str) -> str:
    return re.sub(r"<[^>]+>", "", xml.replace("</w:p>", "\n"))


def _fuzzy_pattern(phrase: str) -> str:
    """Match phrase when Word splits it across multiple w:t runs."""
    parts: list[str] = []
    for ch in phrase:
        parts.append(re.escape(ch))
        parts.append(r"(?:<[^>]+>)*")
    return "".join(parts)


def _replace_in_xml(xml: str, old: str, new: str) -> tuple[str, bool]:
    if old in xml:
        return xml.replace(old, new), True
    pat = _fuzzy_pattern(old)
    m = re.search(pat, xml, flags=re.DOTALL)
    if not m:
        return xml, False
    repl = (
        "<w:r><w:t xml:space=\"preserve\">"
        + new
        + "</w:t></w:r>"
    )
    return xml[: m.start()] + repl + xml[m.end() :], True


def main() -> int:
    if not DOCX.is_file():
        print(f"missing {DOCX}", file=sys.stderr)
        return 1
    with zipfile.ZipFile(DOCX, "r") as zin:
        parts = {name: zin.read(name) for name in zin.namelist()}
    xml = parts["word/document.xml"].decode("utf-8")
    changed = 0
    for old, new in REPLACEMENTS:
        xml, ok = _replace_in_xml(xml, old, new)
        if ok:
            changed += 1
    merged = _merge_text_runs(xml)
    if EXTRA_NOTE[:40] not in merged and "</w:body>" in xml:
        note_xml = (
            "<w:p><w:r><w:t xml:space=\"preserve\">"
            + EXTRA_NOTE
            + "</w:t></w:r></w:p>"
        )
        xml = xml.replace("</w:body>", note_xml + "</w:body>", 1)
        changed += 1
    parts["word/document.xml"] = xml.encode("utf-8")
    tmp = DOCX.with_suffix(".patched.docx")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in parts.items():
            zout.writestr(name, data)
    tmp.replace(DOCX)
    print(f"patched {DOCX} ({changed} replacement passes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())