from types import SimpleNamespace

from news_rag.rupeestop_auth import rupeestop_admin_request_headers, rupeestop_bearer_token


def test_bearer_prefers_auth_token_over_admin_token():
    settings = SimpleNamespace(rupeestop_auth_token="auth-token", rupeestop_admin_token="admin-token")
    assert rupeestop_bearer_token(settings) == "auth-token"


def test_admin_headers_include_bearer():
    settings = SimpleNamespace(rupeestop_auth_token="secret", rupeestop_admin_token="")
    url = "https://backend.rupeestop.com/api/v1/admin/rs-rating/INF123"
    headers = rupeestop_admin_request_headers(url, settings=settings)
    assert headers["Authorization"] == "Bearer secret"


def test_non_admin_url_has_no_authorization():
    settings = SimpleNamespace(rupeestop_auth_token="secret", rupeestop_admin_token="")
    url = "https://backend.rupeestop.com/api/v1/app/fund/INF123"
    headers = rupeestop_admin_request_headers(url, settings=settings)
    assert "Authorization" not in headers
