"""URL canonicalization, time parsing, and title checks."""

from __future__ import annotations

import html
import re
import uuid
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_KEYS = {
    "fbclid",
    "gclid",
    "gclsrc",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "ocid",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None
    text = str(value).strip()
    try:
        parsed = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError):
        parsed = None
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def within_news_window(value: datetime | None, hours: int, now: datetime) -> bool:
    """Missing times stay in the pipeline until scrape can fill them."""
    if value is None:
        return True
    start = now - timedelta(hours=hours)
    end = now + timedelta(minutes=15)
    return start <= value <= end


def host_of(url: str) -> str:
    if not url:
        return ""
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def host_matches(host: str, domain: str) -> bool:
    if not host:
        return False
    return host == domain or host.endswith("." + domain)


def canonical_url(url: str) -> str:
    parsed = urlparse(url.strip())
    host = host_of(url)
    if host.startswith("m.") and host.count(".") >= 2:
        host = host[2:]
    if host.startswith("amp."):
        host = host[4:]
    query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in TRACKING_KEYS:
            continue
        query.append((key, value))
    path = parsed.path.rstrip("/") or "/"
    return urlunparse(("https", host, path, "", urlencode(query), ""))


def point_id_for_url(url: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, url))


def strip_html(value: str) -> str:
    text = html.unescape(_TAG_RE.sub(" ", value or ""))
    return _WS_RE.sub(" ", text).strip()


def is_english_title(title: str) -> bool:
    letters = [char for char in title if char.isalpha()]
    if not letters:
        return False
    latin = 0
    for char in letters:
        if ("A" <= char <= "Z") or ("a" <= char <= "z"):
            latin += 1
    return (latin / len(letters)) >= 0.8


def normalize_title(title: str) -> str:
    text = html.unescape(title or "").lower()
    text = re.sub(r"\s+[-|–—]\s+[^-|–—]+$", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def contains_phrase(text: str, phrase: str) -> bool:
    if not phrase:
        return False
    pattern = r"\b" + re.escape(phrase.strip()) + r"\b"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def embedding_text(title: str, body: str, char_limit: int) -> str:
    snippet = " ".join((body or "").split())[:char_limit]
    return f"{title.strip()}\n\n{snippet}".strip()


def truncate_words(text: str, word_limit: int) -> str:
    words = (text or "").split()
    if len(words) <= word_limit:
        return " ".join(words)
    return " ".join(words[:word_limit])
