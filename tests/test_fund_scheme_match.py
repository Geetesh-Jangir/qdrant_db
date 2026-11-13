"""AMC + distinctive token matching across the full catalog vocabulary."""

import pytest

from news_rag.fund_scheme_match import pick_best_matching_scheme, user_text_names_scheme


@pytest.mark.parametrize(
    "question, chosen, rejected",
    [
        (
            "tell me about the fund manager of kotak contra fund",
            "Kotak Contra Fund - Regular Plan - Growth",
            "Kotak Liquid Fund - Regular Plan - Growth",
        ),
        (
            "hdfc mid cap fund nav",
            "HDFC Mid Cap Fund - Regular Plan - Growth",
            "HDFC Liquid Fund - Growth",
        ),
        (
            "icici prudential liquid fund expense",
            "ICICI Prudential Liquid Fund - Growth",
            "ICICI Prudential India Opportunities Fund - Growth",
        ),
        (
            "sbi small cap fund returns",
            "SBI Small Cap Fund - Regular Plan - Growth",
            "SBI BlueChip Fund - Regular Plan - Growth",
        ),
        (
            "axis flexi cap fund",
            "Axis Flexi Cap Fund - Regular Plan - Growth",
            "Axis Liquid Fund - Regular Plan - Growth",
        ),
        (
            "nippon india power infra fund",
            "Nippon India Power & Infra Fund - Growth Option",
            "Nippon India Liquid Fund - Growth",
        ),
    ],
)
def test_amc_plus_style_disambiguates(question: str, chosen: str, rejected: str) -> None:
    assert user_text_names_scheme(question, chosen)
    assert not user_text_names_scheme(question, rejected)
    assert pick_best_matching_scheme(question, [rejected, chosen]) == chosen


def test_exit_load_minimum_variance_not_confused_by_minimum_word() -> None:
    q = "exit load on icici prudential minimum variance"
    target = "ICICI Prudential Equity Minimum Variance Fund - Regular Plan - Growth"
    assert user_text_names_scheme(q, target)
    assert not user_text_names_scheme("whats the minimum redemption period", target)


def test_amc_catalog_typo_still_names_scheme() -> None:
    assert user_text_names_scheme(
        "tell me how the tauras large cap fund is doing",
        "Taurus Large Cap Fund",
    )
