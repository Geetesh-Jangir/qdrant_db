"""Publisher allowlist used after Google News RSS (source URL / label)."""

from news_pipeline.config import PUBLISHERS
from news_pipeline.sources.google_news import _match_publisher
from news_pipeline.textutil import host_matches


def test_publisher_domains_are_unique():
    domains = [p.domain for p in PUBLISHERS]
    assert len(domains) == len(set(domains))


def test_match_via_source_url_and_google_label():
    cases = [
        ("https://www.moneycontrol.com/", "Moneycontrol", "https://news.google.com/...", "moneycontrol.com"),
        ("", "Livemint", "https://news.google.com/...", "livemint.com"),
        ("https://www.zeebiz.com/", "Zee Business", "https://news.google.com/...", "zeebiz.com"),
        ("https://www.fortuneindia.com/x", "Fortune India", "https://news.google.com/...", "fortuneindia.com"),
        ("", "Reuters", "https://news.google.com/...", "reuters.com"),
        ("https://www.sebi.gov.in/", "SEBI", "https://news.google.com/...", "sebi.gov.in"),
    ]
    for source_url, source_name, link, expected in cases:
        assert _match_publisher(source_url, source_name, link) == expected


def test_host_matches_subdomain():
    assert host_matches("www.economictimes.indiatimes.com", "economictimes.indiatimes.com")
    assert (
        _match_publisher(
            "https://economictimes.indiatimes.com/markets",
            "Economic Times",
            "https://economictimes.indiatimes.com/a",
        )
        == "economictimes.indiatimes.com"
    )