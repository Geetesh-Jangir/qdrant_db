"""Parse NSE FII/DII JSON without network."""

from ai_insight.data.base import FlowLeg
from ai_insight.data.nse_fii_dii import _bucket, _leg


def test_leg_parses_nse_row():
    row = {
        "buyValue": "18339.57",
        "sellValue": "12603.02",
        "netValue": "5736.55",
        "category": "FII/FPI",
        "date": "13-Nov-2026",
    }
    leg = _leg(row)
    assert leg is not None
    assert leg.buy_inr_crore == 18339.57
    assert leg.net_inr_crore == 5736.55


def test_bucket_fii_dii():
    assert _bucket("FII/FPI") == "fii"
    assert _bucket("DII") == "dii"