"""One-off probe: list Gemini models and test generateContent (uses .env GEMINI_API_KEY)."""

from __future__ import annotations

import httpx

from news_rag.config import get_settings


def main() -> None:
    settings = get_settings()
    key = (settings.gemini_api_key or "").strip().strip('"')
    if not key:
        raise SystemExit("GEMINI_API_KEY not set")
    headers = {"x-goog-api-key": key}
    base = settings.gemini_base_url.rstrip("/")
    r = httpx.get(f"{base}/models", headers=headers, params={"pageSize": 50}, timeout=30)
    print("list_models status", r.status_code)
    if r.status_code != 200:
        print(r.text[:1000])
        return
    names = [m.get("name", "") for m in r.json().get("models", [])]
    for name in sorted(names):
        if "flash" in name.lower():
            print(name)
    model = settings.gemini_model
    url = f"{base}/models/{model}:generateContent"
    r2 = httpx.post(
        url,
        headers={**headers, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": "Say hi in one word."}]}]},
        timeout=60,
    )
    print("generate", model, "status", r2.status_code)
    print(r2.text[:800])


if __name__ == "__main__":
    main()
