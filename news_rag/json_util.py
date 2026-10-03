"""JSON helpers for API payloads that may include numpy/pandas scalars."""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any


def _json_default(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    if hasattr(value, "tolist") and callable(value.tolist):
        try:
            return value.tolist()
        except (TypeError, ValueError):
            pass
    return str(value)


def safe_json_dumps(obj: Any, *, limit: int | None = None) -> str:
    text = json.dumps(obj, ensure_ascii=False, default=_json_default)
    if limit is not None and len(text) > limit:
        return text[:limit]
    return text
