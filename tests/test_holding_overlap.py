from news_rag.fund_search import build_holding_overlap
from news_rag.insight.contracts import AnswerMode, ExecutionPlan
from news_rag.insight.evidence_pack import build_evidence_pack, render_data_only_template


def _detail(name: str, holdings: dict) -> dict:
    return {
        "fund_name": name,
        "fund_short_name": name,
        "holdings": holdings,
        "nav": 10,
        "aum": 100,
        "category": "Large Cap",
        "expense_ratio": {"regular": 1.0},
        "exit_load_summary": "This fund has no exit load.",
    }


def test_overlap_uses_full_stock_list_and_skips_cash():
    left = _detail(
        "Fund A",
        {
            "Reliance Industries Limited": {"percentage": 8.2, "industry": "Oil"},
            "TREPS / Reverse Repo Investments": {"percentage": 4.0, "industry": "Cash"},
            "Small Name": {"percentage": 0.2, "industry": "Equity"},
        },
    )
    right = _detail(
        "Fund B",
        {
            "Reliance Industries Ltd": {"percentage": 5.5, "industry": "Oil"},
            "TREPS / Reverse Repo Investments": {"percentage": 3.0, "industry": "Cash"},
            "Other Co": {"percentage": 2.0, "industry": "Equity"},
        },
    )
    overlap = build_holding_overlap([left, right])
    assert overlap["overlap_count"] == 1
    assert overlap["rows"][0]["stock"].startswith("Reliance")
    assert overlap["rows"][0]["weights"]["Fund A"] == 8.2
    assert overlap["rows"][0]["weights"]["Fund B"] == 5.5


def test_no_overlap_message_and_overlap_table():
    plan = ExecutionPlan(intent="compare", answer_mode=AnswerMode.DATA_ONLY, funds=["Fund A", "Fund B"])
    empty = build_evidence_pack(
        plan,
        [{
            "tool": "compare_funds",
            "ok": True,
            "data": {"holding_overlap": {"fund_names": ["Fund A", "Fund B"], "overlap_count": 0, "rows": []}, "fund_briefs": []},
        }],
        [],
    )
    text = render_data_only_template(empty, plan)
    assert text is not None
    assert "no overlapping stock holding" in text

    present = build_evidence_pack(
        plan,
        [{
            "tool": "compare_funds",
            "ok": True,
            "data": {
                "holding_overlap": {
                    "fund_names": ["Fund A", "Fund B"],
                    "overlap_count": 1,
                    "rows": [{"stock": "Reliance Industries", "weights": {"Fund A": 8.2, "Fund B": 5.5}}],
                },
                "fund_briefs": [
                    {
                        "fund_name": "Fund A",
                        "nav": 56.98,
                        "aum": 1000,
                        "expense_ratio": 1.25,
                        "category": "Large Cap",
                        "top_sector": "Banks (30.08%)",
                        "exit_load_summary": "This fund has no exit load.",
                        "returns": {"1Y": 12.5, "3Y": 8.1},
                    },
                    {
                        "fund_name": "Fund B",
                        "nav": 100,
                        "aum": 2000,
                        "expense_ratio": 1.5,
                        "category": "Large Cap",
                        "top_sector": "Banks (22.00%)",
                        "exit_load_summary": "Exit load is 1% if you leave within 1 year.",
                        "returns": {"1Y": 9.0},
                    },
                ],
            },
        }],
        [],
    )
    table = render_data_only_template(present, plan)
    assert table is not None
    assert "Top sector" in table
    assert "Banks (30.08%)" in table
    assert "### Historical returns" in table
    assert "12.50%" in table
    assert "Reliance Industries" in table
    assert "8.20%" in table
    assert "5.50%" in table
