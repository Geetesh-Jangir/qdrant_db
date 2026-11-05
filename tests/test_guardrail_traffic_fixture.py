import json
from pathlib import Path

import pytest

from news_rag.insight.guardrails import guard_reply

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "guardrail_traffic.json"


@pytest.mark.parametrize("row", json.loads(_FIXTURE.read_text(encoding="utf-8")))
def test_guardrail_traffic_fixture(row: dict) -> None:
    expect = row.get("expect")
    got = guard_reply(row["q"], portfolio_enabled=True)
    if expect is None:
        assert got is None, (row["q"], got)
    else:
        assert got is not None and got[0] == expect, (row["q"], got)
