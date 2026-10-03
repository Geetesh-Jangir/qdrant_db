"""Smoke checks for /api/ask — uses news_rag.ask_eval.HARD_ASK_CASES."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_rag.ask_eval import HARD_ASK_CASES, validate_ask_response

BASE = "http://127.0.0.1:8080/api/ask"


@dataclass
class Row:
    case_id: str
    ok: bool
    detail: str


def main() -> int:
    rows: list[Row] = []
    cases = [c for c in HARD_ASK_CASES if not c.routing_only]
    with httpx.Client(timeout=120.0) as client:
        for case in cases:
            try:
                r = client.post(BASE, json={"question": case.question})
                if r.status_code != 200:
                    rows.append(Row(case.id, False, f"HTTP {r.status_code}: {r.text[:200]}"))
                    continue
                fails = validate_ask_response(case, r.json())
                if fails:
                    rows.append(Row(case.id, False, "; ".join(fails)))
                else:
                    data = r.json()
                    preview = (data.get("insight_summary") or "")[:120]
                    rows.append(
                        Row(
                            case.id,
                            True,
                            f"intent={data.get('intent')} src={data.get('insight_source')} | {preview}",
                        )
                    )
            except Exception as exc:
                rows.append(Row(case.id, False, str(exc)))

    print(json.dumps([{"id": r.case_id, "ok": r.ok, "detail": r.detail} for r in rows], indent=2))
    failed = sum(1 for r in rows if not r.ok)
    print(f"\n{len(rows) - failed}/{len(rows)} passed", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
