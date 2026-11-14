"""MoSPI client cache, retries, derived YoY, and snapshot isolation. No live network."""

from __future__ import annotations

import json

import httpx

from ai_insight.data.macro_data import MospiClient, MospiError, fetch_gdp, fetch_wpi, get_macro_snapshot

def _sse(payload: dict) -> httpx.Response:
    body = "event: message\ndata: " + json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"structuredContent": payload}}) + "\n"
    return httpx.Response(200, text=body)


def _client(handler, tmp_path):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    return MospiClient(http, tmp_path, sleep=lambda _s: None)


def test_retries_500_then_reads_cache(tmp_path):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(500, text="no")
        return _sse({"data": [{"ok": 1}]})

    client = _client(handler, tmp_path)
    assert client.call("get_data", {"dataset": "CPI", "filters": {}})["data"] == [{"ok": 1}]
    assert calls["n"] == 3
    assert client.call("get_data", {"dataset": "CPI", "filters": {}})["data"] == [{"ok": 1}]
    assert calls["n"] == 3


def test_400_is_not_retried(tmp_path):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, text="bad")

    client = _client(handler, tmp_path)
    try:
        client.call("get_data", {"dataset": "CPI", "filters": {}})
    except MospiError as exc:
        assert exc.retryable is False
    else:
        raise AssertionError("expected MospiError")
    assert calls["n"] == 1


def test_wpi_yoy_is_derived(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        params = json.loads(request.content)["params"]
        args = params["arguments"]
        if params["name"] == "get_metadata":
            return _sse({"data": {"year": [{"year": 2026}], "month": [{"month_code": 9}]}})
        year = args["filters"]["year"]
        index = "110" if year == "2026" else "100"
        return _sse(
            {
                "data": [
                    {
                        "year": int(year),
                        "month": "September",
                        "major_group": "Wholesale Price Index",
                        "group": None,
                        "item": None,
                        "index_value": index,
                    }
                ]
            }
        )

    rows = fetch_wpi(_client(handler, tmp_path))
    assert rows[0].index_value == 110
    assert rows[0].inflation_rate_yoy == 10.0
    assert rows[0].yoy_derived is True


def test_gdp_yoy_uses_prior_fiscal_year(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        params = json.loads(request.content)["params"]
        args = params["arguments"]
        if params["name"] == "get_metadata":
            return _sse({"data": {"year": [{"year": "2025-26"}, {"year": "2024-25"}]}})
        return _sse(
            {
                "data": [
                    {
                        "indicator": "Gross Domestic Product",
                        "year": "2025-26",
                        "quarter": "Q1",
                        "current_price": "200",
                        "constant_price": "110",
                    },
                    {
                        "indicator": "Gross Domestic Product",
                        "year": "2024-25",
                        "quarter": "Q1",
                        "current_price": "180",
                        "constant_price": "100",
                    },
                ]
            }
        )

    rows = fetch_gdp(_client(handler, tmp_path))
    assert len(rows) == 1
    assert rows[0].growth_rate_yoy == 10.0


def test_snapshot_keeps_other_entities_when_one_fails(tmp_path, monkeypatch):
    import ai_insight.data.macro_data as mod

    monkeypatch.setattr(mod, "fetch_cpi", lambda client=None: (_ for _ in ()).throw(RuntimeError("cpi down")))
    monkeypatch.setattr(mod, "fetch_wpi", lambda client=None: [])
    monkeypatch.setattr(mod, "fetch_iip", lambda client=None: [])
    monkeypatch.setattr(mod, "fetch_gdp", lambda client=None: [])
    snap = get_macro_snapshot()
    assert snap.cpi == []
    assert any(item.startswith("cpi:") for item in snap.unavailable)
    assert any(item.startswith("bond_yields:") for item in snap.unavailable)
