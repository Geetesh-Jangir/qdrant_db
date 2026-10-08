from news_pipeline.config import Settings
from news_pipeline.error_summary import summarize_errors


def test_google_and_jev_errors_are_split_with_entities_and_dates():
    settings = Settings()
    settings.news_date_range = "5/10/2026-7/10/2026"
    summary = summarize_errors(
        [
            {
                "source": "google_news",
                "stage": "fetch_google_news",
                "error": "429",
                "entities": ["HDFC Bank", "Macro - Gold"],
                "dates": ["2026-10-05", "2026-10-06"],
            },
            {
                "source": "jev",
                "stage": "jev_title_screen",
                "name": "Macro - Nifty 50",
                "error": "timeout",
                "dates": ["2026-10-05", "2026-10-06"],
            },
            {
                "source": "jev",
                "stage": "jev_article_scores",
                "entities": ["HDFC Bank"],
                "published_at": "2026-10-06T12:00:00Z",
                "error": "Jev returned 500",
            },
        ],
        settings=settings,
    )
    assert summary["google_news"]["count"] == 1
    assert summary["google_news"]["entities"] == ["HDFC Bank", "Macro - Gold"]
    assert summary["google_news"]["dates"] == ["2026-10-05", "2026-10-06"]
    assert summary["jev"]["count"] == 2
    assert "Macro - Nifty 50" in summary["jev"]["entities"]
    assert "HDFC Bank" in summary["jev"]["entities"]
