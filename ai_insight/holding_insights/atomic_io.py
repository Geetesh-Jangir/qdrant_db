"""Atomic JSON file writes safe on Windows (polling readers + os.replace)."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_ACCESS_DENIED = frozenset({5, 13})  # WinError 5, EACCES


def atomic_write_json(
    path: Path,
    payload: dict[str, Any],
    *,
    indent: int | None = 2,
    retries: int = 8,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    text = json.dumps(payload, ensure_ascii=False, indent=indent)
    last_exc: OSError | None = None
    for attempt in range(retries):
        try:
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, path)
            return
        except OSError as exc:
            last_exc = exc
            code = getattr(exc, "winerror", None) or exc.errno
            if code not in _ACCESS_DENIED or attempt >= retries - 1:
                break
            time.sleep(0.02 * (attempt + 1))
        finally:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
    if last_exc is not None:
        raise last_exc