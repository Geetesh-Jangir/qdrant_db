"""Back-to-back Jev calls (title-screen shape) to verify API health."""

from __future__ import annotations

import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_pipeline.config import Settings
from news_pipeline.jev.client import JevClient, JevError, read_noul, title_questions
SAMPLE_TITLES = [
    "RBI holds repo rate steady at 6.5%",
    "Nifty 50 closes at record high on IT rally",
    "SEBI tightens disclosure norms for mutual funds",
    "HDFC Bank Q3 net profit rises 12% YoY",
    "Crude oil slips below $80 on demand worries",
    "Rupee weakens to 84 against US dollar",
    "Sensex gains 400 points; banking stocks lead",
    "Gold prices hit fresh high on safe-haven demand",
    "India CPI inflation eases to 4.8% in September",
    "FII selling continues for third straight session",
]


def main() -> int:
    settings = Settings()
    # Jev only — skip Qdrant requirement
    if not (settings.jev_base_url or "").strip() or not (settings.jev_api_key or "").strip():
        print("FAIL: set JEV_BASE_URL and JEV_API_KEY in .env")
        return 1

    entity = {
        "name": "Macro - Nifty 50",
        "type": "macro",
        "industry": "Macro",
        "aliases": [],
        "keywords": [],
    }
    n_calls = 20
    print(f"jev_url_host={settings.jev_base_url.split('/')[2] if '/' in settings.jev_base_url else settings.jev_base_url}")
    print(f"model={settings.jev_model} planned_calls={n_calls}")

    ok = 0
    fail = 0
    latencies: list[float] = []
    errors: list[str] = []

    with JevClient(settings) as client:
        for i in range(n_calls):
            title = SAMPLE_TITLES[i % len(SAMPLE_TITLES)]
            rows = [{"question_id": "t0", "title": title}]
            state = {
                "name": entity["name"],
                "type": entity["type"],
                "industry": entity["industry"],
                "aliases": entity["aliases"],
                "keywords": entity["keywords"],
            }
            t0 = time.perf_counter()
            try:
                answers = client.evaluate(
                    state,
                    title_questions(rows, entity),
                    stage="jev_stress_test",
                    detail=f"call={i + 1}",
                )
                score = read_noul(answers.get("t0"))
                elapsed = time.perf_counter() - t0
                latencies.append(elapsed)
                usage = client.last_call_usage()
                ok += 1
                print(
                    f"  [{i + 1:02d}] ok noul={score:.3f} "
                    f"sec={elapsed:.2f} in_tok={usage.get('input_tokens')} out_tok={usage.get('output_tokens')}"
                )
            except JevError as exc:
                fail += 1
                elapsed = time.perf_counter() - t0
                msg = str(exc)[:200]
                errors.append(msg)
                print(f"  [{i + 1:02d}] FAIL sec={elapsed:.2f} {msg}")

    print("---")
    if latencies:
        print(
            f"summary ok={ok} fail={fail} "
            f"latency_avg={sum(latencies) / len(latencies):.2f}s "
            f"min={min(latencies):.2f}s max={max(latencies):.2f}s"
        )
    else:
        print(f"summary ok={ok} fail={fail}")
    if errors:
        print("unique_errors:", list(dict.fromkeys(errors))[:5])
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
