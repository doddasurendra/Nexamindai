"""SSRF protection, rate limiting and MCP header encryption tests."""
from __future__ import annotations

import pytest

from app.errors import SSRFBlocked
from app.services.fetch import validate_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://localhost:8000/",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "file:///C:/Windows/win.ini",
        "ftp://example.com/file",
        "http://user:pass@example.com/",
    ],
)
async def test_ssrf_blocks_dangerous_urls(url):
    with pytest.raises(SSRFBlocked):
        await validate_url(url)


async def test_ssrf_allows_documented_private_override():
    assert await validate_url("http://127.0.0.1:8000/", allow_private=True) == "http://127.0.0.1:8000/"


def test_rate_limit_returns_429(client, monkeypatch):
    from app import middleware

    monkeypatch.setattr(middleware.settings, "auth_rate_limit_per_minute", 2)
    middleware.RateLimitMiddleware.windows.clear()
    payload = {"email": "rate@example.com", "password": "password-123"}
    client.post("/api/auth/login", json=payload)
    client.post("/api/auth/login", json=payload)
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == 429
    assert response.headers["retry-after"] == "60"
    middleware.RateLimitMiddleware.windows.clear()


def test_mcp_headers_roundtrip():
    from app.services.mcp import decrypt_headers, encrypt_headers

    token = encrypt_headers({"Authorization": "Bearer secret-value"})
    assert "secret-value" not in token
    assert decrypt_headers(token) == {"Authorization": "Bearer secret-value"}


def test_openrouter_key_never_exposed_in_health(client):
    payload = client.get("/health").json()
    assert "openrouter_api_key" not in payload
    assert "OPENROUTER_API_KEY" not in str(payload)
