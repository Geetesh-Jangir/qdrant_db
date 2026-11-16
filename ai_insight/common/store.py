"""JSON files under data/ai_insights/<insight_id>/<YYYY-MM-DD>.json. Writes are atomic."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai_insight.common.config import load_config
from ai_insight.common.schemas import Envelope, InsightBundle

_ID = "abcdefghijklmnopqrstuvwxyz0123456789_"


def save(envelope: Envelope, *, root: Path | None = None, live: bool = False) -> Path:
    path = _file(envelope.insight_id, envelope.trading_date, root, live=live)
    _dump(path, envelope.model_dump(mode="json"))
    return path


def load(insight_id: str, trading_date: str, *, root: Path | None = None, live: bool = False) -> Envelope | None:
    path = _file(insight_id, trading_date, root, live=live)
    if not path.is_file():
        return None
    return Envelope.model_validate(json.loads(path.read_text(encoding="utf-8")))


@dataclass
class LoadedEnvelope:
    envelope: Envelope | None
    stale: bool = False
    stale_reason: str = ""


def load_best(insight_id: str, trading_date: str, *, root: Path | None = None) -> Envelope | None:
    """Newest envelope for the day (scheduled or live)."""
    return load_best_detail(insight_id, trading_date, root=root).envelope


def load_best_detail(insight_id: str, trading_date: str, *, root: Path | None = None) -> LoadedEnvelope:
    """Return the newest saved envelope for the day (scheduled vs live), never an older ok fallback."""
    scheduled = load(insight_id, trading_date, root=root, live=False)
    live_file = load(insight_id, trading_date, root=root, live=True)
    candidates = [item for item in (scheduled, live_file) if item is not None]
    if not candidates:
        return LoadedEnvelope(None)
    chosen = max(candidates, key=lambda item: item.as_of_ist)
    return LoadedEnvelope(chosen, stale=False, stale_reason="")


def save_bundle(bundle: InsightBundle, *, root: Path | None = None, live: bool = False) -> Path:
    path = _file(bundle.insight_id, bundle.trading_date, root, live=live)
    _dump(path, bundle.model_dump(mode="json"))
    return path


def load_bundle(insight_id: str, trading_date: str, *, root: Path | None = None, live: bool = False) -> InsightBundle | None:
    path = _file(insight_id, trading_date, root, live=live)
    if not path.is_file():
        return None
    return InsightBundle.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_json(path: Path, payload: Any) -> Path:
    _dump(path, payload)
    return path


def load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def exists(insight_id: str, trading_date: str, *, status: str | None = None, root: Path | None = None) -> bool:
    loaded = load(insight_id, trading_date, root=root)
    if loaded is None:
        return False
    return status is None or loaded.status == status


def bundle_exists(insight_id: str, trading_date: str, *, status: str | None = None, root: Path | None = None) -> bool:
    loaded = load_bundle(insight_id, trading_date, root=root)
    if loaded is None:
        return False
    return status is None or loaded.status == status


def list_dates(insight_id: str, *, root: Path | None = None) -> list[str]:
    folder = _root(root) / _check_id(insight_id)
    if not folder.is_dir():
        return []
    found: set[str] = set()
    for path in folder.glob("*.json"):
        stem = path.stem
        if stem.endswith(".live"):
            stem = stem[: -len(".live")]
        if _is_date(stem):
            found.add(stem)
    return sorted(found)


def latest(insight_id: str, *, status: str | None = None, root: Path | None = None) -> Envelope | None:
    for trading_date in reversed(list_dates(insight_id, root=root)):
        loaded = load(insight_id, trading_date, root=root)
        if loaded is None:
            continue
        if status is None or loaded.status == status:
            return loaded
    return None


def _file(insight_id: str, trading_date: str, root: Path | None, *, live: bool = False) -> Path:
    if not _is_date(trading_date):
        raise ValueError(f"trading_date must be YYYY-MM-DD, got {trading_date!r}")
    name = f"{trading_date}.live.json" if live else f"{trading_date}.json"
    return _root(root) / _check_id(insight_id) / name


def _dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        _replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _root(root: Path | None) -> Path:
    return Path(root) if root is not None else load_config().data_dir


def _check_id(insight_id: str) -> str:
    if not insight_id or any(ch not in _ID for ch in insight_id):
        raise ValueError(f"insight_id is not a safe folder name: {insight_id!r}")
    return insight_id


def _is_date(value: str) -> bool:
    if len(value) != 10 or value[4] != "-" or value[7] != "-":
        return False
    year, month, day = value.split("-")
    return year.isdigit() and month.isdigit() and day.isdigit()


def _replace(src: Path, dst: Path) -> None:
    delay = 0.05
    for _ in range(5):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            time.sleep(delay)
            delay *= 2
    os.replace(src, dst)
