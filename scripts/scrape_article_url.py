"""CLI: scrape one URL with news_pipeline.scrape.article_url.scrape_article_url."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from news_pipeline.scrape.article_url import ScrapeArticleError, scrape_article_url


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape one news article URL (pipeline scraper).")
    parser.add_argument("url", help="Publisher HTTPS URL or news.google.com link")
    parser.add_argument("--title", default="", help="Fallback title if body is short")
    parser.add_argument("--snippet", default="", help="Fallback snippet if body is short")
    parser.add_argument("--json", action="store_true", help="Print full result as JSON")
    parser.add_argument("--chars", type=int, default=800, help="Max chars to print when not --json")
    parser.add_argument("--raise-on-thin", action="store_true", help="Exit 1 on extract_thin / short body")
    args = parser.parse_args()

    try:
        result = scrape_article_url(
            args.url,
            title_fallback=args.title,
            snippet_fallback=args.snippet,
            raise_on_thin=args.raise_on_thin,
        )
    except ScrapeArticleError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        if args.json:
            print(json.dumps(exc.record, indent=2, ensure_ascii=False))
        return 1
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    status = result.get("status") or "ok"
    title = result.get("title") or "(no title)"
    text = (result.get("text") or "").strip()
    print(f"status={status} chars={len(text)}")
    print(f"title={title}")
    if result.get("date"):
        print(f"date={result['date']}")
    if result.get("error"):
        print(f"note={result['error']}")
    preview = text[: args.chars]
    if len(text) > args.chars:
        preview += "..."
    print("---")
    print(preview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
