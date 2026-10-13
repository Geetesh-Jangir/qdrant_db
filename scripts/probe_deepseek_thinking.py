#!/usr/bin/env python3
"""Check whether the configured DeepSeek model spends tokens on reasoning, and whether
`thinking: disabled` is accepted. Sends two tiny requests to the DEEPSEEK_BASE_URL in .env."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_rag.config import get_settings


def main() -> int:
    s = get_settings()
    if not (s.deepseek_api_key or "").strip():
        print("DEEPSEEK_API_KEY not set")
        return 1
    url = s.deepseek_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": "Bearer " + s.deepseek_api_key}
    base = {
        "model": s.deepseek_model,
        "messages": [{"role": "user", "content": 'Return a JSON object {"a": 1, "b": "x"}'}],
        "max_tokens": 400,
        "response_format": {"type": "json_object"},
    }
    for label, extra in (("default", {}), ("thinking disabled", {"thinking": {"type": "disabled"}})):
        r = httpx.post(url, headers=headers, json={**base, **extra}, timeout=90)
        print("---", label, "http", r.status_code, "model", s.deepseek_model)
        try:
            d = r.json()
        except Exception:
            print(r.text[:300])
            continue
        if "choices" not in d:
            print(json.dumps(d)[:400])
            continue
        msg = d["choices"][0]["message"]
        print("finish", d["choices"][0].get("finish_reason"), "usage", d.get("usage"))
        print("content  ", repr(msg.get("content"))[:200])
        print("reasoning", repr(msg.get("reasoning_content"))[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
