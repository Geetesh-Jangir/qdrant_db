import json
import time
from pathlib import Path

import requests

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
OUT = Path(__file__).resolve().parent / "gdelt_hdfc_bank_limited_sample.json"

last_request_time = 0.0


def query_gdelt(params, *, retries: int = 4):
    global last_request_time
    last_error = None
    for attempt in range(retries):
        elapsed = time.monotonic() - last_request_time
        if elapsed < 5:
            time.sleep(5 - elapsed)
        response = requests.get(GDELT_URL, params=params, timeout=60)
        last_request_time = time.monotonic()
        if response.status_code == 429:
            last_error = response
            time.sleep(15 * (attempt + 1))
            continue
        response.raise_for_status()
        try:
            return response.json(), response.status_code, None
        except ValueError:
            raise RuntimeError(f"GDELT did not return JSON: {response.text[:500]}")
    if last_error is not None:
        return None, last_error.status_code, last_error.text[:2000]
    raise RuntimeError("GDELT request failed")


params = {
    "query": '"HDFC Bank Limited"',
    "mode": "artlist",
    "format": "json",
    "maxrecords": 250,
    "startdatetime": "20260914000000",
    "enddatetime": "20261016235959",
    "sort": "datedesc",
}

data, status, err_text = query_gdelt(params)
if data is not None:
    payload = {
        "ok": True,
        "http_status": status,
        "query_params": params,
        "article_count": len(data.get("articles", [])),
        "response": data,
    }
else:
    payload = {
        "ok": False,
        "http_status": status,
        "query_params": params,
        "article_count": 0,
        "error": "GDELT rate limited (429 Too Many Requests). Retry later.",
        "response_body_preview": err_text,
        "response": {"articles": []},
    }

OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("Articles:", payload["article_count"])
print("ok:", payload["ok"])
print("Saved:", OUT)
