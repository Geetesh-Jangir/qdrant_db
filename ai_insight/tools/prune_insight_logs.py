"""Drop superseded insight run logs; keep the latest trace folder per insight per day."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

from ai_insight.common.config import load_config

_FLAT = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})_\d{6}_(?P<run_id>[a-f0-9]{6})\.(log|prompt\.txt)$")


def prune_insight_logs(log_dir: Path, *, execute: bool = False) -> dict[str, int]:
    root = Path(log_dir)
    removed_dirs = 0
    removed_files = 0
    kept_run_ids: set[tuple[str, str, str]] = set()

    for day_dir in sorted(root.iterdir()):
        if not day_dir.is_dir() or len(day_dir.name) != 10 or day_dir.name[4] != "-":
            continue
        trading_date = day_dir.name
        for insight_dir in day_dir.iterdir():
            if not insight_dir.is_dir():
                continue
            insight_id = insight_dir.name
            runs = [item for item in insight_dir.iterdir() if item.is_dir()]
            if not runs:
                continue
            runs.sort(key=lambda path: (path.stat().st_mtime, path.name), reverse=True)
            keep = runs[0]
            kept_run_ids.add((trading_date, insight_id, keep.name))
            for old in runs[1:]:
                if execute:
                    shutil.rmtree(old, ignore_errors=True)
                removed_dirs += 1

    for trading_date, insight_id, run_id in kept_run_ids:
        artifact = root / trading_date / insight_id / run_id
        if (artifact / "llm_draft_request.json").is_file():
            flat_dir = root / insight_id
            for path in flat_dir.glob(f"*_{run_id}.prompt.txt"):
                if execute:
                    path.unlink(missing_ok=True)
                removed_files += 1

    for flat_dir in root.iterdir():
        if not flat_dir.is_dir() or len(flat_dir.name) == 10:
            continue
        insight_id = flat_dir.name
        for path in list(flat_dir.glob("*")):
            if not path.is_file():
                continue
            if path.suffix not in {".log", ".txt"}:
                continue
            match = _FLAT.match(path.name)
            if match:
                key = (match.group("date"), insight_id, match.group("run_id"))
                if key in kept_run_ids:
                    continue
            if execute:
                path.unlink(missing_ok=True)
            removed_files += 1

    return {"removed_run_dirs": removed_dirs, "removed_flat_files": removed_files, "kept_runs": len(kept_run_ids)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ai_insight.tools.prune_insight_logs")
    parser.add_argument("--execute", action="store_true", help="Delete files (default is a dry-run count only).")
    args = parser.parse_args(argv)
    cfg = load_config()
    stats = prune_insight_logs(cfg.log_dir, execute=args.execute)
    mode = "removed" if args.execute else "would_remove"
    print(
        f"{mode} run_dirs={stats['removed_run_dirs']} flat_files={stats['removed_flat_files']} "
        f"kept_runs={stats['kept_runs']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())