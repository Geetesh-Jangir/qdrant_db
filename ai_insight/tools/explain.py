"""Print one run's decision trace and the files that support it."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_insight.common.config import load_config


def explain(insight_id: str, trading_date: str, run_id: str = "", *, log_dir: Path | None = None) -> str:
    root = Path(log_dir) if log_dir is not None else load_config().log_dir
    day = root / trading_date / insight_id
    if run_id:
        folder = day / run_id
    else:
        folders = sorted(path for path in day.glob("*") if path.is_dir()) if day.is_dir() else []
        folder = folders[-1] if folders else day
    if not folder.is_dir():
        return f"No run folder for {insight_id} on {trading_date}."
    parts = [f"# {insight_id} {trading_date} {folder.name}", ""]
    trace = folder / "decision_trace.md"
    if trace.is_file():
        parts.append(trace.read_text(encoding="utf-8"))
    for name in ("window.json", "retrieval.json", "scores.json", "validation.json", "envelope.json"):
        path = folder / name
        if not path.is_file():
            continue
        parts.append(f"## {name}")
        parts.append(_short(path))
    evidence = folder / "evidence_articles.json"
    if evidence.is_file():
        rows = json.loads(evidence.read_text(encoding="utf-8"))
        parts.append("## evidence")
        for row in rows if isinstance(rows, list) else []:
            parts.append(f"- {row.get('cluster_id')} | {row.get('title')} | {row.get('url')}")
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ai_insight.tools.explain")
    parser.add_argument("--insight", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--run", default="")
    args = parser.parse_args(argv)
    print(explain(args.insight, args.date, args.run))
    return 0


def _short(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text if len(text) <= 4000 else text[:4000] + "\n..."


if __name__ == "__main__":
    raise SystemExit(main())
