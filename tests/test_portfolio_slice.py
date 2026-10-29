"""A holdings question gets every weight, and a smaller cache does not stand in for it."""

from news_rag.insight.capabilities.executor import widen_portfolio_args
from news_rag.insight.grounding import cores_in_text, strip_ungrounded_numbers
from news_rag.insight.memory.evidence import clear_conversation, recall_wider_portfolio, remember_slice


def test_each_holding_asks_for_the_full_list_not_one_name():
    args = widen_portfolio_args(
        "also show me the weightage of each holding",
        {"sections": ["holdings"], "top_n": 1},
    )
    assert args["top_n"] == 50
    named = widen_portfolio_args(
        "show the top 5 holdings",
        {"sections": ["holdings"], "top_n": 5},
    )
    assert named["top_n"] == 5


def test_a_rounded_holding_weight_is_kept():
    allowed = cores_in_text("8.31298508039499")
    text = "ICICI Bank Limited at **8.31%** of the fund."
    assert "8.31%" in strip_ungrounded_numbers(text, allowed)


def test_a_shorter_holdings_cache_does_not_answer_a_longer_request():
    clear_conversation("conv-weights")
    rows = [{"name": f"Stock {i}", "weight_pct": i} for i in range(1, 11)]
    remember_slice(
        "conv-weights",
        "Invesco India Largecap Fund",
        "get_portfolio_data",
        {"sections": ["holdings"], "top_n": 10},
        {"holdings": rows, "sectors": []},
        turn=1,
    )
    assert recall_wider_portfolio(
        "conv-weights",
        "Invesco India Largecap Fund",
        {"sections": ["holdings"], "top_n": 50},
    ) is None
    smaller = recall_wider_portfolio(
        "conv-weights",
        "Invesco India Largecap Fund",
        {"sections": ["holdings"], "top_n": 3},
    )
    assert smaller is not None
    assert len(smaller["holdings"]) == 3
    clear_conversation("conv-weights")
