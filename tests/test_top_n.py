from news_rag.insight.top_n import top_n_from_question


def test_top_five_sectors():
    assert top_n_from_question("top 5 sectors of axis", item="sectors") == 5


def test_top_six_word():
    assert top_n_from_question("top six sectors of hdfc", item="sectors") == 6


def test_top_sectors_default_three():
    assert top_n_from_question("what are the top sectors of axis", item="sectors") == 3


def test_top_sector_singular():
    assert top_n_from_question("top sector of axis large cap", item="sectors") == 1
