"""Print full ask pipeline outputs for manual/CI review."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from unittest.mock import patch

from news_rag.ask_eval import HARD_ASK_CASES, validate_ask_response
from news_rag.answer import generate_answer
from news_rag.retrieve import retrieve_for_question

_DUMMY = [0.0] * 384


def run(q: str) -> dict:
    with patch("news_rag.retrieve.embed_query", return_value=_DUMMY):
        with patch("news_rag.embed.embed_query", return_value=_DUMMY):
            with patch("news_rag.retrieve.QdrantReader") as m:
                m.return_value.query_vector.return_value = []
                m.return_value.scroll_filtered.return_value = []
                parsed, articles = retrieve_for_question(q)
                return generate_answer(parsed, articles)


def main() -> None:
    for case in [c for c in HARD_ASK_CASES if not c.routing_only]:
        out = run(case.question)
        fails = validate_ask_response(case, out)
        print("=" * 72)
        print(case.id)
        print("Q:", case.question[:100])
        print("intent:", out.get("intent"), "source:", out.get("insight_source"))
        print("VALID:", "OK" if not fails else fails)
        print("SUMMARY:", (out.get("insight_summary") or "")[:500])
        bullets = out.get("insight_bullets") or []
        if bullets:
            print("BULLETS:", bullets[:4])
        if out.get("impact_rankings"):
            funds = (out.get("impact_rankings") or {}).get("funds") or []
            for f in funds[:3]:
                print("  RANK:", f.get("rank"), f.get("fund_name"), f.get("sector_weight_pct"))
        if out.get("impact_breakdown"):
            bd = out["impact_breakdown"]
            print("  FUND:", bd.get("fund_name"), bd.get("isin"))
            for s in (bd.get("touched_sectors") or [])[:4]:
                print("  SECTOR:", s)
    print("=" * 72)


if __name__ == "__main__":
    main()
