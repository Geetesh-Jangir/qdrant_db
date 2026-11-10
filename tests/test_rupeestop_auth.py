import base64
import json
import os
import time
from types import SimpleNamespace

from news_rag.rupeestop_auth import (
    ensure_fresh_rupeestop_bearer,
    persist_rupeestop_auth_token,
    rupeestop_admin_request_headers,
    rupeestop_bearer_token,
    token_needs_refresh,
)


def _jwt(exp: int) -> str:
    header = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
    payload = base64.urlsafe_b64encode(json.dumps({"exp": exp}).encode()).decode().rstrip("=")
    return f"{header}.{payload}.sig"


def test_bearer_prefers_auth_token_over_admin_token():
    settings = SimpleNamespace(rupeestop_auth_token="auth-token", rupeestop_admin_token="admin-token")
    assert rupeestop_bearer_token(settings) == "auth-token"


def test_admin_headers_include_bearer():
    settings = SimpleNamespace(
        rupeestop_auth_token="secret",
        rupeestop_admin_token="",
        rupeestop_admin_username="",
        rupeestop_admin_password="",
        rupeestop_backend_base="https://backend.rupeestop.com",
    )
    url = "https://backend.rupeestop.com/api/v1/admin/rs-rating/INF123"
    headers = rupeestop_admin_request_headers(url, settings=settings)
    assert headers["Authorization"] == "Bearer secret"


def test_non_admin_url_has_no_authorization():
    settings = SimpleNamespace(rupeestop_auth_token="secret", rupeestop_admin_token="")
    url = "https://backend.rupeestop.com/api/v1/app/fund/INF123"
    headers = rupeestop_admin_request_headers(url, settings=settings)
    assert "Authorization" not in headers


def test_valid_jwt_does_not_call_login(monkeypatch):
    future = int(time.time()) + 3600
    settings = SimpleNamespace(
        rupeestop_auth_token=_jwt(future),
        rupeestop_admin_token="",
        rupeestop_admin_username="user",
        rupeestop_admin_password="pass",
        rupeestop_backend_base="https://backend.rupeestop.com",
    )

    def fail_post(*_a, **_k):
        raise AssertionError("login should not run for a valid JWT")

    monkeypatch.setattr("news_rag.rupeestop_auth.httpx.Client", lambda **_k: SimpleNamespace(post=fail_post))
    assert ensure_fresh_rupeestop_bearer(settings) == settings.rupeestop_auth_token
    assert not token_needs_refresh(settings.rupeestop_auth_token)


def test_expired_jwt_logs_in_once_and_reuses_fresh_token(monkeypatch):
    past = int(time.time()) - 60
    future = int(time.time()) + 7200
    old = _jwt(past)
    new = _jwt(future)
    settings = SimpleNamespace(
        rupeestop_auth_token=old,
        rupeestop_admin_token="",
        rupeestop_admin_username="rupeestop@123",
        rupeestop_admin_password="rupeestop@123",
        rupeestop_backend_base="https://backend.rupeestop.com",
    )
    calls: list[dict] = []

    class FakeResp:
        status_code = 200

        @staticmethod
        def json():
            return {"message": "Login successful", "token": new}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def post(self, url, json=None, headers=None):
            calls.append({"url": url, "json": json, "headers": headers})
            return FakeResp()

    monkeypatch.setattr("news_rag.rupeestop_auth.httpx.Client", FakeClient)

    def _persist(t: str) -> None:
        settings.rupeestop_auth_token = t
        os.environ["RUPEESTOP_AUTH_TOKEN"] = t

    monkeypatch.setattr("news_rag.rupeestop_auth.persist_rupeestop_auth_token", _persist)

    first = ensure_fresh_rupeestop_bearer(settings)
    second = ensure_fresh_rupeestop_bearer(settings)
    assert first == new
    assert second == new
    assert len(calls) == 1
    assert calls[0]["json"] == {"username": "rupeestop@123", "password": "rupeestop@123"}
    assert "/api/v1/user/admin-login" in calls[0]["url"]


def test_admin_headers_use_token_from_login(monkeypatch):
    past = int(time.time()) - 60
    future = int(time.time()) + 7200
    old = _jwt(past)
    new = _jwt(future)
    settings = SimpleNamespace(
        rupeestop_auth_token=old,
        rupeestop_admin_token="",
        rupeestop_admin_username="u",
        rupeestop_admin_password="p",
        rupeestop_backend_base="https://backend.rupeestop.com",
    )

    class FakeResp:
        status_code = 200

        @staticmethod
        def json():
            return {"token": new}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def post(self, *_a, **_k):
            return FakeResp()

    monkeypatch.setattr("news_rag.rupeestop_auth.httpx.Client", FakeClient)
    monkeypatch.setattr("news_rag.rupeestop_auth.persist_rupeestop_auth_token", lambda t: None)
    headers = rupeestop_admin_request_headers(
        "https://backend.rupeestop.com/api/v1/admin/rs-rating/INF123",
        settings=settings,
    )
    assert headers["Authorization"] == f"Bearer {new}"


def test_failed_login_keeps_previous_token(monkeypatch):
    past = int(time.time()) - 60
    old = _jwt(past)
    settings = SimpleNamespace(
        rupeestop_auth_token=old,
        rupeestop_admin_token="",
        rupeestop_admin_username="u",
        rupeestop_admin_password="p",
        rupeestop_backend_base="https://backend.rupeestop.com",
    )

    class FakeResp:
        status_code = 401

        @staticmethod
        def json():
            return {}

    class FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def post(self, *_a, **_k):
            return FakeResp()

    monkeypatch.setattr("news_rag.rupeestop_auth.httpx.Client", FakeClient)
    assert ensure_fresh_rupeestop_bearer(settings) == old


def test_persist_sets_process_env(monkeypatch, tmp_path):
    monkeypatch.setenv("RUPEESTOP_AUTH_TOKEN", "before")
    env = tmp_path / ".env"
    env.write_text("RUPEESTOP_AUTH_TOKEN=before\nOTHER=1\n", encoding="utf-8")
    monkeypatch.setattr("news_rag.rupeestop_auth._env_files_for_token", lambda: [env])
    persist_rupeestop_auth_token("after")
    assert os.environ.get("RUPEESTOP_AUTH_TOKEN") == "after"
    assert "RUPEESTOP_AUTH_TOKEN=after" in env.read_text(encoding="utf-8")

