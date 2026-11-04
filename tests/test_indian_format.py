from news_rag.indian_format import (
    format_inr,
    format_indian_amount,
    normalize_rupee_commas_in_text,
)


def test_format_indian_amount_lakh():
    assert format_indian_amount(100_000) == "1,00,000"
    assert format_indian_amount(786_928.88) == "7,86,928.88"
    assert format_indian_amount(3_805_248.45) == "38,05,248.45"


def test_format_inr_symbol():
    assert format_inr(408_251) == "₹4,08,251"
    assert format_inr(-99995) == "-₹99,995"


def test_normalize_western_rupee_in_prose():
    raw = "current value ₹786,928, invested ₹408,251"
    out = normalize_rupee_commas_in_text(raw)
    assert "₹7,86,928" in out
    assert "₹4,08,251" in out
    assert "786,928" not in out


def test_skips_below_lakh_unless_already_rupee():
    text = "NAV ₹59.75"
    assert normalize_rupee_commas_in_text(text) == text
