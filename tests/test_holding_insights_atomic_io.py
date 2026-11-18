import json
from pathlib import Path

from ai_insight.holding_insights.atomic_io import atomic_write_json


def test_atomic_write_json_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "progress.json"
    atomic_write_json(path, {"done": 1, "total": 99})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data == {"done": 1, "total": 99}