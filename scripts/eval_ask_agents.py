#!/usr/bin/env python3
"""Deprecated — use scripts/eval_ask_v2.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    script = _ROOT / "scripts" / "eval_ask_v2.py"
    return subprocess.call([sys.executable, str(script), "--mode", "v2", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
