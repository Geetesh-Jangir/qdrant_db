"""Article text extraction via trafilatura, with a small HTML fallback."""

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from trafilatura import extract_with_metadata

THIN_TEXT_CHARS = 120


def extract_article(html, url):
    doc = None
    try:
        doc = extract_with_metadata(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
            output_format="txt",
        )
    except Exception:
        doc = None

    text = ""
    title = None
    authors = []
    date = None
    sitename = None

    if doc is not None:
        text = (doc.raw_text or doc.text or "").strip()
        title = _clean(doc.title)
        authors = _authors(doc.author)
        date = _clean(doc.date)
        sitename = _clean(doc.sitename) or urlparse(url).netloc

    if len(text) < THIN_TEXT_CHARS:
        fallback = _meta_fallback(html, url)
        title = title or fallback["title"]
        authors = authors or fallback["authors"]
        date = date or fallback["date"]
        sitename = sitename or fallback["sitename"] or urlparse(url).netloc
        if len(fallback["text"]) > len(text):
            text = fallback["text"]

    return {
        "title": title,
        "authors": authors,
        "date": date,
        "sitename": sitename,
        "text": text or "",
        "thin": len(text) < THIN_TEXT_CHARS,
    }


def _meta_fallback(html, url):
    soup = BeautifulSoup(html, "lxml")
    title = _meta(soup, property="og:title") or _meta(soup, name="twitter:title")
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()
    article = soup.find("article")
    text = article.get_text("\n", strip=True) if article else (
        _meta(soup, property="og:description") or _meta(soup, name="description") or ""
    )
    return {
        "title": title,
        "authors": _authors(_meta(soup, name="author") or _meta(soup, property="author")),
        "date": _meta(soup, property="article:published_time") or _meta(soup, name="date"),
        "sitename": _meta(soup, property="og:site_name"),
        "text": text,
    }


def _authors(raw):
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return [part.strip() for part in re.split(r"[;|]| and ", str(raw)) if part.strip()]


def _clean(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _meta(soup, property=None, name=None):
    attrs = {"property": property} if property else {"name": name}
    tag = soup.find("meta", attrs=attrs)
    if tag and tag.get("content"):
        return tag["content"].strip()
    return None
