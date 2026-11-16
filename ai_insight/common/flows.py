"""Readers for the FII/DII history file. Insight packages share this, not each other."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class FlowDay:
    date: str
    fii_net: float
    dii_net: float
    fii: dict[str, Any]
    dii: dict[str, Any]
    source: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "fii": self.fii,
            "dii": self.dii,
            "source": self.source,
        }


def load_flow_history(path: Path) -> list[FlowDay]:
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    days: list[FlowDay] = []
    for row in raw if isinstance(raw, list) else []:
        if not isinstance(row, dict):
            continue
        fii = row.get("fii") or {}
        dii = row.get("dii") or {}
        days.append(
            FlowDay(
                date=str(row.get("date") or ""),
                fii_net=_num(fii.get("net")),
                dii_net=_num(dii.get("net")),
                fii=dict(fii),
                dii=dict(dii),
                source=str(row.get("source") or ""),
            )
        )
    days.sort(key=lambda item: item.date)
    return [item for item in days if item.date]


def cumulative(days: list[FlowDay], n: int, key: str = "fii_net") -> float | None:
    """Sum of the last n days present, including the last row. None when empty."""
    if n < 1 or not days:
        return None
    window = days[-n:]
    return round(sum(float(getattr(day, key)) for day in window), 2)


def history_path(data_dir: Path) -> Path:
    return Path(data_dir) / "_data" / "fii_dii_history.json"


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
