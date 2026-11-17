from ai_insight.api import _holding_job_payload


def test_holding_job_payload_shape():
    class Job:
        job_id = "abc"
        status = "done"
        started_at = 1.0
        finished_at = 2.0
        limit = 5
        progress = {"done": 5, "total": 5}
        result = {
            "insights": [{"stock_id": "X"}],
            "insufficient": [{"stock_name": "Y", "reason": "no_news_after_filter"}],
            "counts": {"ok": 1, "insufficient": 1},
            "generated_on": "2025-01-01",
        }

    payload = _holding_job_payload(Job())
    assert payload["insights"][0]["stock_id"] == "X"
    assert payload["insufficient"][0]["reason"] == "no_news_after_filter"
    assert payload["counts"]["ok"] == 1


def test_holding_job_payload_running_empty():
    class Job:
        job_id = "run1"
        status = "running"
        started_at = 1.0
        finished_at = None
        limit = 3
        progress = {"done": 1, "total": 3}
        result = None

    payload = _holding_job_payload(Job())
    assert payload["insights"] == []
    assert payload["insufficient"] == []