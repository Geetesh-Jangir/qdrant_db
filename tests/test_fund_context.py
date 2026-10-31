from news_rag.insight.memory.fund_context import primary_fund_isin, primary_fund_name


def test_primary_fund_isin_from_memory_frame():
    memory = {
        "frame": {
            "subjects": [
                {"id": "INF209K01LV0", "name": "ABSL Banking & PSU Debt Fund - Growth", "role": "primary"},
            ]
        }
    }
    assert primary_fund_isin(memory) == "INF209K01LV0"
    assert "ABSL" in primary_fund_name(memory)
