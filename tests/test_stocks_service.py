import pandas as pd


def test_get_stock_profile_includes_one_year_return(monkeypatch):
    closes = [100.0 + i * 0.05 for i in range(260)]
    hist = pd.DataFrame(
        {
            "Close": closes,
            "Low": closes,
            "High": closes,
        }
    )

    class FakeTicker:
        fast_info = type("FI", (), {"year_high": 120.0, "year_low": 90.0})()

        def history(self, period=None):
            return hist

    import historical_data.stocks_service as svc

    monkeypatch.setattr(svc, "yf", type("YF", (), {"Ticker": lambda _t, *_a, **_k: FakeTicker()})())
    monkeypatch.setattr(svc, "_STOCK_CACHE", {})
    monkeypatch.setattr(svc, "_CACHE_TIMESTAMP", {})

    profile = svc.get_stock_profile("HDFC Bank")
    assert profile is not None
    assert profile.get("return_1y") is not None
    assert profile["return_1y"] == round(((closes[-1] - closes[-252]) / closes[-252]) * 100.0, 2)
