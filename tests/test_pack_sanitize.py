from news_rag.insight.contracts import EvidencePack
from news_rag.insight.pack_sanitize import sanitize_data_pack_for_composer


def test_compact_strips_contribution_from_data_attribution():
    pack = EvidencePack(
        data_pack={
            "fund:HDFC": {
                "attribution": {
                    "detractors": [
                        {
                            "name": "Titan",
                            "weight_pct": 5.07,
                            "return_pct": -10.77,
                            "contribution_pct": -0.55,
                        }
                    ],
                    "contributors": [],
                }
            }
        },
        performance_digest={
            "top_detractors": [
                {"name": "Titan", "weight_pct": 5.07, "return_pct": -10.77, "contribution_pct": -0.55}
            ]
        },
    )
    compact = pack.compact()
    detr = compact["DATA"]["fund:HDFC"]["attribution"]["detractors"][0]
    assert "contribution_pct" not in detr
    assert detr["weight_pct"] == 5.07
    assert "holding_contribution_pp_internal" in compact["PERFORMANCE"]
    assert compact["PERFORMANCE"]["top_detractors"][0].get("contribution_pct") is None


def test_sanitize_data_pack_moves_pp_to_internal():
    data, internal = sanitize_data_pack_for_composer(
        {
            "fund:x": {
                "attribution": {
                    "detractors": [{"name": "A", "weight_pct": 1.0, "return_pct": -2.0, "contribution_pct": -0.02}],
                    "contributors": [],
                    "rows": [],
                }
            }
        }
    )
    assert "contribution_pct" not in data["fund:x"]["attribution"]["detractors"][0]
    assert internal["funds"][0]["detractors"][0]["contribution_pp"] == -0.02
