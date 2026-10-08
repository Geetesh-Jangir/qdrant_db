"""HTTP fetch via impit (browser impersonation)."""

from __future__ import annotations

import http.cookiejar
import os
import threading
import time
from http.cookiejar import Cookie
from typing import Any
from urllib.parse import urlparse

from impit import Client

from lib.google_guard import (
    GoogleBlockedError,
    google_breaker,
    google_throttle,
    is_google_host,
    log_google_block,
    looks_like_google_block,
)

DEFAULT_TIMEOUT = 20
RETRY_STATUSES = {408, 425, 429, 500, 502, 503, 504}
_GOOGLE_NO_RETRY = {401, 403}
_RETRY_BROWSERS = ("chrome", "firefox", "safari")
_local = threading.local()


def _proxy() -> str | None:
    raw = (os.environ.get("GOOGLE_HTTP_PROXY") or os.environ.get("HTTP_PROXY") or "").strip()
    return raw or None


def _consent_jar() -> http.cookiejar.CookieJar:
    jar = http.cookiejar.CookieJar()
    jar.set_cookie(
        Cookie(
            0,
            "CONSENT",
            "YES+",
            None,
            False,
            ".google.com",
            True,
            True,
            "/",
            True,
            False,
            None,
            True,
            None,
            None,
            {},
        )
    )
    return jar


def make_session(browser: str = "chrome") -> Client:
    kwargs: dict[str, Any] = {
        "browser": browser,
        "timeout": DEFAULT_TIMEOUT,
        "follow_redirects": True,
        "cookie_jar": _consent_jar(),
    }
    proxy = _proxy()
    if proxy:
        kwargs["proxy"] = proxy
    return Client(**kwargs)


def thread_session() -> Client:
    session = getattr(_local, "session", None)
    if session is None:
        session = make_session()
        _local.session = session
    return session


def _retry_after_seconds(response: Any) -> float | None:
    try:
        raw = response.headers.get("Retry-After") or response.headers.get("retry-after")
    except Exception:
        raw = None
    if not raw:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _handle_google_response(response: Any, url: str) -> tuple[bool, str | None]:
    """Returns (is_block, error_message)."""
    final_url = str(getattr(response, "url", url) or url)
    body = response.text or ""
    if looks_like_google_block(response.status_code, final_url, body):
        log_google_block(response.status_code, url)
        google_breaker.record_block()
        if google_breaker.blocked():
            raise GoogleBlockedError("Google News blocked this IP (circuit open)")
        return True, f"google block {response.status_code} for url: {url}"
    google_breaker.record_success()
    return False, None


def fetch_url(session: Client, url: str, timeout=DEFAULT_TIMEOUT, referer=None, retries=2):
    """GET a URL. Returns (final_url, html, error)."""
    google_breaker.assert_allowed()
    last_error = None
    current = session
    google = is_google_host(url)
    for attempt in range(retries + 1):
        if attempt > 0 and not google:
            current = make_session(_RETRY_BROWSERS[(attempt - 1) % len(_RETRY_BROWSERS)])
        if google:
            google_throttle()
        headers = {"Referer": referer} if referer else None
        try:
            response = current.get(
                url,
                timeout=timeout,
                headers=headers,
            )
            if google:
                blocked, block_err = _handle_google_response(response, url)
                if blocked:
                    last_error = block_err
                    if response.status_code in _GOOGLE_NO_RETRY:
                        return None, None, last_error
                    if response.status_code == 429 and attempt < retries:
                        delay = _retry_after_seconds(response) or 30.0
                        time.sleep(delay)
                        continue
                    return None, None, last_error
            elif response.status_code >= 400:
                last_error = f"{response.status_code} for url: {url}"
                if response.status_code in RETRY_STATUSES and attempt < retries:
                    _backoff(attempt)
                    continue
                return None, None, last_error

            if response.status_code >= 400:
                last_error = f"{response.status_code} for url: {url}"
                return None, None, last_error

            text = response.text or ""
            if not text.strip():
                last_error = "empty page"
                if attempt < retries and not google:
                    _backoff(attempt)
                    continue
                return str(response.url), None, last_error
            return str(response.url), text, None
        except GoogleBlockedError:
            raise
        except Exception as exc:
            last_error = str(exc)
        if attempt < retries and not google:
            _backoff(attempt)
    return None, None, last_error


def post_url(
    session: Client,
    url: str,
    *,
    data: dict[str, str],
    headers: dict[str, str] | None = None,
    timeout=DEFAULT_TIMEOUT,
    retries: int = 0,
) -> tuple[int, str, str | None]:
    """POST form data. Returns (status_code, body_text, error)."""
    google_breaker.assert_allowed()
    google = is_google_host(url)
    last_error = None
    for attempt in range(retries + 1):
        if google:
            google_throttle()
        try:
            response = session.post(url, data=data, headers=headers, timeout=timeout)
            body = response.text or ""
            if google:
                blocked, block_err = _handle_google_response(response, url)
                if blocked:
                    last_error = block_err
                    if response.status_code in _GOOGLE_NO_RETRY:
                        return response.status_code, body, last_error
                    if response.status_code == 429 and attempt < retries:
                        time.sleep(_retry_after_seconds(response) or 30.0)
                        continue
                    return response.status_code, body, last_error
            if response.status_code >= 400:
                return response.status_code, body, f"{response.status_code} for url: {url}"
            return response.status_code, body, None
        except GoogleBlockedError:
            raise
        except Exception as exc:
            last_error = str(exc)
            if attempt < retries:
                _backoff(attempt)
    return 0, "", last_error


def _backoff(attempt: int) -> None:
    time.sleep(0.4 * (2 ** attempt))
