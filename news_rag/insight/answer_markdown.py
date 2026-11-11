"""Repair composer markdown the chat renderer otherwise drops or glues together."""

from __future__ import annotations

import re

_BLANK_RUN = re.compile(r"\n{3,}")


def _balance_bold(text: str) -> str:
    if text.count("**") % 2:
        return text + "**"
    return text


def _split_cells(line: str) -> list[str]:
    raw = line.strip()
    if raw.startswith("|"):
        raw = raw[1:]
    if raw.endswith("|"):
        raw = raw[:-1]
    return [cell.strip().replace("|", "/") for cell in raw.split("|")]


def _is_rule(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.count("|") >= 2


def normalize_answer_markdown(text: str) -> str:
    src = (text or "").replace("\r\n", "\n").strip()
    if not src:
        return ""
    lines = src.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not _is_table_line(line):
            if line.strip().startswith("#") and out and out[-1].strip():
                out.append("")
            out.append(line.rstrip())
            i += 1
            continue
        if out and out[-1].strip():
            out.append("")
        block: list[str] = []
        while i < len(lines) and _is_table_line(lines[i]):
            block.append(lines[i])
            i += 1
        rows = [_split_cells(row) for row in block]
        width = max(len(row) for row in rows)
        padded = [row + ["—"] * (width - len(row)) for row in rows]
        if len(padded) == 1 or not _is_rule(padded[1] if len(padded) > 1 else []):
            rule = ["---"] * width
            padded.insert(1, rule)
        for row in padded:
            out.append("| " + " | ".join(row[:width]) + " |")
        out.append("")
    joined = _BLANK_RUN.sub("\n\n", "\n".join(out)).strip()
    return _balance_bold(joined)
